import pyvisa

from qinst.instrument import Instrument


class GPIBInst(Instrument):
    def __init__(self, name: str, address: str, timeout: int = 1000, sleep: int = 0):
        super().__init__(name, address)

        self.rm = pyvisa.ResourceManager()
        self.timeout = timeout
        self.sleep = sleep

    def connect(self):
        self.gpib = self.rm.open_resource(self.name)
        self.gpib.timeout = self.timeout

    def disconnect(self):
        if self.gpib:
            self.gpib.close()
