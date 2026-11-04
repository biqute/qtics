"""Test the SMA100B driver."""

import pytest

from qtics import SMA100B
from qtics.instruments.types import RFSource
from qtics.transport import FakeTransport, SocketTransport


@pytest.fixture
def sma():
    """Connected SMA100B on a fake transport answering 0."""
    inst = SMA100B(FakeTransport(default="0"))
    inst.transport.connect()
    return inst


def test_is_rf_source(sma):
    """SMA100B implements the RFSource interface."""
    assert isinstance(sma, RFSource)


def test_transport_defaults():
    """Address string builds a socket transport with the old defaults."""
    inst = SMA100B("127.0.0.1")
    assert isinstance(inst.transport, SocketTransport)
    assert inst.transport.port == 5025
    assert inst.transport.timeout == 10
    assert inst.transport.delay == 0.1
    assert inst.transport.no_delay is True


def test_connect_sets_dbm():
    """Power unit is set to dBm after connecting."""
    inst = SMA100B(FakeTransport(default="0"))
    inst.connect()
    assert inst.transport.written == ["UNIT:POW DBM"]


def test_frequency(sma):
    """Frequency getter returns float, setter sends CW command."""
    sma.transport.answers["SOUR:FREQ:CW?"] = "1e9"
    assert sma.frequency == 1e9
    sma.frequency = 5e9
    assert sma.transport.written[-1] == "SOUR:FREQ:CW 5000000000.0"


def test_power(sma):
    """Power getter returns float, setter sends the level."""
    sma.transport.answers["SOUR:POW:LEV:IMM:AMPL?"] = "-10.5"
    assert sma.power == -10.5
    sma.power = -20
    assert sma.transport.written[-1] == "SOUR:POW:LEV:IMM:AMPL -20"


def test_output(sma):
    """Output is a bool property."""
    sma.transport.answers["OUTP:STAT?"] = "1"
    assert sma.output is True
    sma.transport.answers["OUTP:STAT?"] = "0"
    assert sma.output is False
    sma.output = True
    sma.output = False
    assert sma.transport.written[-2:] == ["OUTP:STAT ON", "OUTP:STAT OFF"]


def test_sweep_range(sma):
    """Sweep limits use f_start and f_stop."""
    sma.transport.answers["SOUR:FREQ:STAR?"] = "1e9"
    sma.transport.answers["SOUR:FREQ:STOP?"] = "2e9"
    assert sma.f_start == 1e9
    assert sma.f_stop == 2e9
    sma.f_start = 1e9
    sma.f_stop = 10e9
    assert sma.transport.written[-2:] == [
        "SOUR:FREQ:STAR 1000000000.0",
        "SOUR:FREQ:STOP 10000000000.0",
    ]
    with pytest.raises(ValueError):
        sma.f_stop = 30e9


def test_power_sweep_range(sma):
    """Power sweep limits use p_start and p_stop."""
    sma.p_start = -30
    sma.p_stop = 0
    assert sma.transport.written == ["SOUR:POW:STAR -30", "SOUR:POW:STOP 0"]


def test_f_center(sma):
    """Center frequency setter must send FREQ:CENT."""
    sma.f_center = 5e9
    assert sma.transport.written == ["SOUR:FREQ:CENT 5000000000.0"]


@pytest.mark.parametrize("mode", ["AUTO", "SING", "EXT", "EAUT"])
def test_f_sweep_mode(sma, mode):
    """All frequency sweep trigger modes must be accepted."""
    sma.f_sweep_mode = mode
    assert sma.transport.written == [f"TRIG:FSW:SOUR {mode}"]


@pytest.mark.parametrize("offset", [0, -1e9, 30e9])
def test_f_offset_unbounded(sma, caplog, offset):
    """Offset has no range in the manual: sent as-is, without warnings."""
    sma.f_offset = offset
    assert sma.transport.written == [f"SOUR:FREQ:OFFS {offset}"]
    assert "not in range" not in caplog.text


def test_p_unit(sma):
    """Power unit stays available."""
    sma.p_unit = "DBUV"
    assert sma.transport.written == ["UNIT:POW DBUV"]
    with pytest.raises(RuntimeError):
        sma.p_unit = "W"


def test_sweep_trigger(sma):
    """One-off sweep sends *TRG."""
    sma.sweep()
    assert sma.transport.written == ["*TRG"]


def test_scpi_common(sma):
    """Common SCPI commands come from SCPIInstrument."""
    sma.reset(defaults=False)
    sma.clear()
    sma.wait()
    assert sma.is_completed is False
    assert sma.transport.written == ["*RST", "*CLS", "*WAI", "*OPC?"]
