"""Hardware tests of the Siglent SDG6052X waveform generator.

Config: ``[SDG6052X]`` with ``address`` (raw socket port 5025 by default).
Nothing needs to be connected to the outputs, the output test uses 0.1 Vpp
into a high impedance load. The tests are skipped if an output is already on.
"""

import numpy as np
import pytest

from qtics import SDG6052X


@pytest.fixture(scope="module")
def awg(open_instrument):
    """Connected generator, outputs left off."""
    inst = open_instrument(SDG6052X)
    if inst.channel(1).output or inst.channel(2).output:
        pytest.skip("An output is on, it may be in use: not touching it")
    yield inst
    for n in (1, 2):
        inst.channel(n).output = False


@pytest.fixture
def ch1(awg):
    """Channel 1, with a sine wave."""
    channel = awg.channel(1)
    channel.waveform = "SINE"
    return channel


def test_identity(awg):
    """The instrument answers *IDN? as a Siglent SDG6052X."""
    idn = awg.get_id()
    assert "SDG6052X" in idn.upper()


def test_readonly(awg):
    """Status queries answer with the expected types."""
    for n in (1, 2):
        assert isinstance(awg.channel(n).output, bool)
    assert awg.is_completed


@pytest.mark.parametrize(
    "prop, values",
    [
        ("frequency", [1e3, 1e6]),
        ("amplitude", [0.1, 0.5]),
        ("offset", [0, 0.1]),
        ("phase", [0, 90]),
    ],
)
def test_roundtrip(ch1, roundtrip, prop, values):
    """Set values are read back."""
    roundtrip(ch1, prop, values, abs_tol=1e-9)


def test_upload_waveform(ch1):
    """An uploaded waveform is selected on the channel."""
    t = np.linspace(0, 2 * np.pi, 1024, endpoint=False)
    ch1.upload_waveform(np.sin(t), "qtics_test")
    assert ch1.arb_name == "qtics_test"
    assert ch1.waveform == "ARB"


@pytest.mark.output
def test_output(ch1, confirm):
    """Switch channel 1 on at 0.1 Vpp, 1 kHz and off again."""
    ch1.frequency = 1e3
    ch1.amplitude = 0.1
    ch1.offset = 0
    ch1.output = True
    assert ch1.output
    confirm("Is the SDG6052X channel 1 output indicator lit?")
    ch1.output = False
    assert not ch1.output
