"""Attenuator349464."""

from typing import Literal

import serial

from qtics.instruments import SerialInst


class Attenuator_3494_64(SerialInst):
    """Control for the latching RF attenuator."""

    def __init__(
        self,
        name: str,
        address: str,
        baudrate: int = 9600,
        bytesize: int = serial.EIGHTBITS,
        parity: Literal["N"] = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        timeout: int = 5,
        sleep: float = 0.1,
    ):
        """Initialize."""
        super().__init__(
            name, address, baudrate, bytesize, parity, stopbits, timeout, sleep
        )
        self._attenuation: float = 0.0

    @property
    def attenuation(self):
        """The pulse_lenght in ms."""
        return self.query("ATT?")

    @attenuation.setter
    def attenuation(self, value: float):
        self._attenuation = round(value, 2)
        self.write(f"ATT {value}")

    def get_pins_state(self):
        """Get status of digital arduino pins."""
        return self.query("DIG:PIN?")
