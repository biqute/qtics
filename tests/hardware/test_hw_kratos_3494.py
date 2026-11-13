"""Hardware tests of the Kratos 3494 attenuator, driven by an Arduino.

Config: ``[Kratos3494Attenuator]`` with ``address`` (serial port).

Changing the attenuation changes the signal path, so setters are marked
``output``. Each roundtrip restores the original attenuation.
"""

import pytest

from qtics import Kratos3494Attenuator


@pytest.fixture(scope="module")
def attenuator(open_instrument):
    """Connected attenuator."""
    return open_instrument(Kratos3494Attenuator)


def test_identity(attenuator):
    """The Arduino answers *IDN?."""
    assert attenuator.get_id()


def test_readonly(attenuator):
    """Attenuation and pin state are readable."""
    assert 0 <= attenuator.attenuation <= 63.75
    assert attenuator.get_pins_state().strip()


@pytest.mark.output
@pytest.mark.parametrize("values", [[0, 10, 31.5], [20.25, 0.5]])
def test_roundtrip(attenuator, roundtrip, values):
    """Set attenuations are read back."""
    roundtrip(attenuator, "attenuation", values, abs_tol=0.01)
