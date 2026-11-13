"""Hardware tests of the NI QuickSyn synthesizer (base ``QuickSyn`` class).

Config: ``[QuickSyn]`` with ``address`` (serial port). Nothing needs to be
connected to the RF output. The frequency range tested (0.65-10 GHz) is valid for
all the QuickSyn models.
"""

import pytest

from qtics import QuickSyn


@pytest.fixture(scope="module")
def synth(open_instrument):
    """Connected synthesizer, RF output left off."""
    inst = open_instrument(QuickSyn)
    if inst.output:
        pytest.skip("RF output is on, it may be in use: not touching it")
    yield inst
    inst.output = False


def test_identity(synth):
    """The instrument answers a non-empty identification string."""
    assert synth.get_id()


def test_readonly(synth):
    """Status queries answer with the expected types."""
    assert isinstance(synth.output, bool)
    assert isinstance(synth.ext_ref_source, bool)
    assert 0 < synth.temperature < 100
    assert synth.min_freq <= synth.frequency <= synth.max_freq


@pytest.mark.parametrize("values", [[1e9, 5.123456789e9]])
def test_roundtrip(synth, roundtrip, values):
    """Set frequencies are read back."""
    roundtrip(synth, "frequency", values)


@pytest.mark.output
def test_output(synth, confirm):
    """Switch the RF output on at 1 GHz and off again."""
    synth.frequency = 1e9
    synth.output = True
    assert synth.output
    confirm("Is the RF output of the QuickSyn enabled (indicator lit)?")
    synth.output = False
    assert not synth.output
