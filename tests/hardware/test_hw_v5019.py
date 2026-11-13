"""Hardware tests of the Valon 5019 RF synthesizer.

Config: ``[Valon5019]`` with ``address`` (serial port). Nothing needs to be
connected to the RF output, the output test uses -20 dBm.
"""

import pytest

from qtics import Valon5019


@pytest.fixture(scope="module")
def synth(open_instrument):
    """Connected synthesizer, RF output left off."""
    inst = open_instrument(Valon5019)
    if inst.output:
        pytest.skip("RF output is on, it may be in use: not touching it")
    yield inst
    inst.output = False


def test_identity(synth):
    """The instrument answers its ID."""
    assert "5019" in synth.get_id()


def test_readonly(synth):
    """Status queries answer with the expected types."""
    assert isinstance(synth.output, bool)
    assert synth.mode in ("CW", "SWE", "LIST")
    assert synth.ref_source in ("Internal", "External")
    assert 10e6 <= synth.frequency <= 20e9


@pytest.mark.parametrize(
    "prop, values",
    [
        ("frequency", [1e9, 5.5e9]),
        ("power", [-20, -10.5]),
        ("f_start", [1e9]),
        ("f_stop", [2e9]),
        ("f_step", [1e6]),
    ],
)
def test_roundtrip(synth, roundtrip, prop, values):
    """Set values are read back."""
    roundtrip(synth, prop, values, rel=1e-4)


@pytest.mark.output
def test_output(synth, confirm):
    """Switch the RF output on at -20 dBm and off again."""
    synth.set(frequency=1e9, power=-20)
    synth.output = True
    assert synth.output
    confirm("Is the RF output of the Valon 5019 enabled (indicator lit)?")
    synth.output = False
    assert not synth.output
