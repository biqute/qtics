"""Hardware tests of the NI PXIe-5170R digitizer (needs the ``niscope`` package).

Config: ``[Pxie5170R]`` with ``address`` (NI resource name, e.g. ``PXI1Slot2``).
Nothing needs to be connected to the input: acquisitions emit no signal.
"""

import pytest

pytest.importorskip("niscope")

from qtics import Pxie5170R  # noqa: E402


@pytest.fixture(scope="module")
def digitizer(open_instrument):
    """Connected digitizer."""
    return open_instrument(Pxie5170R)


def test_available(digitizer):
    """The device can open a session."""
    assert digitizer.available


@pytest.mark.parametrize(
    "prop, values",
    [("voltage_range", [1, 2]), ("sample_rate", [100e6, 250e6])],
)
def test_roundtrip(digitizer, roundtrip, prop, values):
    """Configuration values are read back."""
    roundtrip(digitizer, prop, values)


def test_acquire(digitizer):
    """A 1 us acquisition on channel 0 returns the expected number of samples."""
    digitizer.sample_rate = 250e6
    waveforms = digitizer.acquire("0", 1e-6)
    assert len(waveforms) == 1
    assert len(waveforms[0].samples) == int(1e-6 * digitizer.sample_rate)
