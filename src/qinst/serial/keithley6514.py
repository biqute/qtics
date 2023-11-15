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
        sleep: int = 1,
    ):
        super().__init__(
            name, address, baudrate, bytesize, parity, stopbits, timeout, sleep
        )

    """Put Keithley 6514 Electrometer in remote."""

    def connect(self):
        super().connect()
        self.write("SYST:REM")

    """Take Keithley 6514 Electrometer out of remote."""

    def disconnect(self):
        if self.serial.is_open:
            self.write("SYST:LOC")
        super().disconnect()

    """Returns Model 6514 to the *RST default conditions."""

    def reset(self):
        self.write("*RST")

    def zcheck_on(self):
        self.write("SYST:ZCHE ON")

    def zcheck_off(self):
        self.write("SYST:ZCHE OFF")

    def zcheck_status(self):
        return self.query("SYST:ZCHE?")

    def zcorrect(self):
        self.write("SYST:ZCOR ON")

    def time_reset(self):
        self.write("SYST:TIME:RES")

    def read_data(self):
        return self.query("READ?")

    def set_voltage_measure(self):
        return self.query("SENS:FUNC VOLT")

    def set_current_measure(self):
        return self.query("SENS:FUNC CURR")

    def set_resistance_measure(self):
        return self.query("SENS:FUNC RES")

    def set_charge_measure(self):
        return self.query("SENS:FUNC CHAR")
