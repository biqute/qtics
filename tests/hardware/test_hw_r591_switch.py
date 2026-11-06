"""Hardware tests of the Arduino-driven R591 RF switch.

Config: ``[R591Switch]`` with ``address`` (serial port, e.g. ``/dev/ttyACM0``).

Switching changes the physical RF path, so it is marked ``output``. The switch is
only commanded to the port found open at the start, then left as found.
"""

import pytest

from qtics import R591Switch


@pytest.fixture(scope="module")
def switch(open_instrument):
    """Connected switch."""
    return open_instrument(R591Switch)


def test_identity(switch):
    """The Arduino answers *IDN?."""
    assert switch.get_id()


def test_readonly(switch):
    """State queries answer with non-empty strings."""
    assert switch.get_open_ports().strip()
    assert switch.get_pins_state().strip()


def test_pulse_length(switch, roundtrip):
    """The pulse length is read back (short pulses, no RF path change)."""
    roundtrip(switch, "pulse_length", [5, 10])


@pytest.mark.output
def test_reopen_current_port(switch, confirm):
    """Re-open the port already open: the state must not change."""
    before = switch.get_open_ports().strip()
    if not before.isdigit():
        pytest.skip(f"Cannot parse a single open port from {before!r}")
    confirm(f"Port {before} is open. Re-send the command to it, OK?")
    switch.open(int(before))
    assert switch.get_open_ports().strip() == before
