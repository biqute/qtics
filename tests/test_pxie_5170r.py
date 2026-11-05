"""Test PXIe-5170R driver."""

from qtics.instruments.niscope.pxie_5170r import Pxie5170R, SoftwareTrigger


def test_default_sample_rate():
    """Default sample rate must be the 5170R maximum, 250 MS/s."""
    assert Pxie5170R("pxie", "address").sample_rate == 250e6


def test_default_trigger_immediate():
    """No trigger configured by default, i.e. niscope immediate trigger."""
    assert Pxie5170R("pxie", "address").trigger is None


def test_software_trigger_without_source():
    """Software trigger has no source."""
    assert SoftwareTrigger().source is None
