"""Test PXIe-5170R driver."""

import pytest

pytest.importorskip("niscope")

from qtics.instruments.base import Instrument  # noqa: E402
from qtics.instruments.ni.pxie5170r import (  # noqa: E402
    Pxie570R,
    Pxie5170R,
    SoftwareTrigger,
)


def test_is_instrument_without_transport():
    """Driver has a plain address attribute and no transport."""
    inst = Pxie5170R("address")
    assert isinstance(inst, Instrument)
    assert inst.address == "address"
    assert inst.name == "Pxie5170R"
    assert not hasattr(inst, "transport")


def test_connect_disconnect_noop():
    """Connect and disconnect do nothing."""
    inst = Pxie5170R("address")
    inst.connect()
    inst.disconnect()


def test_default_sample_rate():
    """Default sample rate must be the 5170R maximum, 250 MS/s."""
    assert Pxie5170R("address").sample_rate == 250e6


def test_default_trigger_immediate():
    """No trigger configured by default, i.e. niscope immediate trigger."""
    assert Pxie5170R("address").trigger is None


def test_software_trigger_without_source():
    """Software trigger has no source."""
    assert SoftwareTrigger().source is None


def test_deprecated_alias():
    """The misspelled name is kept as an alias."""
    assert Pxie570R is Pxie5170R
