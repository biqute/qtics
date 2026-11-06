"""Test the Tektronix DPO3014 driver with a fake transport."""

import numpy as np
import pytest

from qtics import DPO3014
from qtics.transport import FakeTransport, SocketTransport

PREAMBLE = {
    "WFMOutpre:YMUlt?": "0.01",
    "WFMOutpre:YOFf?": "10",
    "WFMOutpre:YZEro?": "0.5",
    "WFMOutpre:XINcr?": "1E-6",
    "WFMOutpre:XZEro?": "-2E-6",
    "WFMOutpre:PT_Off?": "0",
}


def binblock(data: bytes) -> bytes:
    """Encode bytes as an IEEE 488.2 definite-length block with a final newline."""
    size = str(len(data))
    return b"#" + str(len(size)).encode() + size.encode() + data + b"\n"


def make(answers=None):
    """Oscilloscope on an open fake transport, no setup commands sent."""
    inst = DPO3014(FakeTransport(answers))
    inst.transport.connect()
    return inst


def test_transport_defaults():
    """Socket transport on the socket server port, nothing opened."""
    inst = DPO3014("127.0.0.1")
    assert isinstance(inst.transport, SocketTransport)
    assert inst.transport.port == 4000
    assert inst.transport.timeout == 10
    assert inst.name == "DPO3014"
    assert not inst.is_connected


def test_connect_hook():
    """Connecting switches the headers off."""
    inst = DPO3014(FakeTransport())
    inst.connect()
    assert inst.transport.written == ["HEADer OFF", "VERBose ON"]


def test_channel_commands():
    """Channel properties send the CH<n> commands."""
    inst = make({"CH2:SCAle?": "1.0E-1", "SELect:CH2?": "1", "CH2:COUPling?": "DC"})
    channel = inst.channel(2)
    assert channel is inst.channel(2)
    channel.scale = 0.5
    channel.offset = 0.1
    channel.position = 1
    channel.coupling = "ac"
    channel.termination = 50
    channel.termination = 1_000_000
    channel.bandwidth = "twenty"
    channel.enabled = False
    assert channel.scale == pytest.approx(0.1)
    assert channel.enabled is True
    assert channel.coupling == "DC"
    assert inst.transport.written[:8] == [
        "CH2:SCAle 0.5",
        "CH2:OFFSet 0.1",
        "CH2:POSition 1",
        "CH2:COUPling AC",
        "CH2:TERmination FIFty",
        "CH2:TERmination MEG",
        "CH2:BANdwidth TWEnty",
        "SELect:CH2 0",
    ]


def test_validation():
    """Invalid channels and options are rejected."""
    inst = make()
    for bad in (0, 5):
        with pytest.raises(RuntimeError):
            inst.channel(bad)
    with pytest.raises(RuntimeError):
        inst.channel(1).coupling = "XX"
    with pytest.raises(RuntimeError):
        inst.channel(1).termination = 75
    with pytest.raises(RuntimeError):
        inst.record_length = 1234
    with pytest.raises(RuntimeError):
        inst.trigger_slope = "UP"
    with pytest.raises(RuntimeError):
        inst.measure("BOGUS")
    with pytest.raises(RuntimeError):
        inst.read_waveform(5)
    with pytest.raises(RuntimeError):
        inst.read_waveform(1, width=4)
    assert inst.transport.written == []


def test_horizontal_and_trigger():
    """Timebase and trigger properties send and parse the commands."""
    inst = make(
        {
            "HORizontal:SCAle?": "2.0E-6",
            "HORizontal:RECOrdlength?": "10000",
            "TRIGger:A:EDGe:SLOpe?": "RISE",
            "TRIGger:A:LEVel?": "1.0E-1",
        }
    )
    inst.horizontal_scale = 1e-3
    inst.record_length = 10000
    inst.horizontal_position = 50
    inst.trigger_source = "ch1"
    inst.trigger_slope = "FALL"
    inst.trigger_mode = "NORMAL"
    inst.trigger_level = 0.2
    inst.force_trigger()
    assert inst.horizontal_scale == pytest.approx(2e-6)
    assert inst.record_length == 10000
    assert inst.trigger_slope == "RISE"
    assert inst.trigger_level == pytest.approx(0.1)
    assert inst.transport.written[:8] == [
        "HORizontal:SCAle 0.001",
        "HORizontal:RECOrdlength 10000",
        "HORizontal:POSition 50",
        "TRIGger:A:EDGe:SOUrce CH1",
        "TRIGger:A:EDGe:SLOpe FALL",
        "TRIGger:A:MODe NORMal",
        "TRIGger:A:LEVel 0.2",
        "TRIGger FORCe",
    ]


def test_acquisition_commands():
    """Acquisition settings and run/stop."""
    inst = make({"ACQuire:NUMAVg?": "16"})
    inst.acquire_mode = "average"
    inst.averages = 16
    inst.run()
    inst.stop()
    assert inst.averages == 16
    assert inst.transport.written[:6] == [
        "ACQuire:MODe AVErage",
        "ACQuire:NUMAVg 16",
        "ACQuire:STOPAfter RUNSTop",
        "ACQuire:STATE ON",
        "ACQuire:STATE OFF",
        "ACQuire:NUMAVg?",
    ]


def test_single_waits_for_completion():
    """single() polls the acquisition state until it is stopped."""
    states = iter(["1", "1", "0"])
    inst = make({"ACQuire:STATE?": lambda _: next(states)})
    inst.single(timeout=1, poll=0)
    assert inst.transport.written[:2] == [
        "ACQuire:STOPAfter SEQuence",
        "ACQuire:STATE ON",
    ]
    assert inst.transport.written.count("ACQuire:STATE?") == 3


def test_single_timeout():
    """single() stops the acquisition and raises if no trigger arrives."""
    inst = make({"ACQuire:STATE?": "1"})
    with pytest.raises(TimeoutError):
        inst.single(timeout=0, poll=0)
    assert inst.transport.written[-1] == "ACQuire:STATE OFF"


def test_read_waveform_scaling():
    """The binary block is converted with the WFMOutpre scaling."""
    raw = np.array([10, 20, -30, 127], dtype=">i1")
    answers = {
        **PREAMBLE,
        "HORizontal:RECOrdlength?": "4",
        "CURVe?": binblock(raw.tobytes()),
    }
    inst = make(answers)
    times, volts = inst.read_waveform(3)
    np.testing.assert_allclose(volts, 0.5 + 0.01 * (raw - 10))
    np.testing.assert_allclose(times, -2e-6 + 1e-6 * np.arange(4))
    assert inst.transport.written[:6] == [
        "DATa:SOUrce CH3",
        "DATa:ENCdg RIBinary",
        "DATa:WIDth 1",
        "DATa:STARt 1",
        "HORizontal:RECOrdlength?",
        "DATa:STOP 4",
    ]


def test_read_waveform_two_bytes():
    """Two bytes per point are decoded as big-endian signed integers."""
    raw = np.array([-300, 0, 25000], dtype=">i2")
    inst = make(
        {**PREAMBLE, "HORizontal:RECOrdlength?": "3", "CURVe?": binblock(raw.tobytes())}
    )
    _, volts = inst.read_waveform(1, width=2)
    np.testing.assert_allclose(volts, 0.5 + 0.01 * (raw - 10))
    assert "DATa:WIDth 2" in inst.transport.written


def test_read_waveform_bad_block():
    """A CURVe? answer that is not a binary block is an error."""
    inst = make({**PREAMBLE, "HORizontal:RECOrdlength?": "1", "CURVe?": b"1234"})
    with pytest.raises(ValueError):
        inst.read_waveform(1)


def test_acquire():
    """acquire() runs a single sequence and reads every channel."""
    raw = np.array([1, 2], dtype=">i1")
    inst = make(
        {
            **PREAMBLE,
            "ACQuire:STATE?": "0",
            "HORizontal:RECOrdlength?": "2",
            "CURVe?": lambda _: binblock(raw.tobytes()),
        }
    )
    data = inst.acquire([1, 2], timeout=1)
    assert set(data) == {1, 2}
    assert len(data[2][1]) == 2
    assert "DATa:SOUrce CH2" in inst.transport.written


def test_measure():
    """measure() selects source and type, then reads the value."""
    inst = make({"MEASUrement:IMMed:VALue?": "1.5E+3"})
    assert inst.measure("frequency", 2) == pytest.approx(1500)
    assert inst.transport.written == [
        "MEASUrement:IMMed:SOUrce1 CH2",
        "MEASUrement:IMMed:TYPe FREQuency",
        "MEASUrement:IMMed:VALue?",
    ]


def test_measure_error_is_nan():
    """The instrument error value 9.9E37 becomes NaN."""
    inst = make({"MEASUrement:IMMed:VALue?": "9.9E+37"})
    assert np.isnan(inst.measure("PK2Pk"))
