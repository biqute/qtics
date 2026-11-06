"""Hardware tests of the R&S SMA100B signal generator.

Config: ``[SMA100B]`` with ``address``. Nothing needs to be connected to the RF
output, the output test uses -30 dBm. The tests are skipped if the output is
already on.
"""

import pytest

from qtics import SMA100B


@pytest.fixture(scope="module")
def source(open_instrument):
    """Connected generator, RF output left off."""
    inst = open_instrument(SMA100B)
    if inst.output:
        pytest.skip("RF output is on, it may be in use: not touching it")
    yield inst
    inst.output = False


def test_identity(source):
    """The instrument answers *IDN? as a Rohde & Schwarz SMA100B."""
    idn = source.get_id()
    assert "SMA100B" in idn.upper()


def test_readonly(source):
    """Status queries answer with the expected types."""
    assert isinstance(source.output, bool)
    assert source.f_mode == "CW"
    assert source.is_completed


@pytest.mark.parametrize(
    "prop, values",
    [
        ("frequency", [1e9, 5.123456e9]),
        ("power", [-30, -20.5]),
        ("f_start", [1e9]),
        ("f_stop", [2e9]),
        ("p_start", [-40]),
        ("p_stop", [-30]),
        ("p_dwell", [0.01, 0.1]),
    ],
)
def test_roundtrip(source, roundtrip, prop, values):
    """Set values are read back."""
    roundtrip(source, prop, values)


@pytest.mark.output
def test_output(source, confirm):
    """Switch the RF output on at -30 dBm and off again."""
    source.set(frequency=1e9, power=-30)
    source.output = True
    assert source.output
    confirm("Is the SMA100B RF ON indicator lit?")
    source.output = False
    assert not source.output
