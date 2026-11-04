"""Python driver for an arduino-controlled RF switch."""

from qtics.instruments.base import SCPIInstrument
from qtics.transport import SerialTransport, Transport


class R591Switch(SCPIInstrument):
    """Control for the latching RF switch R591722600."""

    default_transport = SerialTransport
    transport_defaults = {"baudrate": 9600, "terminator": "\n", "delay": 0.1}

    def __init__(
        self,
        transport: Transport | str,
        name: str = "",
        pulse_length: int = 5,  # milliseconds
        **transport_kwargs,
    ):
        """Initialize, ``pulse_length`` is sent to the switch when connecting."""
        super().__init__(transport, name, **transport_kwargs)
        self._pulse_length = pulse_length

    def _after_connect(self):
        """Set the pulse length."""
        self.pulse_length = self._pulse_length

    @property
    def pulse_length(self) -> int:
        """The pulse length in ms."""
        return int(self.query("PUL:LEN?"))

    @pulse_length.setter
    def pulse_length(self, value: int):
        self._pulse_length = value
        self.write(f"PUL:LEN {value}")

    def open(self, pin: int) -> None:
        """Open port at specified pin."""
        self.write(f"SWI:ON {pin}")

    def get_open_ports(self):
        """Get currently open RF ports."""
        return self.query("SWI:ON?")

    def get_pins_state(self):
        """Get status of digital arduino pins."""
        return self.query("DIG:PIN?")
