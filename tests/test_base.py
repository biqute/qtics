"""Test base instrument classes, helpers and type interfaces."""

import struct

import numpy as np
import pytest

from qtics.instruments.base import Instrument, MessageInstrument, SCPIInstrument
from qtics.instruments.types import RFSource
from qtics.instruments.utils import query_binblock, to_bool
from qtics.transport import FakeTransport, SerialTransport, SocketTransport


class Device(SCPIInstrument):
    """SCPI device with a setup and a teardown."""

    transport_defaults = {"port": 1234}

    def __init__(self, transport, name="", **kwargs):
        """Initialize."""
        super().__init__(transport, name, **kwargs)
        self.level = 0.0

    def _after_connect(self):
        self.write("SYST:REM")

    def _before_disconnect(self):
        self.write("SYST:LOC")


class SerialDevice(MessageInstrument):
    """Device with a serial default transport."""

    default_transport = SerialTransport
    transport_defaults = {"baudrate": 115200, "terminator": "\r"}


@pytest.fixture
def fake():
    """Fake transport answering identification and completion."""
    return FakeTransport({"*IDN?": "fake,device", "*OPC?": "1"})


def test_address_builds_default_transport():
    """An address string builds the default transport, without connecting."""
    dev = Device("192.0.2.1", timeout=3)
    assert isinstance(dev.transport, SocketTransport)
    assert dev.transport.port == 1234
    assert dev.transport.timeout == 3
    assert dev.address == "192.0.2.1"
    assert dev.name == "Device"
    assert not dev.is_connected


def test_serial_default_transport():
    """Transport defaults are per driver."""
    dev = SerialDevice("/dev/null", name="synth")
    assert isinstance(dev.transport, SerialTransport)
    assert dev.transport.serial.baudrate == 115200
    assert dev.transport.terminator == "\r"
    assert dev.name == "synth"


def test_transport_options_need_address(fake):
    """Transport options with a transport instance are an error."""
    with pytest.raises(TypeError):
        Device(fake, timeout=3)


def test_connect_hooks(fake):
    """Setup and teardown run around the transport, connect is idempotent."""
    with Device(fake) as dev:
        dev.connect()
        assert dev.is_connected
    assert fake.written == ["SYST:REM", "SYST:LOC"]
    assert not fake.is_connected


def test_scpi_common_commands(fake):
    """SCPI common commands."""
    dev = Device(fake)
    dev.connect()
    assert dev.get_id() == "fake,device"
    assert dev.is_completed
    with pytest.raises(ValueError):
        dev.query("NO_QUESTION_MARK")


def test_scpi_reset_restores_defaults(fake):
    """SCPI reset sends *RST, then applies the defaults."""
    dev = Device(fake)
    dev.connect()
    dev.update_defaults(level=2.5)
    dev.reset()
    assert fake.written[-1] == "*RST"
    assert dev.level == 2.5


def test_message_reset_sends_nothing(fake):
    """Non-SCPI instruments only restore defaults on reset."""
    dev = MessageInstrument(fake)
    dev.connect()
    dev.reset()
    assert fake.written == []


def test_validate_opt_returns_value():
    """validate_opt returns the validated option."""
    assert Instrument.validate_opt(2, (1, 2, 3)) == 2
    with pytest.raises(RuntimeError):
        Instrument.validate_opt(4, (1, 2, 3))


@pytest.mark.parametrize(
    "answer, expected",
    [("1", True), ("ON", True), (" on\n", True), ("0", False), ("OFF", False)],
)
def test_to_bool(answer, expected):
    """Instrument on/off answers."""
    assert to_bool(answer) is expected


def test_query_binblock(fake):
    """Binary block parsing through the transport."""
    values = [1.5, -2.0, 3.25]
    payload = struct.pack("<3d", *values)
    header = f"#2{len(payload)}".encode()
    fake.answers["TRAC?"] = header + payload + b"\n"
    dev = Device(fake)
    dev.data_format = None
    dev.connect()
    np.testing.assert_array_equal(query_binblock(dev, "TRAC?"), values)
    assert dev.data_format == "REAL,64"


def test_query_binblock_ascii(fake):
    """ASCII data."""
    fake.answers["TRAC?"] = "1,2.5,3"
    dev = Device(fake)
    dev.connect()
    np.testing.assert_array_equal(query_binblock(dev, "TRAC?", "ASC,0"), [1, 2.5, 3])


def test_type_interface_enforced(fake):
    """A driver missing a required property cannot be instantiated."""

    class Incomplete(RFSource, SCPIInstrument):
        """Source without output."""

        @property
        def frequency(self):
            """Frequency."""
            return 0.0

    with pytest.raises(TypeError):
        Incomplete(fake)  # pylint: disable=abstract-class-instantiated
