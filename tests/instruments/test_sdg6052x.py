"""Test the SDG6052X driver."""

import numpy as np
import pytest

from qtics import SDG6052X
from qtics.instruments.siglent.sdg6052x import parse_params
from qtics.transport import FakeTransport, SocketTransport

BSWV = (
    "C1:BSWV WVTP,SINE,FRQ,1000HZ,PERI,0.001S,AMP,2V,AMPVRMS,0.707Vrms,"
    "OFST,-0.5V,HLEV,0.5V,LLEV,-1.5V,PHSE,90"
)


class BytesTransport(FakeTransport):
    """Fake transport keeping the raw bytes of the writes."""

    def __init__(self, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)
        self.raw_written = []

    def _write_bytes(self, data: bytes):
        self.raw_written.append(data)
        if data.isascii():
            super()._write_bytes(data)


@pytest.fixture
def awg():
    """Connected SDG6052X on a fake transport."""
    inst = SDG6052X(BytesTransport(default="0"))
    inst.transport.connect()
    return inst


def test_transport_defaults():
    """Address string builds a socket transport on port 5025."""
    inst = SDG6052X("127.0.0.1")
    assert isinstance(inst.transport, SocketTransport)
    assert inst.transport.port == 5025


def test_parse_basic_wave():
    """Units are stripped and numbers converted."""
    assert parse_params(BSWV) == {
        "WVTP": "SINE",
        "FRQ": 1000.0,
        "PERI": 0.001,
        "AMP": 2.0,
        "AMPVRMS": 0.707,
        "OFST": -0.5,
        "HLEV": 0.5,
        "LLEV": -1.5,
        "PHSE": 90.0,
    }


def test_parse_scientific_and_off():
    """Exponents and the short answer of a disabled mode are handled."""
    assert parse_params("C2:BTWV STATE,ON,PRD,2.4e-07S,TIME,INF")["PRD"] == 2.4e-7
    assert parse_params("C2:BTWV STATE,OFF") == {"STATE": "OFF"}


def test_parse_modulation():
    """Modulation type is kept and the carrier is nested."""
    params = parse_params(
        "C1:MDWV STATE,ON,AM,MDSP,SINE,SRC,INT,FRQ,100HZ,DEPTH,100,"
        "CARR,WVTP,RAMP,FRQ,1000HZ,AMP,4V"
    )
    assert params["TYPE"] == "AM"
    assert params["FRQ"] == 100.0
    assert params["CARR"] == {"WVTP": "RAMP", "FRQ": 1000.0, "AMP": 4.0}


def test_channel_validation(awg):
    """Only channels 1 and 2 exist."""
    assert awg.channel(2).number == 2
    for n in (0, 3):
        with pytest.raises(RuntimeError):
            awg.channel(n)


def test_output(awg):
    """Output state, load and polarity are parsed from OUTP?."""
    ch = awg.channel(1)
    awg.transport.answers["C1:OUTP?"] = "C1:OUTP ON,LOAD,HZ,PLRT,NOR"
    assert ch.output is True
    assert ch.load == "HZ"
    assert ch.polarity == "NOR"
    awg.transport.answers["C1:OUTP?"] = "C1:OUTP OFF,LOAD,50,PLRT,INVT"
    assert ch.output is False
    assert ch.load == 50.0
    ch.output = True
    ch.load = "HZ"
    ch.load = 50
    ch.polarity = "INVT"
    assert awg.transport.written[-4:] == [
        "C1:OUTP ON",
        "C1:OUTP LOAD,HZ",
        "C1:OUTP LOAD,50",
        "C1:OUTP PLRT,INVT",
    ]


def test_basic_wave(awg):
    """Basic wave getters parse BSWV?, setters send BSWV commands."""
    ch = awg.channel(1)
    awg.transport.answers["C1:BSWV?"] = BSWV
    assert ch.waveform == "SINE"
    assert ch.frequency == 1000.0
    assert ch.amplitude == 2.0
    assert ch.offset == -0.5
    assert ch.phase == 90.0
    ch.waveform = "SQUARE"
    ch.frequency = 1e6
    ch.amplitude = 0.1
    ch.offset = 0
    ch.duty = 25
    assert awg.transport.written[-5:] == [
        "C1:BSWV WVTP,SQUARE",
        "C1:BSWV FRQ,1000000.0",
        "C1:BSWV AMP,0.1",
        "C1:BSWV OFST,0",
        "C1:BSWV DUTY,25",
    ]
    with pytest.raises(RuntimeError):
        ch.waveform = "TRIANGLE"


def test_channel_two_command(awg):
    """The channel number is in the command prefix."""
    awg.channel(2).frequency = 10
    assert awg.transport.written[-1] == "C2:BSWV FRQ,10"


def test_missing_parameter(awg):
    """A parameter absent from the answer raises an explicit error."""
    awg.transport.answers["C1:BTWV?"] = "C1:BTWV STATE,OFF"
    assert awg.channel(1).burst_enable is False
    with pytest.raises(RuntimeError, match="PRD"):
        awg.channel(1).burst_period


def test_burst(awg):
    """Burst commands."""
    ch = awg.channel(1)
    awg.transport.answers["C1:BTWV?"] = "C1:BTWV STATE,ON,PRD,0.01S,TRSR,MAN,TIME,5"
    assert ch.burst_enable
    assert ch.burst_cycles == 5
    assert ch.burst_period == 0.01
    assert ch.burst_trigger_source == "MAN"
    ch.burst_enable = True
    ch.burst_cycles = "inf"
    ch.burst_trigger_source = "EXT"
    ch.trigger_burst()
    assert awg.transport.written[-4:] == [
        "C1:BTWV STATE,ON",
        "C1:BTWV TIME,INF",
        "C1:BTWV TRSR,EXT",
        "C1:BTWV MTRIG",
    ]


def test_sweep(awg):
    """Sweep commands."""
    ch = awg.channel(2)
    awg.transport.answers["C2:SWWV?"] = (
        "C2:SWWV STATE,ON,TIME,1S,STOP,100HZ,START,10HZ,TRSR,MAN,"
        "TRMD,OFF,SWMD,LINE,DIR,UP,CARR,WVTP,SQUARE,FRQ,1000HZ"
    )
    assert (ch.sweep_start, ch.sweep_stop, ch.sweep_time) == (10, 100, 1)
    assert ch.sweep_mode == "LINE"
    assert ch.sweep_direction == "UP"
    ch.sweep_enable = True
    ch.sweep_mode = "LOG"
    ch.sweep_start = 1e3
    ch.trigger_sweep()
    assert awg.transport.written[-4:] == [
        "C2:SWWV STATE,ON",
        "C2:SWWV SWMD,LOG",
        "C2:SWWV START,1000.0",
        "C2:SWWV MTRIG",
    ]


def test_modulation(awg):
    """Modulation commands use the current modulation type."""
    ch = awg.channel(1)
    awg.transport.answers["C1:MDWV?"] = (
        "C1:MDWV STATE,ON,FM,MDSP,SINE,SRC,INT,FRQ,10HZ,DEVI,500HZ,CARR,WVTP,SINE"
    )
    assert ch.mod_type == "FM"
    assert ch.mod_frequency == 10
    assert ch.mod_deviation == 500
    ch.mod_type = "AM"
    assert awg.transport.written[-1] == "C1:MDWV AM"
    ch.mod_deviation = 1e3
    assert awg.transport.written[-1] == "C1:MDWV FM,DEVI,1000.0"
    ch.mod_frequency = 20
    assert awg.transport.written[-1] == "C1:MDWV FM,FRQ,20"
    with pytest.raises(RuntimeError):
        ch.mod_depth = 50  # type is FM in the scripted answer


def test_upload_waveform(awg):
    """WVDT carries 16-bit little-endian samples, then the waveform is selected."""
    data = np.array([-1, -0.5, 0, 0.5, 1, 2, -2, 0.25])
    awg.channel(2).upload_waveform(data, "wave_1", amplitude=0.2)
    payload = awg.transport.raw_written[0]
    header = (
        b"C2:WVDT WVNM,wave_1,FREQ,1000.0,TYPE,8,AMPL,0.2,OFST,0.0,PHASE,0.0,WAVEDATA,"
    )
    assert payload.startswith(header)
    assert payload.endswith(b"\n")
    samples = np.frombuffer(payload[len(header) : -1], dtype="<i2")
    assert list(samples) == [-32767, -16384, 0, 16384, 32767, 32767, -32767, 8192]
    assert awg.transport.written == ["C2:ARWV NAME,wave_1", "C2:BSWV WVTP,ARB"]


def test_upload_waveform_invalid(awg):
    """Bad names and data are rejected before writing."""
    ch = awg.channel(1)
    with pytest.raises(ValueError):
        ch.upload_waveform(np.zeros(16), "bad name")
    with pytest.raises(ValueError):
        ch.upload_waveform(np.zeros(3), "short")
    with pytest.raises(ValueError):
        ch.upload_waveform(np.zeros((4, 4)), "twod")
    assert awg.transport.raw_written == []
