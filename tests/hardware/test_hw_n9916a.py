"""Hardware tests of the Keysight N9916A FieldFox, in VNA and SA mode.

Config: ``[VNAN9916A]`` and ``[SAN9916A]``, each with ``address`` (the same
instrument). Connecting resets it and selects the mode. The VNA and SA tests are
grouped in classes, each connection is closed at the end of its class so the two
modes are never connected at once. The VNA sweep emits RF at -30 dBm.
"""

import numpy as np
import pytest

from qtics import SAN9916A, VNAN9916A


@pytest.fixture(scope="class")
def vna(open_instrument):
    """Connected FieldFox in VNA mode at the lowest test power."""
    inst = open_instrument(VNAN9916A)
    inst.power = -30
    yield inst
    inst.continuous = False
    inst.disconnect()


@pytest.fixture(scope="class")
def sa(open_instrument):
    """Connected FieldFox in SA mode."""
    inst = open_instrument(SAN9916A)
    yield inst
    inst.disconnect()


class TestVNA:
    """FieldFox in VNA mode."""

    def test_vna_identity(self, vna):
        """The instrument answers *IDN? as an N9916A."""
        assert "N9916A" in vna.get_id().upper()

    def test_vna_readonly(self, vna):
        """Status queries answer with the expected types."""
        assert isinstance(vna.continuous, bool)
        assert isinstance(vna.points, int)
        assert isinstance(vna.averages, int)
        assert vna.f_stop > vna.f_start
        assert "S21" in vna.s_parameter.upper()

    @pytest.mark.parametrize(
        "prop, values",
        [
            ("f_start", [1e9, 1.5e9]),
            ("f_stop", [2e9, 3e9]),
            ("points", [101, 201]),
            ("ifbw", [1000]),
            ("power", [-30, -25]),
            ("averages", [1, 4]),
        ],
    )
    def test_vna_roundtrip(self, vna, roundtrip, prop, values):
        """Set values are read back."""
        roundtrip(vna, prop, values)

    @pytest.mark.output
    def test_vna_snapshot(self, vna):
        """A sweep at -30 dBm returns complex data matching the frequency axis."""
        vna.set(f_start=1e9, f_stop=2e9, points=201, power=-30, ifbw=1000, averages=1)
        vna.continuous = False
        freqs, trace = vna.snapshot()
        assert len(freqs) == len(trace) == vna.points == 201
        assert np.iscomplexobj(trace)
        assert np.all(np.isfinite(trace))


class TestSA:
    """FieldFox in SA mode."""

    def test_sa_identity(self, sa):
        """The instrument answers *IDN? as an N9916A."""
        assert "N9916A" in sa.get_id().upper()

    def test_sa_readonly(self, sa):
        """Status queries answer with the expected types."""
        assert isinstance(sa.continuous, bool)
        assert isinstance(sa.auto_rbw, bool)
        assert sa.f_stop > sa.f_start
        assert sa.rbw > 0

    @pytest.mark.parametrize(
        "prop, values",
        [
            ("f_center", [2e9, 3e9]),
            ("f_span", [1e6, 1e7]),
            ("points", [101, 201]),
            ("rbw", [1e4, 1e5]),
            ("attenuation", [10, 20]),
        ],
    )
    def test_sa_roundtrip(self, sa, roundtrip, prop, values):
        """Set values are read back."""
        roundtrip(sa, prop, values)

    def test_sa_snapshot(self, sa):
        """A single sweep returns a finite trace matching the frequency axis."""
        sa.set(f_center=2e9, f_span=1e7, points=201, rbw=1e5, averages=1)
        sa.continuous = False
        freqs, trace = sa.snapshot()
        assert len(freqs) == len(trace) == sa.points == 201
        assert np.all(np.isfinite(trace))
