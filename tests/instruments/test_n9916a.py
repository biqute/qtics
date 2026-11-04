"""Test the N9916A drivers (VNA and SA modes) with a fake transport."""

import numpy as np
import pytest

from qtics import SAN9916A, VNAN9916A
from qtics.instruments.keysight.n9916a import N9916A
from qtics.instruments.types import VNA, SpectrumAnalyzer
from qtics.transport import FakeTransport, SocketTransport


def binblock(values) -> bytes:
    """Encode float64 values as an IEEE 488.2 binary block."""
    data = np.asarray(values, dtype=np.float64).tobytes()
    size = str(len(data))
    return b"#" + str(len(size)).encode() + size.encode() + data + b"\n"


def reply(cmd):
    """Answer queries only: 1 to *OPC?, 0 to the others."""
    if cmd == "*OPC?":
        return "1"
    return "0" if "?" in cmd else None


def make(cls, answers=None, **kwargs):
    """Instrument on an open fake transport, no setup commands sent."""
    inst = cls(FakeTransport({"*OPC?": "1", **(answers or {})}), **kwargs)
    inst.transport.connect()
    return inst


@pytest.fixture
def sa():
    """SAN9916A answering 0 to its queries."""
    inst = SAN9916A(FakeTransport(default=reply))
    inst.transport.connect()
    return inst


@pytest.fixture
def vna():
    """VNAN9916A answering 0 to its queries."""
    inst = VNAN9916A(FakeTransport(default=reply))
    inst.transport.connect()
    return inst


@pytest.mark.parametrize("cls", [VNAN9916A, SAN9916A])
def test_transport_defaults(cls):
    """Socket transport with port 5025 and a 10 s timeout, nothing opened."""
    inst = cls("127.0.0.1")
    assert isinstance(inst.transport, SocketTransport)
    assert inst.transport.port == 5025
    assert inst.transport.timeout == 10
    assert inst.transport.delay == 0.1
    assert not inst.is_connected
    assert inst.name == cls.__name__


def test_type_interfaces():
    """The modes implement the swept analyzer interfaces."""
    assert issubclass(VNAN9916A, VNA) and issubclass(VNAN9916A, N9916A)
    assert issubclass(SAN9916A, SpectrumAnalyzer) and issubclass(SAN9916A, N9916A)
    assert not issubclass(SAN9916A, VNA)


@pytest.mark.parametrize("cls", [VNAN9916A, SAN9916A])
def test_one_mode_at_a_time_documented(cls):
    """The docstring warns that only one mode class can be connected."""
    assert "only one" in cls.__doc__.lower()


def test_vna_connect_setup():
    """Connecting clears, resets, selects NA mode and configures the trace."""
    inst = VNAN9916A(FakeTransport(default=reply))
    inst.connect()
    written = inst.transport.written
    for cmd in ("*CLS", "*RST", 'INST:SEL "NA"', "CALC:PAR1:DEF S21", "BWID 1000"):
        assert cmd in written
    assert (
        written.index("*CLS") < written.index("*RST") < written.index('INST:SEL "NA"')
    )
    assert written[-1] == "FORM:DATA REAL,64"
    inst.disconnect()
    assert not inst.is_connected


def test_sa_connect_setup():
    """Connecting clears, resets, selects SA mode and single sweeps."""
    inst = SAN9916A(FakeTransport(default=reply))
    inst.connect()
    written = inst.transport.written
    for cmd in ("*CLS", "*RST", 'INST:SEL "SA"', "INIT:CONT 0", "TRAC1:TYPE AVG"):
        assert cmd in written
    assert written[-1] == "FORM:DATA REAL,64"


def test_auto_attenuation(sa):
    """Auto attenuation setter must send POW:ATT:AUTO."""
    sa.auto_attenuation = True
    assert sa.transport.written == ["POW:ATT:AUTO 1"]


def test_yscale(sa):
    """Amplitude scale command must not contain a stray colon."""
    sa.yscale = "LOG"
    assert sa.transport.written == ["AMPL:SCAL LOG"]


@pytest.mark.parametrize("attr", ["auto_attenuation", "gain", "auto_rbw", "continuous"])
def test_bool_getters(attr):
    """SCPI boolean queries answer 1/0 and return bool."""
    for answer, expected in (("1", True), ("0", False), ("ON", True)):
        inst = SAN9916A(FakeTransport(default=lambda cmd, a=answer: a))
        inst.transport.connect()
        assert getattr(inst, attr) is expected


@pytest.mark.parametrize(
    "attr, query, answer, value, setter",
    [
        ("f_start", "SENS:FREQ:START?", "4e9", 4e9, "SENS:FREQ:START 4000000000.0"),
        ("f_stop", "SENS:FREQ:STOP?", "8e9", 8e9, "SENS:FREQ:STOP 8000000000.0"),
        ("f_center", "SENS:FREQ:CENT?", "6e9", 6e9, "SENS:FREQ:CENT 6000000000.000000"),
        ("f_span", "SENS:FREQ:SPAN?", "4e9", 4e9, "SENS:FREQ:SPAN 4000000000.0"),
        ("points", "SENS:SWE:POIN?", "1001", 1001, "SWE:POIN 1001"),
        ("averages", "AVER:COUN?", "5", 5, "SENSE:AVER:COUN 5"),
    ],
)
@pytest.mark.parametrize("cls", [VNAN9916A, SAN9916A])
def test_common_properties(cls, attr, query, answer, value, setter):
    """Common properties return numbers and send the SCPI command on set."""
    inst = make(cls, {query: answer})
    got = getattr(inst, attr)
    assert got == value
    assert isinstance(got, int if attr in ("points", "averages") else float)
    assert inst.transport.written == [query]
    setattr(inst, attr, value)
    assert inst.transport.written[-1] == setter


def test_points_clipped_to_max_points():
    """Number of points is limited by max_points."""
    inst = make(VNAN9916A, max_points=201)
    inst.points = 5000
    assert inst.transport.written == ["SWE:POIN 201"]


def test_continuous_setter_holds():
    """Setting the acquisition mode waits for completion."""
    inst = make(SAN9916A)
    inst.continuous = False
    assert inst.transport.written == ["INIT:CONT 0", "*OPC?"]


def test_vna_properties():
    """VNA specific properties: s_parameter, ifbw, power."""
    inst = make(
        VNAN9916A,
        {"CALC:PAR1:DEF?": "S21", "BWID?": "1000", "SOUR:POW?": "-20"},
    )
    assert inst.s_parameter == "S21"
    assert inst.ifbw == 1000.0
    assert inst.power == -20.0
    inst.s_parameter = "S11"
    inst.ifbw = 500e3
    inst.power = 10
    assert inst.transport.written[-3:] == [
        "CALC:PAR1:DEF S11",
        "BWID 100000",
        "SOUR:POW 3",
    ]
    with pytest.raises(RuntimeError):
        inst.s_parameter = "S33"


def test_sa_rbw():
    """The resolution bandwidth is clipped and read as float."""
    inst = make(SAN9916A, {"BAND:RES?": "1000"})
    assert inst.rbw == 1000.0
    inst.rbw = 1e3
    inst.rbw = 5
    assert inst.transport.written[-2:] == ["BAND:RES 1000.0", "BAND:RES 10"]


def test_vna_sweep_swept_averaging():
    """Sweep mode averaging triggers one sweep per average."""
    inst = make(VNAN9916A, {"INIT:CONT?": "0", "AVER:COUN?": "3", "AVER:MODE?": "SWE"})
    inst.sweep()
    written = inst.transport.written
    assert written[0] == "AVER:CLE"
    assert written.count("INIT:IMM") == 3


def test_vna_sweep_point_averaging():
    """Point by point averaging needs a single trigger."""
    inst = make(
        VNAN9916A, {"INIT:CONT?": "0", "AVER:COUN?": "3", "AVER:MODE?": "POINT"}
    )
    inst.sweep()
    assert inst.transport.written.count("INIT:IMM") == 1


def test_vna_sweep_bad_average_mode():
    """Unknown average modes are an error."""
    inst = make(VNAN9916A, {"INIT:CONT?": "0", "AVER:COUN?": "1", "AVER:MODE?": "X"})
    with pytest.raises(RuntimeError):
        inst.sweep()


def test_sa_sweep_averages():
    """The SA restarts averaging and triggers one sweep per average."""
    inst = make(SAN9916A, {"INIT:CONT?": "0", "AVER:COUN?": "2"})
    inst.sweep()
    written = inst.transport.written
    assert written[0] == "INIT:REST"
    assert written.count("INIT:IMM") == 2


def test_sa_sweep_continuous_waits(mocker):
    """In continuous mode the SA waits the measurement time instead of triggering."""
    sleep = mocker.patch("qtics.instruments.keysight.n9916a.time.sleep")
    inst = make(SAN9916A, {"INIT:CONT?": "1", "AVER:COUN?": "2", "SWE:MTIME?": "0.5"})
    inst.sweep()
    assert "INIT:IMM" not in inst.transport.written
    sleep.assert_called_with(pytest.approx(0.5 * 2 * 1.02))


def test_vna_read_trace_complex():
    """Raw IQ data is returned as complex numbers."""
    inst = make(VNAN9916A, {"CALC:DATA:SDATA?": binblock([1, 2, 3, 4])})
    z = inst.read_trace_data()
    np.testing.assert_array_equal(z, [1 + 2j, 3 + 4j])
    assert "FORM:DATA REAL,64" in inst.transport.written


def test_vna_read_trace_formatted():
    """Formatted data selects the format first."""
    inst = make(VNAN9916A, {"CALC:DATA:FDATA?": binblock([-3.0, -4.0])})
    np.testing.assert_array_equal(inst.read_trace_data("MLOG"), [-3.0, -4.0])
    assert inst.transport.written[0] == "CALC:FORM MLOG"


def test_vna_read_freqs():
    """Frequencies are read as a binary block in the current data format."""
    inst = make(
        VNAN9916A,
        {"FORM:DATA?": "REAL,64", "FREQ:DATA?": binblock([1e9, 2e9])},
    )
    np.testing.assert_array_equal(inst.read_freqs(), [1e9, 2e9])


def test_sa_read_trace_and_freqs():
    """SA trace is a binary block, frequencies are computed."""
    inst = make(
        SAN9916A,
        {
            "TRAC1:DATA?": binblock([-50, -60, -70]),
            "SENS:FREQ:START?": "1e9",
            "SENS:FREQ:STOP?": "3e9",
            "SENS:SWE:POIN?": "3",
        },
    )
    np.testing.assert_array_equal(inst.read_trace_data(), [-50, -60, -70])
    np.testing.assert_array_equal(inst.read_freqs(), [1e9, 2e9, 3e9])


def test_sa_snapshot_returns_freqs_and_data():
    """Snapshot sets parameters, sweeps once and returns (freqs, data)."""
    inst = make(
        SAN9916A,
        {
            "INIT:CONT?": "0",
            "AVER:COUN?": "1",
            "TRAC1:DATA?": binblock([-50, -60, -70]),
            "SENS:FREQ:START?": "1e9",
            "SENS:FREQ:STOP?": "3e9",
            "SENS:SWE:POIN?": "3",
        },
    )
    f, z = inst.snapshot(f_start=1e9, f_stop=3e9)
    assert inst.transport.written.count("INIT:IMM") == 1
    written = inst.transport.written
    assert "SENS:FREQ:START 1000000000.0" in written
    assert "SENS:FREQ:STOP 3000000000.0" in written
    np.testing.assert_array_equal(f, [1e9, 2e9, 3e9])
    np.testing.assert_array_equal(z, [-50, -60, -70])


def test_set_full_and_zero_span(sa):
    """Span shortcuts."""
    sa.set_full_span()
    sa.set_zero_span()
    assert sa.transport.written == ["FREQ:SPAN:FULL", "FREQ:SPAN:ZERO"]
