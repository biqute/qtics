"""Hardware tests of the R&S ZNB vector network analyzer.

Config: ``[ZNB]`` with ``address`` (optional: ``channel``, ``max_points``).
Connecting resets the instrument. Connect a DUT or a 50 ohm load/through to the
ports: the sweep tests emit RF at -30 dBm.
"""

import numpy as np
import pytest

from qtics import ZNB


@pytest.fixture(scope="module")
def vna(open_instrument):
    """Connected VNA at the lowest test power."""
    inst = open_instrument(ZNB)
    inst.power = -30
    yield inst
    inst.continuous = False


def test_identity(vna):
    """The instrument answers *IDN? as a Rohde & Schwarz ZNB."""
    assert "ZNB" in vna.get_id().upper()


def test_readonly(vna):
    """Status queries answer with the expected types."""
    assert isinstance(vna.continuous, bool)
    assert isinstance(vna.points, int)
    assert isinstance(vna.averages, int)
    assert vna.f_stop > vna.f_start
    assert vna.sweep_time > 0
    assert "S21" in vna.s_parameter.upper()
    assert vna.f_center == pytest.approx((vna.f_start + vna.f_stop) / 2)


@pytest.mark.parametrize(
    "prop, values",
    [
        ("f_start", [1e9, 1.5e9]),
        ("f_stop", [2e9, 3e9]),
        ("points", [101, 201]),
        ("ifbw", [1000, 10000]),
        ("power", [-30, -20.5]),
        ("averages", [1, 4]),
        ("s_parameter", ["S11", "S21"]),
    ],
)
def test_roundtrip(vna, roundtrip, prop, values):
    """Set values are read back."""
    roundtrip(vna, prop, values)


@pytest.mark.output
def test_snapshot(vna):
    """A sweep at -30 dBm returns complex data matching the frequency axis."""
    vna.set(f_start=1e9, f_stop=2e9, points=201, power=-30, ifbw=1000, averages=1)
    freqs, trace = vna.snapshot()
    assert len(freqs) == len(trace) == vna.points == 201
    assert freqs[0] == pytest.approx(1e9)
    assert freqs[-1] == pytest.approx(2e9)
    assert np.iscomplexobj(trace)
    assert np.all(np.isfinite(trace))
