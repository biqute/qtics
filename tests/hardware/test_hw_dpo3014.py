"""Hardware tests of the Tektronix DPO3014 oscilloscope.

Config: ``[DPO3014]`` with ``address`` (and ``port`` if not 4000). The socket server
must be enabled on the scope. It does not emit signals, any input is left alone.
"""

import numpy as np
import pytest

from qtics import DPO3014


@pytest.fixture(scope="module")
def scope(open_instrument):
    """Connected oscilloscope."""
    inst = open_instrument(DPO3014)
    yield inst
    inst.run()


def test_identity(scope):
    """The instrument answers *IDN? as a Tektronix DPO3014."""
    idn = scope.get_id()
    assert "TEKTRONIX" in idn.upper()
    assert "DPO3014" in idn.upper()


def test_readonly(scope):
    """Status queries answer with the expected types."""
    assert isinstance(scope.channel(1).enabled, bool)
    assert isinstance(scope.running, bool)
    assert scope.trigger_slope in ("RISE", "FALL")
    assert scope.is_completed


@pytest.mark.parametrize(
    "prop, values",
    [
        ("horizontal_scale", [1e-6, 1e-3]),
        ("record_length", [10000]),
        ("trigger_level", [0.1]),
    ],
)
def test_roundtrip(scope, roundtrip, prop, values):
    """Set values are read back."""
    roundtrip(scope, prop, values)


@pytest.mark.parametrize("prop, values", [("scale", [0.1, 1])])
def test_channel_roundtrip(scope, roundtrip, prop, values):
    """Channel settings are read back."""
    roundtrip(scope.channel(1), prop, values)


def test_single_acquisition(scope):
    """A single acquisition of channel 1 returns finite arrays of the record length."""
    channel = scope.channel(1)
    channel.enabled = True
    scope.trigger_mode = "AUTO"
    data = scope.acquire([1])
    times, volts = data[1]
    assert len(times) == len(volts) == scope.record_length
    assert np.isfinite(times).all()
    assert np.isfinite(volts).all()


def test_measure(scope):
    """An immediate measurement returns a float."""
    scope.channel(1).enabled = True
    assert isinstance(scope.measure("MEAN", 1), float)


def test_display(scope, confirm):
    """The channel scale is shown on the screen."""
    channel = scope.channel(1)
    previous = channel.scale
    channel.scale = 0.1
    try:
        confirm("Is channel 1 shown at 100 mV/div?")
    finally:
        channel.scale = previous
