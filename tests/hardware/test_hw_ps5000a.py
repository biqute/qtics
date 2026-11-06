"""Hardware tests of the PicoScope 5000 Series oscilloscope (5444D, PicoSDK).

Config: ``[PicoScope5000A]`` with optional ``serial`` (empty opens the first unit)
and ``resolution``. Needs the PicoSDK C libraries. Nothing needs to be connected to
the inputs: captures emit no signal and start by auto trigger.
"""

import numpy as np
import pytest

from qtics import PicoScope5000A

N_SAMPLES = 1000


@pytest.fixture(scope="module")
def scope(open_instrument):
    """Connected oscilloscope, channel A at +-1 V DC, 1 us x 1000 samples."""
    inst = open_instrument(PicoScope5000A)
    inst.resolution = 8
    for channel in "BCD":
        inst.set_channel(channel, enabled=False)
    inst.set_channel("A", range_v=1.0, coupling="DC")
    inst.set_trigger("A", 0.0, auto_trigger_ms=10)
    inst.set_timebase(1e-6, N_SAMPLES)
    return inst


def test_configuration(scope):
    """The channel settings are kept and the timebase is close to the request."""
    assert scope.is_connected
    assert scope.channels["A"] == {
        "enabled": True,
        "range_v": 1.0,
        "coupling": "DC",
        "offset": 0.0,
    }
    assert scope.sample_interval == pytest.approx(1e-6, rel=0.02)
    assert scope.n_samples == N_SAMPLES


def test_acquire(scope):
    """A block capture returns the time axis and finite voltages within the range."""
    time, data = scope.acquire("A", timeout=5)
    assert len(time) == N_SAMPLES
    assert len(data["A"]) == N_SAMPLES
    assert np.all(np.isfinite(data["A"]))
    assert np.all(np.abs(data["A"]) <= 1.0 + 1e-6)
    assert np.all(np.diff(time) > 0)


def test_acquire_average(scope):
    """The average of 3 captures has the length of a capture."""
    _, data = scope.acquire("A", timeout=5, averages=3)
    assert len(data["A"]) == N_SAMPLES
    assert np.all(np.isfinite(data["A"]))


def test_resolution_roundtrip(scope, roundtrip):
    """The resolution is read back, the timebase follows it."""
    roundtrip(scope, "resolution", [8, 12])
    assert scope.resolution == 8
    assert scope.sample_interval == pytest.approx(1e-6, rel=0.02)


def test_segments(scope):
    """Rapid block mode returns one row per segment."""
    time, data = scope.acquire_segments(5, "A", timeout=5)
    assert len(time) == N_SAMPLES
    assert data["A"].shape == (5, N_SAMPLES)
    assert np.all(np.isfinite(data["A"]))
    # the memory is merged again: a normal capture still works
    assert len(scope.acquire("A", timeout=5)[0]) == N_SAMPLES


def test_led(scope, confirm):
    """The unit is working during a capture."""
    scope.acquire("A", timeout=5)
    confirm("Is the PicoScope powered, with its LED lit and no error shown?")
