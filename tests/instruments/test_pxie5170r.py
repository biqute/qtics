"""Test PXIe-5170R driver."""

import pytest

pytest.importorskip("niscope")

from qtics.instruments.base import Instrument  # noqa: E402
from qtics.instruments.ni import pxie5170r  # noqa: E402
from qtics.instruments.ni.pxie5170r import (  # noqa: E402
    DigitalTrigger,
    EdgeTrigger,
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


class FakeChannels:
    """``session.channels`` recording the selected channels."""

    def __init__(self, session):
        self.session = session

    def __getitem__(self, channels):
        self.session.selected = channels
        return self

    def read(self, num_samples):
        self.session.calls.append(("read", {"num_samples": num_samples}))
        return ["waveform"]


class FakeSession:
    """Stand-in for ``niscope.Session`` recording the calls."""

    instances: list = []

    def __init__(self, resource_name, options=None):
        self.resource_name = resource_name
        self.options = options
        self.calls = []
        self.selected = None
        self.channels = FakeChannels(self)
        FakeSession.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.calls.append(("close", {}))

    def __getattr__(self, method):
        if not method.startswith("configure_"):
            raise AttributeError(method)
        return lambda **kwargs: self.calls.append((method, kwargs))


@pytest.fixture
def session(monkeypatch):
    """Patch ``niscope.Session`` and return a function giving the last session."""
    FakeSession.instances = []
    monkeypatch.setattr(pxie5170r.ni, "Session", FakeSession)
    return lambda: FakeSession.instances[-1]


def calls(sess, method):
    """Keyword arguments of the calls of ``method``."""
    return [kwargs for name, kwargs in sess.calls if name == method]


def test_coupling():
    """Coupling is mapped to the niscope enum, invalid values are rejected."""
    inst = Pxie5170R("address")
    assert inst.coupling == pxie5170r.ni.VerticalCoupling.DC
    inst.coupling = "AC"
    assert inst.coupling == pxie5170r.ni.VerticalCoupling.AC
    with pytest.raises(RuntimeError):
        inst.coupling = "GND"


def test_sample_rate_is_int():
    """Sample rate is stored as an integer."""
    inst = Pxie5170R("address")
    inst.sample_rate = 1e8
    assert inst.sample_rate == 100_000_000
    assert isinstance(inst.sample_rate, int)


def test_available(session):
    """Available opens and closes a session on the address."""
    assert Pxie5170R("PXI1Slot2").available
    assert session().resource_name == "PXI1Slot2"
    assert session().calls == [("close", {})]


def test_not_available(monkeypatch):
    """Available is False if the session cannot be opened."""

    def fail(*args, **kwargs):
        raise RuntimeError("no device")

    monkeypatch.setattr(pxie5170r.ni, "Session", fail)
    assert not Pxie5170R("PXI1Slot2").available


def test_acquire(session):
    """Acquire configures the session and reads the requested samples."""
    inst = Pxie5170R("PXI1Slot2")
    inst.voltage_range = 2
    inst.coupling = "AC"
    inst.sample_rate = 100e6
    assert inst.acquire("0,1", 2e-6, ref_position=10, options={"simulate": True}) == [
        "waveform"
    ]
    sess = session()
    assert sess.options == {"simulate": True}
    assert calls(sess, "configure_vertical") == [
        {"range": 2, "coupling": pxie5170r.ni.VerticalCoupling.AC}
    ]
    assert calls(sess, "configure_horizontal_timing") == [
        {
            "min_sample_rate": 100_000_000,
            "min_num_pts": 200,
            "ref_position": 10,
            "num_records": 1,
            "enforce_realtime": True,
        }
    ]
    assert not [name for name, _ in sess.calls if name.startswith("configure_trigger")]
    assert sess.selected == "0,1"
    assert calls(sess, "read") == [{"num_samples": 200}]
    assert sess.calls[-1] == ("close", {})


@pytest.mark.parametrize(
    "trigger, method, expected",
    [
        (
            SoftwareTrigger(holdoff=1e-6, delay=2e-6),
            "configure_trigger_software",
            {"holdoff": 1e-6, "delay": 2e-6},
        ),
        (
            DigitalTrigger("VAL_PFI_0", delay=1e-6),
            "configure_trigger_digital",
            {
                "trigger_source": "VAL_PFI_0",
                "slope": pxie5170r.ni.TriggerSlope.POSITIVE,
                "holdoff": 0.0,
                "delay": 1e-6,
            },
        ),
        (
            EdgeTrigger("0", level=0.5, slope=pxie5170r.ni.TriggerSlope.NEGATIVE),
            "configure_trigger_edge",
            {
                "trigger_source": "0",
                "trigger_coupling": pxie5170r.ni.TriggerCoupling.DC,
                "slope": pxie5170r.ni.TriggerSlope.NEGATIVE,
                "holdoff": 0.0,
                "delay": 0.0,
                "level": 0.5,
            },
        ),
    ],
)
def test_acquire_with_trigger(session, trigger, method, expected):
    """The trigger is configured before reading."""
    inst = Pxie5170R("PXI1Slot2")
    inst.trigger = trigger
    inst.acquire("0", 1e-6)
    sess = session()
    assert calls(sess, method) == [expected]
    names = [name for name, _ in sess.calls]
    assert names.index(method) < names.index("read")
