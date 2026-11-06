"""Hardware tests of the Keithley 6514 electrometer.

Config: ``[Keithley6514]`` with ``address`` (serial port). Only measurements are
made, nothing is applied to the input; the zero correction sequence is run by
``set_measure``, leave the input open or with the usual cabling.
"""

import pytest

from qtics import Keithley6514


@pytest.fixture(scope="module")
def meter(open_instrument):
    """Connected electrometer, zero check left off."""
    inst = open_instrument(Keithley6514)
    yield inst
    inst.zcheck_off()


def test_identity(meter):
    """The instrument answers *IDN? as a Keithley 6514."""
    idn = meter.get_id()
    assert "6514" in idn


@pytest.mark.parametrize("parameter", ["VOLT", "CURR", "RES", "CHAR"])
def test_read_data(meter, parameter):
    """After set_measure the reading is a float."""
    meter.set_measure(parameter)
    assert isinstance(meter.read_data(), float)


def test_set_measure_invalid(meter):
    """An unknown parameter is refused without talking to the instrument."""
    with pytest.raises(ValueError):
        meter.set_measure("FREQ")
