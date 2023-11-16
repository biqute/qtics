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
        timeout: int = 5,
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
        self.is_connected = True

    def disconnect(self):
        if self.serial.is_open:
            self.serial.close()
            self.is_connected = False

    def write(self, cmd):
        if self.serial.is_open:
            self.serial.write((cmd + "\n").encode())

    def read(self):
        if self.serial.is_open:
            return self.serial.read(self.serial.in_waiting)
        return None

    def query(self, cmd):
        if self.serial.is_open:
            self.write(cmd)
            time.sleep(self.sleep)
            return self.read()
        return None
