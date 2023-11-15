import time

import pyvisa

from qinst.instrument import Instrument


class GPIBInst(Instrument):
    def __init__(
        self, name: str, address: str, timeout: int = 1000, sleep: float = 0.1
    ):
        super().__init__(name, address)

        self.rm = pyvisa.ResourceManager()
        self.timeout = timeout
        self.sleep = sleep

    def __del__(self):
        self.disconnect()

    def connect(self):
        self.gpib = self.rm.open_resource(self.name)
        self.gpib.timeout = self.timeout

    def disconnect(self):
        if self.gpib:
            self.gpib.close()

    def write(self, cmd):
        if self.gpib is not None:
            self.gpib.write((cmd + "\n").encode())

    def read(self):
        return self.pyvisa.read() if self.gpib is not None else None

    def query(self, cmd):
        if self.gpib is not None:
            self.write(cmd)
            time.sleep(self.sleep)
            return self.read()
        return None

    def get_id(self):
        """Return name of the device from SCPI standard query."""
        return self.query("*IDN?")
