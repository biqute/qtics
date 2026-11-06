"""Hardware tests of the Keithley 2231A-30-3 triple channel power supply.

Config: ``[Keithley2231A]`` with ``address`` (serial port). Nothing should be
connected to the outputs: the output test uses 0.1 V with a 10 mA current limit on
channel 1.
"""

import pytest

from qtics import Keithley2231A


@pytest.fixture(scope="module")
def supply(open_instrument):
    """Connected supply on channel 1, outputs left off."""
    inst = open_instrument(Keithley2231A)
    for ch in (1, 2, 3):
        inst.channel = ch
        if inst.output:
            pytest.skip(f"channel {ch} is on, it may be in use: not touching it")
    inst.channel = 1
    yield inst
    for ch in (1, 2, 3):
        inst.channel = ch
        inst.output = False
    inst.channel = 1


def test_identity(supply):
    """The instrument answers *IDN? as a Keithley 2231A."""
    idn = supply.get_id()
    assert "2231A" in idn.upper()


@pytest.mark.parametrize("channel", [1, 2, 3])
def test_readonly(supply, channel):
    """Setpoints and limits of each channel are numbers."""
    supply.channel = channel
    assert supply.channel == channel
    assert isinstance(supply.output, bool)
    for prop in ("voltage", "current", "voltage_limit", "current_limit"):
        assert isinstance(getattr(supply, prop), float), prop
    supply.channel = 1


@pytest.mark.parametrize(
    "prop, values",
    [
        ("channel", [2, 3, 1]),
        ("voltage", [0.1, 0.5]),
        ("current", [0.01, 0.1]),
        ("voltage_limit", [4, 5]),
        ("current_limit", [0.05, 0.1]),
    ],
)
def test_roundtrip(supply, roundtrip, prop, values):
    """Set values are read back (output off, channel 1)."""
    roundtrip(supply, prop, values, abs_tol=1e-3)


@pytest.mark.output
def test_output(supply, confirm):
    """Switch channel 1 on at 0.1 V / 10 mA and off again."""
    supply.channel = 1
    supply.set(voltage=0.1, current=0.01)
    supply.output = True
    assert supply.output
    confirm("Is the channel 1 output indicator of the 2231A lit?")
    supply.output = False
    assert not supply.output
