"""Tests of the Keithley6514 driver."""

import pytest

from qtics.instruments.keithley.k6514 import Keithley6514
from qtics.transport import FakeTransport, SerialTransport


@pytest.fixture
def meter():
    """Keithley6514 on a fake transport."""
    inst = Keithley6514(FakeTransport())
    inst.transport.connect()
    return inst


def test_defaults():
    """Serial defaults."""
    inst = Keithley6514("/dev/null")
    assert isinstance(inst.transport, SerialTransport)
    assert inst.transport.serial.baudrate == 9600
    assert inst.transport.delay == 0.3


def test_remote_hooks():
    """SYST:REM on connect, SYST:LOC on disconnect."""
    inst = Keithley6514(FakeTransport())
    inst.connect()
    inst.disconnect()
    assert inst.transport.written == ["SYST:REM", "SYST:LOC"]


def test_set_zero(meter):
    """Zero correction sequence."""
    meter.set_zero()
    assert meter.transport.written == ["SYST:ZCH ON", "SYST:ZCOR ON", "SYST:ZCH OFF"]


def test_set_measure(meter):
    """Measure setup commands."""
    meter.set_measure("CURR")
    assert meter.transport.written[:2] == ["SENS:FUNC 'CURR'", "SENS:CURR:RANG:AUTO ON"]


def test_set_measure_invalid(meter):
    """Invalid parameter raises."""
    with pytest.raises(ValueError):
        meter.set_measure("FOO")


def test_read_data(meter):
    """Read returns a float."""
    meter.transport.answers["READ?"] = "1.5E-9"
    assert meter.read_data() == 1.5e-9
    assert meter.transport.written == ["FORM:ELEM READ", "ARM:COUNT 1", "READ?"]
