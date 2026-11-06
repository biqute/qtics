"""Test the GPIB transport against a stand-in driver library."""

import ctypes

import pytest

from qtics.transport import GPIBTransport, gpib


class FakeLib:
    """Mimics the IEEE 488.2 functions of linux-gpib / NI-488.2."""

    def __init__(self):
        """Initialize."""
        self.opened = {}
        self.written = []
        self.outbox = b""
        self.max_read = 4096
        self.timeout = None
        self.cleared = False
        self.error = 0
        self.count = 0
        self.fail_read = False

    def ibdev(self, board, pad, sad, timo, send_eoi, eos):
        """Open a descriptor."""
        ud = len(self.opened) + 1
        self.opened[ud] = (board, pad, sad, send_eoi, eos)
        self.timeout = timo
        return ud

    def ibonl(self, ud, online):
        """Close a descriptor."""
        assert online == 0
        del self.opened[ud]
        return 0

    def ibtmo(self, ud, code):
        """Set the timeout code."""
        self.timeout = code
        return 0

    def ibclr(self, ud):
        """Device clear."""
        self.cleared = True
        return 0

    def ibwrt(self, ud, data, count):
        """Write, answering queries with "ok:<command>"."""
        self.written.append(data[:count])
        cmd = data[:count].decode().strip()
        if "?" in cmd:
            self.outbox += b"ok:" + cmd.encode() + b"\n"
        return 0

    def ibrd(self, ud, buffer, size):
        """Read at most ``max_read`` bytes, END when the outbox is empty."""
        if self.fail_read:
            self.error = gpib.EABO
            return gpib.ERR
        size = min(size, self.max_read)
        chunk, self.outbox = self.outbox[:size], self.outbox[size:]
        ctypes.memmove(buffer, chunk, len(chunk))
        self.count = len(chunk)
        return 0 if self.outbox else gpib.END

    def ThreadIbcntl(self):  # pylint: disable=invalid-name
        """Bytes moved by the last call."""
        return self.count

    def ThreadIberr(self):  # pylint: disable=invalid-name
        """Error code of the last call."""
        return self.error


@pytest.fixture
def lib(monkeypatch):
    """Replace the driver library loader with a fake."""
    fake = FakeLib()
    monkeypatch.setattr(gpib, "load_library", lambda path="": fake)
    return fake


@pytest.mark.parametrize(
    "address, board, expected",
    [
        (20, 0, "GPIB0::20::INSTR"),
        ("7", 1, "GPIB1::7::INSTR"),
        ("GPIB2::5::INSTR", 0, "GPIB2::5::INSTR"),
        ("GPIB0::5", 0, "GPIB0::5::INSTR"),
    ],
)
def test_gpib_address(address, board, expected):
    """Primary addresses and resource strings give board and address."""
    transport = GPIBTransport(address, board=board)
    assert transport.address == expected
    assert not transport.is_connected


def test_timeout_code():
    """Timeouts round up to the next ibtmo code."""
    assert gpib.timeout_code(10) == 13
    assert gpib.timeout_code(2) == 12
    assert gpib.timeout_code(1e6) == 17


def test_gpib_query(lib):
    """Connect opens the device, query writes the terminator and strips it."""
    transport = GPIBTransport(20, board=1, timeout=1, delay=0)
    transport.connect()
    assert lib.opened[transport.ud] == (1, 20, 0, 1, 0)
    assert lib.timeout == 11
    assert transport.query("INP?") == "ok:INP?"
    assert lib.written == [b"INP?\n"]
    transport.clear()
    assert lib.cleared
    transport.close()
    assert not lib.opened and not transport.is_connected


def test_gpib_read_chunks(lib):
    """Long answers are read until END."""
    transport = GPIBTransport(20)
    transport.connect()
    lib.max_read = 3
    lib.outbox = b"0123456789\n"
    assert transport.read() == "0123456789"


def test_gpib_read_raw(lib):
    """Raw reads keep terminator bytes and stop at n_bytes or END."""
    transport = GPIBTransport(20)
    transport.connect()
    lib.max_read = 2
    lib.outbox = b"\x00\n\x02\x03"
    assert transport.read_raw(3) == b"\x00\n\x02"
    assert transport.read_raw(5) == b"\x03"


def test_gpib_timeout_updates_device(lib):
    """Changing the timeout applies to the open device."""
    transport = GPIBTransport(20)
    transport.connect()
    transport.timeout = 30
    assert lib.timeout == 14


def test_gpib_read_timeout(lib):
    """A driver timeout raises TimeoutError."""
    transport = GPIBTransport(20)
    transport.connect()
    lib.fail_read = True
    with pytest.raises(TimeoutError):
        transport.read()


def test_gpib_not_connected():
    """I/O on a closed transport raises, without loading the library."""
    transport = GPIBTransport(20)
    with pytest.raises(ConnectionError):
        transport.write("*CLS")
    with pytest.raises(ConnectionError):
        transport.read()


def test_gpib_missing_library(monkeypatch):
    """Without the driver, connect says what to install."""
    gpib.load_library.cache_clear()
    monkeypatch.setattr(gpib.ctypes.util, "find_library", lambda name: None)
    with pytest.raises(OSError, match="GPIB library not found"):
        GPIBTransport(20, library="/nonexistent/libgpib.so").connect()
    gpib.load_library.cache_clear()
