import time

import serial

from qinst.instrument import Instrument


class SerialInst(Instrument):
    def __init__(
        self,
        name: str,
        address: str,
        baudrate: int = 9600,
        bytesize: int = serial.EIGHTBITS,
        parity: int = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        timeout: int = 10,
        sleep: float = 0.1,
    ):
        super().__init__(name, address)

        self.serial = serial.Serial()
        self.serial.port = address
        self.serial.baudrate = baudrate
        self.serial.bytesize = bytesize
        self.serial.parity = parity
        self.serial.stopbits = stopbits
        self.serial.timeout = timeout

        self.sleep = sleep

    def __del__(self):
        self.disconnect()

    def connect(self):
        """Connect to the device."""
        self.serial.open()

    def disconnect(self):
        """Disconnect from the device."""
        if self.serial.is_open:
            self.serial.close()

    def write(self, cmd, sleep=False):
        """Write a message to the serial port."""
        if self.serial is not None:
            self.serial.write((cmd + "\n").encode())
            if sleep:
                time.sleep(self.sleep)

    def read(self) -> str:
        """Read a message from the serial port."""
        return (
            self.serial.read(self.serial.in_waiting).decode("utf-8")
            if self.serial is not None
            else ""
        )

    def query(self, cmd) -> str:
        """Send a message, then read from the serial port."""
        if self.serial is not None:
            self.write(cmd, sleep=True)
            return self.read()
        return ""

    def get_id(self) -> str:
        """Return name of the device from SCPI standard query."""
        return self.query("*IDN?")
