import serial

from qinst.serial_inst import SerialInst


class attenuator_3494_64(SerialInst):
    """Control for the latching RF attenuator."""

    def __init__(
        self,
        name: str,
        address: str,
        baudrate: int = 9600,
        bytesize: int = serial.EIGHTBITS,
        parity: int = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        timeout: int = 5,
        sleep: int = 1,
    ):
        super().__init__(
            name, address, baudrate, bytesize, parity, stopbits, timeout, sleep
        )

    @property
    def attenuation(self):
        """The pulse_lenght in ms."""
        return self.query("ATT?")

    @attenuation.setter
    def attenuation(self, value: float):
        self._attenuation = value
        self.write(f"ATT {value}")

    def get_pins_state(self):
        """Get status of digital arduino pins."""
        return self.query("DIG:PIN?")
