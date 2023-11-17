"""
Controller of the Keithley6514 electrometer.

.. module:: keithley6514.py
.. moduleauthor:: Marco Gobbo <marco.gobbo@mib.infn.it>
"""
import serial

from qinst.serial_inst import SerialInst


class Keithley6514(SerialInst):
    """Keithley 6514 Programmable Electrometer by Keithley Instruments."""

    def __init__(
        self,
        name: str,
        address: str,
        baudrate: int = 9600,
        bytesize: int = serial.EIGHTBITS,
        parity: int = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        timeout: int = 10,
        sleep: float = 0.2,
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

    # Basic commands
    def reset(self):
        """Return Model 6514 to the RST default conditions."""
        self.write("*RST", True)

    def zcheck_on(self):
        """Enable zero check."""
        self.write("SYST:ZCH ON", True)

    def zcheck_off(self):
        """Disable zero check."""
        self.write("SYST:ZCH OFF", True)

    def zcorrect(self):
        """Perform zero correction."""
        self.write("SYST:ZCOR ON", True)

    def set_zero(self):
        """Perform zero correction sequence."""
        self.zcheck_on()
        self.zcorrect()
        self.zcheck_off()

    def set_measure(self, parameter: str):
        """
        Basic settings for measure a parameter.

        Valid parameters to write:
        - VOLT: Voltage measurement
        - CURR: Current measurement
        - RES: Resistance measurement
        - CHAR: Charge measurement
        """
        parameters = ("VOLT", "CURR", "RES", "CHAR")

        if parameter in parameters:
            self.write("SENS:FUNC '" + parameter + "'", True)
            self.write("SENS:" + parameter + ":RANG:AUTO ON", True)
            self.set_zero()
        else:
            raise ValueError("Invalid parameter for the set_measure() method.")

    def read_data(self) -> str:
        """Read the parameter data."""
        self.write("FORM:ELEM READ", True)
        self.write("ARM:COUNT 1", True)
        self.write("READ?", True)
        return self.read()
