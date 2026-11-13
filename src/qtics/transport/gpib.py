"""GPIB (IEEE-488) transport.

Calls the IEEE 488.2 C library of the GPIB driver through ctypes: linux-gpib
(``libgpib.so``) on Linux, NI-488.2 (``ni4882.dll``) on Windows. Only the driver
is needed, no Python package.
"""

import ctypes
import ctypes.util
import re
import sys
from functools import lru_cache
from typing import Any, Optional, Union

from qtics import log
from qtics.transport.base import Transport

# ibsta status bits
ERR = 0x8000
END = 0x2000
# iberr code of a timeout
EABO = 6
# ibtmo codes: index of the first timeout (s) not shorter than the requested one
TIMEOUTS = (
    0, 10e-6, 30e-6, 100e-6, 300e-6, 1e-3, 3e-3, 10e-3, 30e-3, 100e-3, 300e-3,
    1, 3, 10, 30, 100, 300, 1000,
)  # fmt: skip
CHUNK = 4096


@lru_cache(maxsize=None)
def load_library(path: str = "") -> Any:
    """Load the GPIB driver library, found automatically if ``path`` is empty."""
    if sys.platform == "win32":
        names = [path] if path else ["ni4882.dll", "gpib-32.dll"]
        loader: Any = ctypes.WinDLL  # type: ignore[attr-defined]
    else:
        names = [path or ctypes.util.find_library("gpib") or "libgpib.so.0"]
        loader = ctypes.CDLL
    for name in names:
        try:
            lib = loader(name)
            break
        except OSError:
            continue
    else:
        raise OSError(
            "GPIB library not found: install the GPIB driver (linux-gpib or "
            "NI-488.2) or pass its path as library."
        )
    count = ctypes.c_size_t
    lib.ibdev.argtypes = [ctypes.c_int] * 6
    lib.ibwrt.argtypes = [ctypes.c_int, ctypes.c_char_p, count]
    lib.ibrd.argtypes = [ctypes.c_int, ctypes.c_char_p, count]
    lib.ThreadIbcntl.restype = ctypes.c_long
    return lib


def timeout_code(seconds: float) -> int:
    """Return the ibtmo code of the shortest timeout of at least ``seconds``."""
    for code, value in enumerate(TIMEOUTS[1:], start=1):
        if value >= seconds:
            return code
    return len(TIMEOUTS) - 1


class GPIBTransport(Transport):
    """GPIB transport.

    ``address`` is the primary address (e.g. 20, combined with ``board``) or a
    VISA-like resource string (e.g. "GPIB0::20::INSTR"). Reads end when the
    instrument asserts EOI, as IEEE 488.2 requires, so binary data is never cut at
    the terminator.
    """

    def __init__(
        self,
        address: Union[int, str],
        board: int = 0,
        timeout: float = 10,
        terminator: str = "\n",
        delay: float = 0.1,
        library: str = "",
    ):
        """Initialize, ``library`` is the path of the driver library."""
        self.ud: Optional[int] = None
        match = re.fullmatch(r"GPIB(\d+)::(\d+)(::INSTR)?", str(address))
        if match:
            board, address = int(match[1]), int(match[2])
        self.board = board
        self.primary_address = int(address)
        resource = f"GPIB{board}::{self.primary_address}::INSTR"
        super().__init__(resource, timeout, terminator, delay)
        self.library = library

    @property
    def lib(self) -> Any:
        """The loaded driver library."""
        return load_library(self.library)

    def _check(self, status: int, action: str) -> int:
        """Raise if ``status`` has the error bit set, otherwise return it."""
        if status & ERR:
            error = self.lib.ThreadIberr()
            if error == EABO:
                raise TimeoutError(f"GPIB {action} on {self.address} timed out.")
            raise ConnectionError(
                f"GPIB {action} on {self.address} failed (iberr {error})."
            )
        return status

    @property
    def timeout(self) -> float:
        """Read timeout in seconds, also applied to an open session."""
        return self._timeout

    @timeout.setter
    def timeout(self, value: float):
        self._timeout = value
        if self.ud is not None:
            self._check(self.lib.ibtmo(self.ud, timeout_code(value)), "ibtmo")

    @property
    def is_connected(self) -> bool:
        """Whether the device descriptor is open."""
        return self.ud is not None

    def connect(self):
        """Open the device descriptor."""
        if self.ud is not None:
            return
        # no secondary address, assert EOI on the last written byte, no EOS
        ud = self.lib.ibdev(
            self.board, self.primary_address, 0, timeout_code(self.timeout), 1, 0
        )
        if ud < 0:
            raise ConnectionError(
                f"GPIB device {self.address} could not be opened "
                f"(iberr {self.lib.ThreadIberr()})."
            )
        self.ud = ud

    def close(self):
        """Close the device descriptor."""
        if self.ud is None:
            return
        self.lib.ibonl(self.ud, 0)
        self.ud = None

    def clear(self):
        """Send a GPIB device clear, which empties the instrument buffers."""
        if self.ud is None:
            raise ConnectionError(f"Transport to {self.address} is not connected.")
        self._check(self.lib.ibclr(self.ud), "device clear")

    def _write_bytes(self, data: bytes):
        assert self.ud is not None
        self._check(self.lib.ibwrt(self.ud, data, len(data)), "write")

    def _read_chunk(self, size: int) -> tuple:
        """Read up to ``size`` bytes, return them and whether the message ended."""
        assert self.ud is not None
        buffer = ctypes.create_string_buffer(size)
        status = self._check(self.lib.ibrd(self.ud, buffer, size), "read")
        return buffer.raw[: self.lib.ThreadIbcntl()], bool(status & END)

    def read(self) -> str:
        """Read until the end of message (EOI), strip the terminator."""
        if self.ud is None:
            raise ConnectionError(f"Transport to {self.address} is not connected.")
        response = b""
        ended = False
        while not ended:
            chunk, ended = self._read_chunk(CHUNK)
            response += chunk
        res = response.decode("utf-8").rstrip("\r\n")
        log.debug(f"READ: {res}")
        return res

    def read_raw(self, n_bytes: int) -> bytes:
        """Read ``n_bytes`` bytes, or fewer if the message ends before."""
        if self.ud is None:
            raise ConnectionError(f"Transport to {self.address} is not connected.")
        data = b""
        while len(data) < n_bytes:
            chunk, ended = self._read_chunk(n_bytes - len(data))
            data += chunk
            if ended:
                break
        return data
