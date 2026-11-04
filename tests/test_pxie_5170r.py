"""Test PXIe-5170R driver."""

from qtics.instruments.niscope.pxie_5170r import Pxie570R


def test_default_sample_rate():
    """Default sample rate must be the 5170R maximum, 250 MS/s."""
    assert Pxie570R("pxie", "address").sample_rate == 250e6
