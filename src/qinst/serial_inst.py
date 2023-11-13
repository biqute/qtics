import serial
from instrument import Instrument


class SerialInst(Instrument):
    def __init__(self, name, address, baudrate):
        super.__init__(name, address)
        self.baudrate: int = baudrate

    def __del__(self):
        self.disconnected()

    def connect():
        self.serial = serial.Serial()
        self.serial.port = self.address
        self.serial.badurate = self.baudrate
