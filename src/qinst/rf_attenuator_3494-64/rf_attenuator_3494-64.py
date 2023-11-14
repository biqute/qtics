import serial
from qinst.serial_inst import SerialInst


class switch_R591(SerialInst):
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
    def pulse_lenght(self, value: float):
        self._attenuation = value
        self.write(f"ATT {value}")

