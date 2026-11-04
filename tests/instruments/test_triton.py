"""Test the Triton driver."""

import pytest

from qtics.instruments.base import MessageInstrument
from qtics.instruments.oxford import triton as triton_module
from qtics.instruments.oxford.triton import Triton
from qtics.transport import SocketTransport
from qtics.transport.fake import FakeTransport


def make(answers):
    """Triton on a fake transport echoing each command before its answer."""
    fake = FakeTransport(
        answers={cmd: f"{cmd}:{reply}" for cmd, reply in answers.items()}, default=None
    )
    inst = Triton(fake)
    inst.transport.connect()
    return inst


def test_transport_defaults():
    """Address string builds a socket transport on port 33576, no default address."""
    inst = Triton("10.0.0.1")
    assert isinstance(inst.transport, SocketTransport)
    assert inst.transport.port == 33576
    assert inst.transport.timeout == 10
    assert inst.transport.delay == 0.1
    assert isinstance(inst, MessageInstrument)
    with pytest.raises(TypeError):
        Triton()  # pylint: disable=no-value-for-parameter


def test_query_strips_echo():
    """The echoed command is removed from the answer."""
    inst = make({"READ:SYS:DR:STATUS": "OK"})
    assert inst.get_state() == "OK"


def test_temperatures():
    """Temperatures drop the unit character and become floats."""
    inst = make(
        {
            "READ:DEV:T8:TEMP:SIG:TEMP": "0.0123K",
            "READ:DEV:T3:TEMP:SIG:TEMP": "0.8K",
            "READ:DEV:T5:TEMP:SIG:TEMP": "0.1K",
            "READ:DEV:T7:TEMP:SIG:TEMP": "3.5K",
            "READ:DEV:T2:TEMP:SIG:TEMP": "40K",
            "READ:DEV:T11:TEMP:SIG:TEMP": "5K",
        }
    )
    assert inst.get_mixing_chamber_temp() == pytest.approx(0.0123)
    assert inst.get_still_temp() == pytest.approx(0.8)
    assert inst.get_cool_temp() == pytest.approx(0.1)
    assert inst.get_pt1_temp() == pytest.approx(3.5)
    assert inst.get_pt2_temp() == pytest.approx(40)
    assert inst.get_sorb_temp() == pytest.approx(5)


def test_heater_range_and_tset():
    """Heater range and set temperature are parsed."""
    inst = make(
        {
            "READ:DEV:T8:TEMP:LOOP:RANGE": "10mA",
            "READ:DEV:T8:TEMP:LOOP:TSET": "0.05K",
        }
    )
    assert inst.heater_range == pytest.approx(10e-3)
    assert inst.mixing_chamber_tset == pytest.approx(0.05)
    inst = make({"READ:DEV:T8:TEMP:LOOP:RANGE": "316uA"})
    assert inst.heater_range == pytest.approx(316e-6)


def test_not_found():
    """NOT_FOUND answers raise."""
    inst = make(
        {
            "READ:DEV:T8:TEMP:LOOP:RANGE": "NOT_FOUND",
            "READ:DEV:T8:TEMP:LOOP:TSET": "NOT_FOUND",
        }
    )
    with pytest.raises(RuntimeError):
        inst.heater_range  # pylint: disable=pointless-statement
    with pytest.raises(RuntimeError):
        inst.mixing_chamber_tset  # pylint: disable=pointless-statement


def test_setters_disabled():
    """Setters raise unless enabled, and nothing is sent."""
    inst = make({})
    with pytest.raises(RuntimeError):
        inst.mixing_chamber_tset = 0.05
    with pytest.raises(RuntimeError):
        inst.heater_range = 1
    assert inst.transport.written == []


def test_setters_enabled(monkeypatch):
    """Set temperature in K and heater range in A, sent as K and mA."""
    monkeypatch.setattr(triton_module, "ENABLE_SETTERS", True)
    inst = make({})
    inst.mixing_chamber_tset = 0.05
    inst.heater_range = 10e-3
    inst.heater_range = 31.6e-6
    assert inst.transport.written == [
        "SET:DEV:T8:TEMP:LOOP:TSET:0.05",
        "SET:DEV:T8:TEMP:LOOP:RANGE:10",
        "SET:DEV:T8:TEMP:LOOP:RANGE:0.0316",
    ]
    with pytest.raises(ValueError):
        inst.mixing_chamber_tset = 0.3
    with pytest.raises(ValueError):
        inst.heater_range = 5e-3


def test_get_action():
    """Action maps the cryostat code, Idle becomes Circulating when cold."""
    inst = make(
        {
            "READ:SYS:DR:STATUS": "OK",
            "READ:SYS:DR:ACTN": "COND",
        }
    )
    assert inst.get_action() == "Condensing"
    inst = make(
        {
            "READ:SYS:DR:STATUS": "OK",
            "READ:SYS:DR:ACTN": "NONE",
            "READ:DEV:T8:TEMP:SIG:TEMP": "0.01K",
        }
    )
    assert inst.get_action() == "Circulating"
    inst = make(
        {
            "READ:SYS:DR:STATUS": "OK",
            "READ:SYS:DR:ACTN": "NONE",
            "READ:DEV:T8:TEMP:SIG:TEMP": "290K",
        }
    )
    assert inst.get_action() == "Idle"
    inst = make({"READ:SYS:DR:STATUS": "ERR"})
    with pytest.raises(RuntimeError):
        inst.get_action()


def test_reset_sends_nothing():
    """Reset only restores the defaults."""
    inst = make({})
    inst.reset()
    assert inst.transport.written == []


@pytest.mark.parametrize("temp", [-0.01, float("nan"), 0.3])
def test_tset_invalid(monkeypatch, temp):
    """Negative, NaN and too high set temperatures are rejected."""
    monkeypatch.setattr(triton_module, "ENABLE_SETTERS", True)
    inst = make({})
    with pytest.raises(ValueError):
        inst.mixing_chamber_tset = temp
    assert inst.transport.written == []


def test_tset_decimal_format(monkeypatch):
    """Small set temperatures are sent in plain decimal notation."""
    monkeypatch.setattr(triton_module, "ENABLE_SETTERS", True)
    inst = make({})
    inst.mixing_chamber_tset = 1e-5
    assert inst.transport.written == ["SET:DEV:T8:TEMP:LOOP:TSET:0.00001"]


def test_heater_range_unknown_unit():
    """An unexpected unit is a clear error."""
    inst = make({"READ:DEV:T8:TEMP:LOOP:RANGE": "1A"})
    with pytest.raises(RuntimeError):
        inst.heater_range  # pylint: disable=pointless-statement
