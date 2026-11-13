"""Test the R&S FSV3030 driver with a fake transport."""

import numpy as np
import pytest

from qtics import FSV3030
from qtics.instruments.types import SpectrumAnalyzer
from qtics.transport import FakeTransport, SocketTransport


def make(answers=None, **kwargs):
    """FSV3030 on an open fake transport."""
    inst = FSV3030(FakeTransport(answers), **kwargs)
    inst.transport.connect()
    return inst


@pytest.fixture
def fsv():
    """FSV3030 answering 0 to every command."""
    inst = FSV3030(FakeTransport(default="0"))
    inst.transport.connect()
    return inst


def test_transport_defaults():
    """Socket transport with port 5025 and a 10 s timeout, nothing opened."""
    inst = FSV3030("127.0.0.1")
    assert isinstance(inst.transport, SocketTransport)
    assert inst.transport.port == 5025
    assert inst.transport.timeout == 10
    assert inst.transport.delay == 0.1
    assert inst.name == "FSV3030"
    assert not inst.is_connected


def test_type_interface():
    """FSV3030 is a spectrum analyzer."""
    assert issubclass(FSV3030, SpectrumAnalyzer)


def test_connect_sends_nothing():
    """The driver has no setup commands."""
    inst = FSV3030(FakeTransport())
    inst.connect()
    inst.disconnect()
    assert inst.transport.written == []


def test_sweep_commands(fsv):
    """A sweep switches continuous mode off, triggers and waits."""
    fsv.sweep()
    assert fsv.transport.written == ["INIT:CONT OFF", "INIT:IMM", "*WAI"]


def test_snapshot_single_sweep(mocker):
    """Snapshot must sweep once and return (freqs, trace)."""
    inst = make(
        {
            "FREQ:STAR?": "1e9",
            "FREQ:STOP?": "3e9",
            "SWE:POIN?": "3",
            "TRAC? TRACE1": "-50,-60,-70",
        }
    )
    sweep = mocker.spy(inst, "sweep")
    f, z = inst.snapshot()
    assert sweep.call_count == 1
    assert inst.transport.written.count("INIT:IMM") == 1
    np.testing.assert_array_equal(f, [1e9, 2e9, 3e9])
    np.testing.assert_array_equal(z, [-50, -60, -70])


def test_read_trace_does_not_sweep():
    """Reading the trace only queries it."""
    inst = make({"TRAC? TRACE2": "-1.5,-2.5"})
    np.testing.assert_array_equal(inst.read_trace_data(2), [-1.5, -2.5])
    assert inst.transport.written == ["TRAC? TRACE2"]


def test_max_hold_flow():
    """Max-hold: set (sweeps), more sweeps, read without resetting."""
    inst = make({"TRAC? TRACE1": "-40,-30"})
    inst.set_max_hold()
    assert inst.transport.written == [
        "TRAC1:MODE MAXH",
        "INIT:CONT OFF",
        "INIT:IMM",
        "*WAI",
    ]
    inst.sweep()
    inst.transport.written.clear()
    np.testing.assert_array_equal(inst.read_max_hold(), [-40, -30])
    assert inst.transport.written == ["TRAC? TRACE1"]


def test_clear_max_hold():
    """Clearing returns the trace to write mode and sweeps."""
    inst = make()
    inst.clear_max_hold(2)
    assert inst.transport.written[0] == "TRAC2:MODE WRIT"
    assert "INIT:IMM" in inst.transport.written


def test_read_max_hold_keeps_trace(fsv):
    """Reading the max-hold trace must not reset it."""
    fsv.query = lambda cmd: "0"
    fsv.read_max_hold()
    assert all("MODE" not in c for c in fsv.transport.written)


@pytest.mark.parametrize("answer, expected", [("1", True), ("0", False), ("ON", True)])
def test_continuous_property(answer, expected):
    """Continuous is a bool property."""
    inst = make({"INIT:CONT?": answer})
    assert inst.continuous is expected
    inst.continuous = True
    inst.continuous = False
    assert inst.transport.written[-2:] == ["INIT:CONT 1", "INIT:CONT 0"]


@pytest.mark.parametrize(
    "attr, query, answer, value, setter",
    [
        ("f_start", "FREQ:STAR?", "1e9", 1e9, "FREQ:STAR 1000000000.0"),
        ("f_stop", "FREQ:STOP?", "2e9", 2e9, "FREQ:STOP 2000000000.0"),
        ("f_center", "FREQ:CENT?", "1.5e9", 1.5e9, "FREQ:CENT 1500000000.0"),
        ("f_span", "FREQ:SPAN?", "1e9", 1e9, "FREQ:SPAN 1000000000.0"),
        ("rbw", "BAND:RES?", "1000", 1000.0, "BAND:RES 1000.0"),
        ("vbw", "BAND:VID?", "3000", 3000.0, "BAND:VID 3000.0"),
        ("points", "SWE:POIN?", "1001", 1001, "SWE:POIN 1001"),
        ("sweep_time", "SWE:TIME?", "0.5", 0.5, "SWE:TIME 0.5"),
        (
            "ref_level",
            "DISP:WIND:TRAC:Y:SCAL:RLEV?",
            "-10",
            -10.0,
            "DISP:WIND:TRAC:Y:SCAL:RLEV -10.0",
        ),
    ],
)
def test_properties(attr, query, answer, value, setter):
    """Properties return numbers and send the SCPI command on set."""
    inst = make({query: answer})
    got = getattr(inst, attr)
    assert got == value
    assert isinstance(got, int if attr == "points" else float)
    setattr(inst, attr, value)
    assert inst.transport.written[-1] == setter


def test_range_is_clipped(caplog):
    """Out of range values are clipped with a warning."""
    inst = make()
    inst.points = 50
    assert inst.transport.written == ["SWE:POIN 101"]
    assert "not in range" in caplog.text


def test_markers_and_scpi_commons():
    """Marker queries and the inherited SCPI commands."""
    inst = make({"CALC:MARK1:X?": "1e9", "CALC:MARK2:Y?": "-30", "*OPC?": "1"})
    inst.marker_to_peak()
    assert inst.marker_freq() == 1e9
    assert inst.marker_power(2) == -30.0
    assert inst.is_completed is True
    inst.clear()
    assert inst.transport.written[0] == "CALC:MARK1:MAX"
    assert inst.transport.written[-1] == "*CLS"
