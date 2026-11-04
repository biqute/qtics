"""Test the QuickSyn drivers."""

import pytest

from qtics import FSL0010, FSL0020, FSW0010, FSW0020, QuickSyn
from qtics.instruments.types import RFSource
from qtics.transport import FakeTransport, SerialTransport


@pytest.fixture
def synth():
    """Connected FSL0010 on a fake transport."""
    inst = FSL0010(FakeTransport(default="0"))
    inst.transport.connect()
    return inst


@pytest.mark.parametrize(
    "cls, min_freq, max_freq",
    [
        (FSL0010, 0.65e9, 10e9),
        (FSL0020, 0.65e9, 20e9),
        (FSW0010, 0.5e9, 10e9),
        (FSW0020, 0.5e9, 20e9),
    ],
)
def test_freq_limits(cls, min_freq, max_freq):
    """Each QuickSyn model must keep its own frequency limits."""
    synth = cls("/dev/null")
    assert synth.min_freq == min_freq
    assert synth.max_freq == max_freq
    assert isinstance(synth, QuickSyn)


def test_transport_defaults():
    """Serial transport at 115200 baud."""
    inst = FSL0010("/dev/null")
    assert isinstance(inst.transport, SerialTransport)
    assert inst.transport.serial.baudrate == 115200
    assert inst.transport.delay == 0.1
    assert inst.transport.terminator == "\n"


def test_is_rf_source(synth):
    """QuickSyn implements the RFSource interface."""
    assert isinstance(synth, RFSource)


def test_frequency(synth):
    """Frequency is read from millihertz and written in mlHz."""
    synth.transport.answers["FREQ?"] = "5000000000000"
    assert synth.frequency == 5e9
    synth.frequency = 5e9
    assert synth.transport.written[-1] == "FREQ 5000000000000.0mlHz"


def test_frequency_clipped(synth):
    """Frequency is clipped to the model range."""
    synth.frequency = 20e9
    assert synth.transport.written[-1] == "FREQ 10000000000000.0mlHz"


@pytest.mark.parametrize("answer, expected", [("1", True), ("ON", True), ("0", False)])
def test_output_getter(synth, answer, expected):
    """Output state query may answer 1/0/ON."""
    synth.transport.answers["OUTP:STAT?"] = answer
    assert synth.output is expected


def test_output_setter(synth):
    """Output setter sends ON/OFF."""
    synth.output = True
    synth.output = False
    assert synth.transport.written == ["OUTP:STAT ON", "OUTP:STAT OFF"]


def test_ext_ref_and_temperature(synth):
    """Reference source and temperature."""
    synth.transport.answers["ROSC:SOUR?"] = "EXT"
    assert synth.ext_ref_source is True
    synth.transport.answers["DIAG:MEAS? 21"] = "35.5"
    assert synth.temperature == 35.5
    synth.ext_ref_source = False
    assert synth.transport.written[-1] == "ROSC:SOUR INT"
