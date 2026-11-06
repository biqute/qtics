"""Tests of the SIM928 driver."""

import pytest

from qtics.instruments.srs.sim928 import SIM928
from qtics.instruments.types import PowerSupply
from qtics.transport import FakeTransport, SerialTransport


@pytest.fixture
def source():
    """SIM928 on a fake transport (answers end with a terminal character)."""
    inst = SIM928(FakeTransport(default="0\r"))
    inst.transport.connect()
    return inst


def test_interface_and_defaults():
    """Type interface and serial defaults."""
    inst = SIM928("/dev/null")
    assert isinstance(inst, PowerSupply)
    assert isinstance(inst.transport, SerialTransport)
    assert inst.transport.delay == 0.1
    assert inst.transport.serial.baudrate == 9600


def test_connect_disconnect_hooks():
    """Port forwarding on connect, esc and reset before closing."""
    inst = SIM928(FakeTransport(), mainframe_port=3)
    inst.connect()
    inst.disconnect()
    assert inst.transport.written == ['CONN 3, "esc"', "esc", "*RST"]
    assert not inst.is_connected


def test_query_strips_last_char(source):
    """The trailing character is removed."""
    source.transport.answers["VOLT?"] = "1.25\r"
    assert source.query("VOLT?") == "1.25"


def test_voltage(source):
    """Getter float, setter command."""
    source.transport.answers["VOLT?"] = "1.25\r"
    assert source.voltage == 1.25
    source.voltage = 2
    assert source.transport.written[-1] == "VOLT 2"


def test_output(source):
    """Output bool property."""
    source.output = True
    source.output = False
    assert source.transport.written == ["OPON", "OPOF"]
    source.transport.default = None
    source.transport._pending.clear()
    source.transport.answers["EXON?"] = "1\r"
    assert source.output is True
    source.transport.answers["EXON?"] = "0\r"
    assert source.output is False


def test_battery_spec_invalid(source):
    """Invalid battery parameter raises."""
    with pytest.raises(RuntimeError):
        source.battery_spec("FOO")


def test_dev_error(source):
    """Error decoding."""
    source.transport.answers["LCME?"] = "1\r"
    assert source.dev_error() == "Illegal command"
