"""Hardware tests of the Oxford Triton dilution refrigerator controller.

Config: ``[Triton]`` with ``address``.

STRICTLY READ-ONLY: only queries (temperatures, state, action, set point and
heater range reads). No setter is ever called, there is no output test.
"""

import pytest

from qtics import Triton


@pytest.fixture(scope="module")
def fridge(open_instrument):
    """Connected cryostat controller."""
    return open_instrument(Triton)


@pytest.mark.parametrize(
    "getter",
    [
        "get_mixing_chamber_temp",
        "get_still_temp",
        "get_cool_temp",
        "get_pt1_temp",
        "get_pt2_temp",
        "get_sorb_temp",
    ],
)
def test_temperatures(fridge, getter):
    """Each thermometer answers with a plausible temperature in K."""
    temperature = getattr(fridge, getter)()
    assert isinstance(temperature, float)
    assert 0 < temperature < 400


def test_state(fridge):
    """State and action are non-empty strings."""
    state = fridge.get_state()
    assert isinstance(state, str) and state
    if state == "OK":
        assert fridge.get_action()


def test_loop_readings(fridge):
    """Set point and heater range read as positive floats when they are set."""
    for prop in ("mixing_chamber_tset", "heater_range"):
        try:
            value = getattr(fridge, prop)
        except RuntimeError as error:
            pytest.skip(f"{prop} not set on the cryostat: {error}")
        assert isinstance(value, float)
        assert value >= 0
