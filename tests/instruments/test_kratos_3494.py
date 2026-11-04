"""Tests of the Kratos3494Attenuator driver."""

from qtics.instruments.arduino.kratos_3494 import Kratos3494Attenuator
from qtics.transport import FakeTransport, SerialTransport


def test_defaults():
    """Serial defaults."""
    inst = Kratos3494Attenuator("/dev/null")
    assert isinstance(inst.transport, SerialTransport)
    assert inst.transport.delay == 0.1
    assert inst.transport.timeout == 5


def test_attenuation():
    """Getter returns float dB, setter sends ATT."""
    # Firmware answer: value, tab, unit (GetAttenuation in the .ino)
    att = Kratos3494Attenuator(FakeTransport(answers={"ATT?": "20.50\tdB\r"}))
    att.transport.connect()
    assert att.attenuation == 20.5
    att.attenuation = 10
    assert att.transport.written[-1] == "ATT 10"


def test_pins_state():
    """Pins query."""
    att = Kratos3494Attenuator(FakeTransport(default="0"))
    att.transport.connect()
    assert att.get_pins_state() == "0"
