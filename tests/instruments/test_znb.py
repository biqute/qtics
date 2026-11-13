"""Test the R&S ZNB driver with a fake transport."""

import numpy as np
import pytest

from qtics import RSZNB, ZNB
from qtics.instruments.types import VNA
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


def make(answers=None, **kwargs):
    """ZNB on an open fake transport, no setup commands sent."""
    inst = ZNB(FakeTransport({"*OPC?": "1", **(answers or {})}), **kwargs)
    inst.transport.connect()
    return inst


@pytest.fixture
def znb():
    """ZNB answering 0 to its queries."""
    inst = ZNB(FakeTransport(default=reply))
    inst.transport.connect()
    return inst


def test_transport_defaults():
    """Socket transport with port 5025 and a 10 s timeout, nothing opened."""
    inst = ZNB("127.0.0.1")
    assert isinstance(inst.transport, SocketTransport)
    assert inst.transport.port == 5025
    assert inst.transport.timeout == 10
    assert inst.transport.delay == 0.1
    assert inst.name == "ZNB"
    assert not inst.is_connected


def test_type_interface_and_alias():
    """ZNB is a VNA, RSZNB is the legacy alias."""
    assert issubclass(ZNB, VNA)
    assert RSZNB is ZNB


def test_connect_setup():
    """Connecting clears, resets and configures the default trace."""
    inst = ZNB(FakeTransport(default=reply))
    inst.connect()
    written = inst.transport.written
    assert written.index("*CLS") < written.index("*RST")
    for cmd in (
        "CALCulate1:PARameter:SDEFine 'Trc1', 'S21'",
        "DISPlay:WINDow1:TRACe1:FEED 'Trc1'",
        "CALCulate1:PARameter:MEASure 'Trc1', 'S21'",
        "CALCulate1:FORMat MLOG",
        "SENSe1:AVERage:STATe OFF",
    ):
        assert cmd in written
    assert written[-1] == "FORMat:DATA REAL,64"
    inst.disconnect()
    assert not inst.is_connected


def test_f_center(znb):
    """Center frequency is set directly, keeping the span."""
    znb.f_center = 5e9
    assert znb.transport.written == ["SENSe1:FREQuency:CENTer 5000000000.0"]


def test_f_span_keeps_center():
    """Span is applied symmetrically around the current center."""
    inst = make({"SENSe1:FREQuency:STARt?": "4e9", "SENSe1:FREQuency:STOP?": "8e9"})
    assert inst.f_center == 6e9
    assert inst.f_span == 4e9
    inst.f_span = 2e9
    assert inst.transport.written[-2:] == [
        "SENSe1:FREQuency:STARt 5000000000.0",
        "SENSe1:FREQuency:STOP 7000000000.0",
    ]


def test_list_traces():
    """Catalog response is a quoted string."""
    inst = make({"CALCulate1:PARameter:CATalog?": "'Trc1,S21,Trc2,S11'"})
    assert inst.list_traces() == [("Trc1", "S21"), ("Trc2", "S11")]


def test_autoscale(znb):
    """Autoscale window trace 1 by default, or the given one."""
    znb.autoscale()
    znb.autoscale(2)
    assert znb.transport.written == [
        "DISPlay:WINDow1:TRACe1:Y:SCALe:AUTO ONCE",
        "DISPlay:WINDow1:TRACe2:Y:SCALe:AUTO ONCE",
    ]


@pytest.mark.parametrize(
    "attr, query, answer, value, setter",
    [
        (
            "f_start",
            "SENSe1:FREQuency:STARt?",
            "4e9",
            4e9,
            "SENSe1:FREQuency:STARt 4000000000.0",
        ),
        (
            "f_stop",
            "SENSe1:FREQuency:STOP?",
            "8e9",
            8e9,
            "SENSe1:FREQuency:STOP 8000000000.0",
        ),
        ("points", "SENSe1:SWEep:POINts?", "1001", 1001, "SENSe1:SWEep:POINts 1001"),
        ("averages", "SENSe1:AVERage:COUNt?", "5", 5, "SENSe1:AVERage:COUNt 5"),
        (
            "ifbw",
            "SENSe1:BANDwidth:RESolution?",
            "1000",
            1000.0,
            "SENSe1:BANDwidth:RESolution 1000.0",
        ),
        (
            "power",
            "SOURce1:POWer:LEVel:IMMediate:AMPLitude?",
            "-20",
            -20.0,
            "SOURce1:POWer:LEVel:IMMediate:AMPLitude -20.0",
        ),
    ],
)
def test_properties(attr, query, answer, value, setter):
    """Properties return numbers and send the SCPI command on set."""
    inst = make({query: answer})
    got = getattr(inst, attr)
    assert got == value
    assert isinstance(got, int if attr in ("points", "averages") else float)
    assert inst.transport.written == [query]
    setattr(inst, attr, value)
    assert setter in inst.transport.written[1:]


def test_averages_switch_state():
    """Averaging is enabled only above one average."""
    inst = make()
    inst.averages = 4
    inst.averages = 1
    assert inst.transport.written == [
        "SENSe1:AVERage:COUNt 4",
        "SENSe1:AVERage:STATe ON",
        "SENSe1:AVERage:COUNt 1",
        "SENSe1:AVERage:STATe OFF",
    ]


def test_s_parameter():
    """The S parameter of the active trace."""
    inst = make({"CALCulate1:PARameter:MEASure? 'Trc1'": "'S21'"})
    assert inst.s_parameter == "S21"
    inst.s_parameter = "S11"
    assert inst.transport.written[-1] == "CALCulate1:PARameter:MEASure 'Trc1', 'S11'"


def test_channel_option():
    """The channel is a constructor keyword."""
    inst = make(channel=2)
    inst.points = 11
    assert inst.transport.written == ["SENSe2:SWEep:POINts 11"]


def test_points_clipped_to_max_points():
    """Number of points is limited by max_points."""
    inst = make(max_points=201)
    inst.points = 5000
    assert inst.transport.written == ["SENSe1:SWEep:POINts 201"]


@pytest.mark.parametrize("answer, expected", [("1", True), ("0", False)])
def test_continuous(answer, expected):
    """Acquisition mode is a bool."""
    inst = make({"INITiate1:CONTinuous?": answer})
    assert inst.continuous is expected
    inst.continuous = True
    assert inst.transport.written[-2:] == ["INITiate1:CONTinuous 1", "*OPC?"]


@pytest.mark.parametrize("answer, expected", [("1", True), ("0", False)])
def test_time_domain_and_harmonic_grid_are_bool(answer, expected):
    """On/off properties return bool and accept bool."""
    inst = make(
        {
            "CALCulate1:TRANsform:TIME:STATe?": answer,
            "SENSe1:HARMonic:AUTO?": answer,
        }
    )
    assert inst.time_domain is expected
    assert inst.harmonic_grid is expected
    inst.time_domain = True
    inst.harmonic_grid = False
    assert inst.transport.written[-2:] == [
        "CALCulate1:TRANsform:TIME:STATe ON",
        "SENSe1:HARMonic:AUTO OFF",
    ]


def test_time_axis_properties():
    """Time axis limits are t_start and t_stop."""
    inst = make({"CALCulate1:TRANsform:TIME:STARt?": "-1e-9"})
    assert inst.t_start == -1e-9
    inst.t_start = 0
    inst.t_stop = 1e-9
    assert inst.transport.written[-2:] == [
        "CALCulate1:TRANsform:TIME:STARt 0",
        "CALCulate1:TRANsform:TIME:STOP 1e-09",
    ]


def test_sweep_averaging():
    """With averages the old trace is cleared and one sweep is run per average."""
    inst = make({"SENSe1:AVERage:COUNt?": "3", "INITiate1:CONTinuous?": "0"})
    inst.sweep()
    written = inst.transport.written
    assert "SENSe1:AVERage:CLEar" in written
    assert written.count("INITiate1:IMMediate") == 3


def test_sweep_single():
    """Without averages a single sweep is triggered and awaited."""
    inst = make({"SENSe1:AVERage:COUNt?": "1", "INITiate1:CONTinuous?": "0"})
    inst.sweep()
    assert "SENSe1:AVERage:CLEar" not in inst.transport.written
    assert inst.transport.written.count("INITiate1:IMMediate") == 1


def test_sweep_continuous_waits(mocker):
    """In continuous mode the sweep time is waited instead of triggering."""
    sleep = mocker.patch("qtics.instruments.rohde_schwarz.znb.time.sleep")
    inst = make(
        {
            "SENSe1:AVERage:COUNt?": "2",
            "INITiate1:CONTinuous?": "1",
            "SENSe1:SWEep:TIME?": "0.5",
        }
    )
    inst.sweep()
    assert "INITiate1:IMMediate" not in inst.transport.written
    sleep.assert_called_with(pytest.approx(0.5 * 2 * 1.02))


def test_read_trace_complex():
    """Raw IQ data is returned as complex numbers."""
    inst = make({"CALCulate1:DATA? SDATa": binblock([1, 2, 3, 4])})
    z = inst.read_trace_data()
    np.testing.assert_array_equal(z, [1 + 2j, 3 + 4j])
    assert "FORMat:DATA REAL,64" in inst.transport.written
    assert "CALCulate1:PARameter:SELect 'Trc1'" in inst.transport.written


def test_read_trace_formatted():
    """Formatted data selects the format first."""
    inst = make({"CALCulate1:DATA? FDATa": binblock([-3.0, -4.0])})
    np.testing.assert_array_equal(inst.read_trace_data("MLOG"), [-3.0, -4.0])
    assert inst.transport.written[0] == "CALCulate1:FORMat MLOG"


def test_snapshot_returns_freqs_and_data():
    """Snapshot sets parameters, sweeps once and returns (freqs, data)."""
    inst = make(
        {
            "SENSe1:AVERage:COUNt?": "1",
            "INITiate1:CONTinuous?": "0",
            "CALCulate1:DATA? SDATa": binblock([1, 2, 3, 4]),
            "SENSe1:FREQuency:STARt?": "1e9",
            "SENSe1:FREQuency:STOP?": "3e9",
            "SENSe1:SWEep:POINts?": "3",
        }
    )
    f, z = inst.snapshot(f_start=1e9, f_stop=3e9)
    assert inst.transport.written.count("INITiate1:IMMediate") == 1
    assert "SENSe1:FREQuency:STARt 1000000000.0" in inst.transport.written
    np.testing.assert_array_equal(f, [1e9, 2e9, 3e9])
    np.testing.assert_array_equal(z, [1 + 2j, 3 + 4j])
