"""Test command strings of network instrument drivers."""

import pytest

from qtics import FSV3030, RSZNB, SAN9916A, SMA100B, VNAN9916A


def mock_io(mocker, inst):
    """Replace write and query of an instrument with mocks."""
    mocker.patch.object(inst, "write")
    mocker.patch.object(inst, "query", return_value="0")
    return inst


@pytest.fixture
def sma(mocker):
    """SMA100B with mocked I/O."""
    return mock_io(mocker, SMA100B("127.0.0.1"))


@pytest.fixture
def sa(mocker):
    """SAN9916A with mocked I/O."""
    return mock_io(mocker, SAN9916A("127.0.0.1"))


def test_sma100b_f_center(sma):
    """Center frequency setter must send FREQ:CENT."""
    sma.f_center = 5e9
    sma.write.assert_called_once_with("SOUR:FREQ:CENT 5000000000.0")


@pytest.mark.parametrize("mode", ["AUTO", "SING", "EXT", "EAUT"])
def test_sma100b_f_sweep_mode(sma, mode):
    """All frequency sweep trigger modes must be accepted."""
    sma.f_sweep_mode = mode
    sma.write.assert_called_once_with(f"TRIG:FSW:SOUR {mode}")


def test_n9916a_auto_attenuation(sa):
    """Auto attenuation setter must send POW:ATT:AUTO."""
    sa.auto_attenuation = True
    sa.write.assert_called_once_with("POW:ATT:AUTO 1")


def test_n9916a_yscale(sa):
    """Amplitude scale command must not contain a stray colon."""
    sa.yscale = "LOG"
    sa.write.assert_called_once_with("AMPL:SCAL LOG")


@pytest.mark.parametrize("cls", [SMA100B, VNAN9916A, SAN9916A, FSV3030, RSZNB])
def test_default_timeout_in_seconds(cls):
    """Socket timeout is in seconds, default must be a few seconds."""
    assert cls("127.0.0.1").timeout == 10
