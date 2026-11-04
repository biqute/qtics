"""Tests of the R591Switch driver."""

from qtics.instruments.arduino.r591_switch import R591Switch
from qtics.transport import FakeTransport, SerialTransport


def test_defaults():
    """Serial defaults."""
    inst = R591Switch("/dev/null")
    assert isinstance(inst.transport, SerialTransport)
    assert inst.transport.delay == 0.1


def test_pulse_length_on_connect():
    """Pulse length passed at init is sent when connecting."""
    switch = R591Switch(FakeTransport(), pulse_length=7)
    switch.connect()
    assert switch.transport.written == ["PUL:LEN 7"]


def test_pulse_length_property():
    """Getter returns int, setter sends the command."""
    switch = R591Switch(FakeTransport(answers={"PUL:LEN?": "12"}))
    switch.transport.connect()
    assert switch.pulse_length == 12
    switch.pulse_length = 20
    assert switch.transport.written[-1] == "PUL:LEN 20"


def test_open_and_queries():
    """Open pin and state queries."""
    switch = R591Switch(FakeTransport(default="1"))
    switch.transport.connect()
    switch.open(5)
    assert switch.get_open_ports() == "1"
    assert switch.get_pins_state() == "1"
    assert switch.transport.written == ["SWI:ON 5", "SWI:ON?", "DIG:PIN?"]


def test_reset():
    """Reset sends *RST."""
    switch = R591Switch(FakeTransport())
    switch.transport.connect()
    switch.reset()
    assert switch.transport.written == ["*RST"]
