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
        timeout: int = 0,
        sleep: int = 0,
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
        self.serial.open()

    def disconnect(self):
        if self.serial.is_open:
            self.serial.close()

    def write(self, cmd):
        if self.serial is not None:
            self.serial.write((cmd + "\n").encode())

    def read(self):
        return (
            self.serial.read(self.serial.in_waiting)
            if self.serial is not None
            else None
        )

    def query(self, cmd):
        if self.serial is not None:
            self.write(cmd)
            time.sleep(self.sleep)
            return self.read()
        return None

    def get_id(self):
        """Return name of the device from SCPI standard query."""
        return self.query("*IDN?")
