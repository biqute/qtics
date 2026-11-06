"""Hardware tests of the SRS SIM928 voltage source (in a SIM900 mainframe).

Config: ``[SIM928]`` with ``address`` (serial port of the mainframe) and
``mainframe_port`` (slot of the module). Nothing should be connected to the
output: the output test uses 0.1 V. The driver resets the module on disconnect.
"""

import pytest

from qtics import SIM928


@pytest.fixture(scope="module")
def source(open_instrument):
    """Connected voltage source, output left off."""
    inst = open_instrument(SIM928)
    if inst.output:
        pytest.skip("the output is on, it may be in use: not touching it")
    yield inst
    inst.output = False


def test_identity(source):
    """The module answers *IDN? as a Stanford Research SIM928."""
    idn = source.get_id()
    assert "SIM928" in idn.upper()


def test_readonly(source):
    """Status queries answer with the expected types."""
    assert isinstance(source.output, bool)
    assert isinstance(source.voltage, float)
    assert len(source.battery_state().split(",")) == 3
    assert source.exe_error()
    assert source.dev_error()


@pytest.mark.parametrize("values", [[0.1, 0.5, -0.25]])
def test_roundtrip(source, roundtrip, values):
    """Set voltages are read back (output off)."""
    roundtrip(source, "voltage", values, abs_tol=1e-3)


@pytest.mark.output
def test_output(source, confirm):
    """Switch the output on at 0.1 V and off again."""
    source.voltage = 0.1
    source.output = True
    assert source.output
    confirm("Is the output ON indicator of the SIM928 lit?")
    source.output = False
    assert not source.output
