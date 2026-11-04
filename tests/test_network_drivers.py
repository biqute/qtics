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


@pytest.mark.parametrize("attr", ["auto_attenuation", "gain"])
def test_n9916a_bool_getters(sa, attr):
    """SCPI boolean queries answer 1/0."""
    sa.query.return_value = "1"
    assert getattr(sa, attr) is True
    sa.query.return_value = "0"
    assert getattr(sa, attr) is False


@pytest.fixture
def fsv(mocker):
    """FSV3030 with mocked I/O."""
    return mock_io(mocker, FSV3030("127.0.0.1"))


def test_fsv3030_snapshot_single_sweep(fsv, mocker):
    """Snapshot must sweep once."""
    sweep = mocker.spy(fsv, "single_sweep")
    fsv.snapshot()
    assert sweep.call_count == 1


def test_fsv3030_read_max_hold_keeps_trace(fsv):
    """Reading the max-hold trace must not reset it."""
    fsv.read_max_hold()
    assert all("MODE" not in c.args[0] for c in fsv.write.call_args_list)


@pytest.fixture
def znb(mocker):
    """RSZNB with mocked I/O."""
    return mock_io(mocker, RSZNB("127.0.0.1"))


def test_rsznb_f_center(znb):
    """Center frequency is set directly, keeping the span."""
    znb.f_center = 5e9
    znb.write.assert_called_once_with("SENSe1:FREQuency:CENTer 5000000000.0")


def test_rsznb_list_traces(znb):
    """Catalog response is a quoted string."""
    znb.query.return_value = "'Trc1,S21,Trc2,S11'"
    assert znb.list_traces() == [("Trc1", "S21"), ("Trc2", "S11")]


@pytest.mark.parametrize("offset", [0, -1e9, 30e9])
def test_sma100b_f_offset_unbounded(sma, caplog, offset):
    """Offset has no range in the manual: sent as-is, without warnings."""
    sma.f_offset = offset
    sma.write.assert_called_once_with(f"SOUR:FREQ:OFFS {offset}")
    assert "not in range" not in caplog.text


def test_rsznb_autoscale(znb):
    """Autoscale window trace 1 by default, or the given one."""
    znb.autoscale()
    znb.autoscale(2)
    assert (
        znb.write.call_args_list[0].args[0]
        == "DISPlay:WINDow1:TRACe1:Y:SCALe:AUTO ONCE"
    )
    assert (
        znb.write.call_args_list[1].args[0]
        == "DISPlay:WINDow1:TRACe2:Y:SCALe:AUTO ONCE"
    )
