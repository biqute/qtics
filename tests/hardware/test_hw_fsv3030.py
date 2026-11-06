"""Hardware tests of the R&S FSV3030 spectrum analyzer.

Config: ``[FSV3030]`` with ``address``. The instrument is not reset on connect and
the acquisitions emit nothing, but leave the RF input free of signals above the
reference level (or disconnected).
"""

import numpy as np
import pytest

from qtics import FSV3030


@pytest.fixture(scope="module")
def analyzer(open_instrument):
    """Connected spectrum analyzer."""
    return open_instrument(FSV3030)


def test_identity(analyzer):
    """The instrument answers *IDN? as a Rohde & Schwarz FSV3030."""
    assert "FSV3030" in analyzer.get_id().upper()


def test_readonly(analyzer):
    """Status queries answer with the expected types."""
    assert isinstance(analyzer.continuous, bool)
    assert isinstance(analyzer.points, int)
    assert analyzer.f_stop > analyzer.f_start
    assert analyzer.rbw > 0
    assert analyzer.sweep_time > 0
    assert analyzer.f_center == pytest.approx((analyzer.f_start + analyzer.f_stop) / 2)


@pytest.mark.parametrize(
    "prop, values",
    [
        ("f_center", [2e9, 3e9]),
        ("f_span", [1e6, 1e7]),
        ("rbw", [1e3, 1e5]),
        ("vbw", [1e3, 1e5]),
        ("points", [101, 1001]),
        ("ref_level", [-20, 0]),
    ],
)
def test_roundtrip(analyzer, roundtrip, prop, values):
    """Set values are read back."""
    roundtrip(analyzer, prop, values)


def test_snapshot(analyzer):
    """A single sweep returns a finite trace matching the frequency axis."""
    analyzer.set(f_center=2e9, f_span=1e7, points=201, rbw=1e5)
    freqs, trace = analyzer.snapshot()
    assert not analyzer.continuous
    assert len(freqs) == len(trace) == analyzer.points == 201
    assert freqs[0] == pytest.approx(2e9 - 5e6)
    assert freqs[-1] == pytest.approx(2e9 + 5e6)
    assert np.all(np.isfinite(trace))
