"""Hardware tests of the Picowatt AVS-47B bridge with AVS47-IB GPIB interface.

Config: ``[AVS47IB]`` with ``address`` (GPIB primary address, e.g. 20) and
optionally ``board``. Needs the GPIB driver (linux-gpib or NI-488.2).

Reads and A/D conversions don't change the bridge setup. Changing channel, range
or excitation disturbs the thermometer reading the TS-530A may be controlling on,
so those tests are marked ``output``, ask the operator to confirm that no
temperature control is running, and restore the original settings. The TS-530A
is only read, never configured.
"""

import pytest

from qtics import AVS47IB
from qtics.instruments.picowatt.avs47ib import RES_OVERLOAD


@pytest.fixture(scope="module")
def bridge(open_instrument):
    """Connected bridge, in remote mode."""
    return open_instrument(AVS47IB)


@pytest.fixture
def no_control(confirm):
    """Ask the operator that changing the bridge setup is harmless."""
    confirm("Is the TS-530A temperature control off (or the bridge not used by it)?")


def test_identity(bridge):
    """The interface answers *IDN? as a Picowatt AVS47-IB."""
    idn = bridge.get_id().upper()
    assert "PICOWATT" in idn and "AVS47" in idn


def test_remote(bridge, confirm):
    """Connecting puts the bridge in remote mode."""
    assert bridge.remote
    confirm("Does the AVS-47B front panel show the REMOTE indicator?")


def test_readonly(bridge):
    """Bridge settings are read as indexes in range."""
    assert bridge.input in (0, 1, 2)
    assert 0 <= bridge.channel <= 7
    assert 0 <= bridge.range <= 7
    assert 0 <= bridge.excitation <= 7
    assert 0 <= bridge.display <= 7
    assert isinstance(bridge.autorange, bool)
    assert isinstance(bridge.overload, bool)


def test_controller_readonly(bridge):
    """TS-530A settings are read (nothing is written)."""
    assert 0 <= bridge.heater_range <= 7
    assert 0 <= bridge.set_point <= 42000


def test_measure(bridge):
    """A conversion returns a resistance within the current range."""
    if bridge.input != 1 or bridge.range == 0:
        pytest.skip("Input not in measure mode or no range selected")
    resistance = bridge.read_resistance() if bridge.overload else bridge.measure()
    assert 0 <= abs(resistance) <= RES_OVERLOAD


def test_average(bridge):
    """Averaged statistics are consistent."""
    if bridge.input != 1 or bridge.range == 0:
        pytest.skip("Input not in measure mode or no range selected")
    stats = bridge.average(3)
    if not stats["overload"]:
        assert stats["min"] <= stats["mean"] <= stats["max"]
        assert stats["std"] >= 0


@pytest.mark.output
@pytest.mark.parametrize("prop, values", [("excitation", [1, 2]), ("range", [5, 6])])
def test_roundtrip(bridge, roundtrip, no_control, prop, values):
    """Excitation and range are read back, then restored."""
    roundtrip(bridge, prop, values)


@pytest.mark.output
def test_set_channel(bridge, no_control):
    """The safe channel change ends on the requested channel, input measuring."""
    original = bridge.get("channel", "range", "excitation", "input")
    target = (original["channel"] + 1) % 8
    try:
        bridge.set_channel(target, settle=0.5)
        assert bridge.channel == target
        assert bridge.input == 1
    finally:
        bridge.set_channel(
            original["channel"], original["range"], original["excitation"], settle=0.5
        )
        bridge.input = original["input"]
