import serial
from instrument import Instrument


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

        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.sleep = sleep

    def __del__(self):
        self.disconnected()

    def connect(self):
        self.serial = serial.Serial()
        self.serial.port = self.address
        self.serial.badurate = self.baudrate
        self.serial.parity = self.parity
        self.serial.stopbits = self.stopbits
        self.serial.timeout = self.timeout

        self.serial.open()

        return

    def disconnect(self):
        if self.serial.isOpen():
            self.serial.close()

        del self.serial

        return

    def write(self, cmd):
        if self.serial is not None:
            self.serial.write((cmd + "\n").encode())

        return

    def read(self):
        return (
            self.serial.read(self.serial.inWaiting())
            if self.__ser is not None
            else None
        )

    def query(self, cmd):
        if self.serial is not None:
            self.write(cmd)
            time.sleep(self.sleep)
            return self.read()
        else:
            return None
