"""Python driver for an arduino-controlled RF switch."""

from typing import Literal

import serial

from qtics.instruments import SerialInst


class Switch_R591(SerialInst):
    """Control for the latching RF switch R591722600."""

    def __init__(
        self,
        name: str,
        address: str,
        baudrate: int = 9600,
        bytesize: int = serial.EIGHTBITS,
        parity: Literal["N"] = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        timeout: int = 10,
        sleep: float = 0.1,
        pulse_lenght: int = 5,  # milliseconds
    ):
        """Initialize super and set pulse length."""
        super().__init__(
            name, address, baudrate, bytesize, parity, stopbits, timeout, sleep
        )

        if self.serial.is_open:
            self.pulse_lenght = pulse_lenght

    @property
    def pulse_lenght(self):
        """The pulse_lenght in ms."""
        return self.query("PUL:LEN?")

    @pulse_lenght.setter
    def pulse_lenght(self, value: int):
        self._pulse_lenght = value
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
