"""Serial port transport."""

from typing import Literal

import serial

from qtics import log
from qtics.transport.base import Transport


class SerialTransport(Transport):
    """Serial port transport.

    Answers are read from what is waiting in the input buffer, so a query relies on
    ``delay`` to give the instrument time to answer.
    """

    def __init__(
        self,
        address: str,
        baudrate: int = 9600,
        bytesize: int = serial.EIGHTBITS,
        parity: Literal["N", "E", "O", "M", "S"] = serial.PARITY_NONE,
        stopbits: float = serial.STOPBITS_ONE,
        timeout: float = 10,
        terminator: str = "\n",
        delay: float = 0.1,
        flush_before_write: bool = True,
    ):
        """Initialize, ``address`` is the port (e.g. /dev/ttyUSB0 or COM3)."""
        super().__init__(address, timeout, terminator, delay)
        self.flush_before_write = flush_before_write
        self.serial = serial.Serial()
        self.serial.port = address
        self.serial.baudrate = baudrate
        self.serial.bytesize = bytesize
        self.serial.parity = parity
        self.serial.stopbits = stopbits
        self.serial.timeout = timeout

    @property
    def is_connected(self) -> bool:
        """Whether the port is open."""
        return self.serial.is_open

    def connect(self):
        """Open the port."""
        if not self.serial.is_open:
            self.serial.open()

    def close(self):
        """Close the port."""
        if self.serial.is_open:
            self.serial.close()

    def _write_bytes(self, data: bytes):
        if self.flush_before_write:
            try:
                self.serial.reset_input_buffer()
            except Exception as exc:  # pylint: disable=broad-except
                log.debug(f"Error in reset input buffer: {exc}")
        self.serial.write(data)

    def read(self) -> str:
        """Read what is waiting in the input buffer."""
        if not self.serial.is_open:
            raise ConnectionError(f"Transport to {self.address} is not connected.")
        res = self.serial.read(self.serial.in_waiting).decode("utf-8").strip("\n")
        log.debug(f"READ: {res}")
        return res

    def read_raw(self, n_bytes: int) -> bytes:
        """Read exactly ``n_bytes`` bytes, or fewer on timeout."""
        if not self.serial.is_open:
            raise ConnectionError(f"Transport to {self.address} is not connected.")
        return self.serial.read(n_bytes)
