"""Tests of the Keithley2231A driver."""

import pytest

from qtics.instruments.keithley.k2231a import Keithley2231A
from qtics.instruments.types import PowerSupply
from qtics.transport import FakeTransport, SerialTransport


@pytest.fixture
def psu():
    """Keithley2231A on a fake transport, answering 0."""
    inst = Keithley2231A(FakeTransport(default="0"))
    inst.transport.connect()
    return inst


def test_interface_and_defaults():
    """Type interface and serial defaults."""
    inst = Keithley2231A("/dev/null")
    assert isinstance(inst, PowerSupply)
    assert isinstance(inst.transport, SerialTransport)
    assert inst.transport.serial.baudrate == 9600
    assert inst.transport.delay == 0.3
    assert inst.transport.terminator == "\n"


def test_remote_hooks():
    """SYST:REM on connect, SYST:LOC on disconnect."""
    inst = Keithley2231A(FakeTransport())
    inst.connect()
    inst.disconnect()
    assert inst.transport.written == ["SYST:REM", "SYST:LOC"]
    assert not inst.is_connected


def test_channel(psu):
    """Channel setter must send the channel number."""
    psu.channel = 2
    assert psu.transport.written == ["INST:NSEL 2"]


def test_channel_getter(psu):
    """Channel getter returns an int."""
    psu.transport.answers["INST:NSEL?"] = "CH 2"
    assert psu.channel == 2


def test_channel_invalid(psu):
    """Invalid channel must raise."""
    with pytest.raises(RuntimeError):
        psu.channel = 4


def test_current_limit(psu):
    """Current limit setter must send CURR:LIMIT."""
    psu.current_limit = 1
    assert psu.transport.written == ["SOUR:CURR:LIMIT:LEV 1"]


def test_voltage_getter_float(psu):
    """Voltage getter returns a float."""
    psu.transport.answers["SOUR:VOLT:LEV:IMM:AMPL?"] = "1.5"
    assert psu.voltage == 1.5


def test_voltage_range_depends_on_channel(psu):
    """Channel 3 is limited to 5 V."""
    psu.transport.answers["INST:NSEL?"] = "3"
    psu.voltage = 10
    assert psu.transport.written[-1] == "SOUR:VOLT:LEV:IMM:AMPL 5"


@pytest.mark.parametrize(
    "value, cmd", [(True, "OUTP:STAT ON"), (False, "OUTP:STAT OFF")]
)
def test_output_setter(psu, value, cmd):
    """Output setter sends OUTP:STAT."""
    psu.output = value
    assert psu.transport.written == [cmd]


def test_output_getter(psu):
    """Output getter returns a bool."""
    psu.transport.answers["OUTP:STAT?"] = "1"
    assert psu.output is True
    psu.transport.answers["OUTP:STAT?"] = "0"
    assert psu.output is False


def test_save_load(psu):
    """Memory commands."""
    psu.save(1)
    psu.load(2)
    assert psu.transport.written == ["*SAV 1", "*RCL 2"]
