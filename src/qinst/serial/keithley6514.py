import serial

from qinst.serial_inst import SerialInst


class Keithley6514(SerialInst):
    """Control for the Keithley 6514 Electrometer."""

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
        super().__init__(
            name, address, baudrate, bytesize, parity, stopbits, timeout, sleep
        )

    def connect(self):
        """Put Keithley 6514 Electrometer in remote."""
        self.serial.open()
        self.write("SYST:REM")

    def disconnect(self):
        """Take Keithley 6514 Electrometer out of remote."""
        if self.serial.is_open:
            self.write("SYST:LOC")
            self.serial.close()

    def reset(self):
        """Returns Model 6514 to the *RST default conditions."""
        self.write("*RST", True)

    def zcheck_on(self):
        self.write("SYST:ZCH ON", True)

    def zcheck_off(self):
        self.write("SYST:ZCH OFF", True)

    def zcorrect(self):
        self.write("SYST:ZCOR ON", True)

    def read_data(self):
        self.write("FORM:ELEM READ", True)
        self.write("ARM:COUNT 1", True)
        self.write("READ?", True)
        return self.read()

    def set_voltage_measure(self):
        self.write("SENS:FUNC 'VOLT'", True)
        return self.query("SENS:VOLT:RANG:AUTO ON")

    def set_current_measure(self):
        self.write("SENS:FUNC 'CURR'", True)
        return self.query("SENS:CURR:RANG:AUTO ON")

    def set_resistance_measure(self):
        self.write("SENS:FUNC 'RES'", True)
        return self.query("SENS:RES:RANG:AUTO ON")

    def set_charge_measure(self):
        self.write("SENS:FUNC 'CHAR'", True)
        return self.query("SENS:CHAR:RANG:AUTO ON")
