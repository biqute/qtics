"""
Controller of the Keithley6514 electrometer.

.. module:: keithley6514.py
.. moduleauthor:: Marco Gobbo <marco.gobbo@mib.infn.it>
"""

from qinst.serial_inst import SerialInst


class Keithley6514(SerialInst):
    """Keithley 6514 Programmable Electrometer by Keithley Instruments."""

    def connect(self):
        """Put Keithley 6514 Electrometer in remote."""
        self.serial.open()
        self.write("SYST:REM")

    def disconnect(self):
        """Take Keithley 6514 Electrometer out of remote."""
        if self.serial.is_open:
            self.write("SYST:LOC")
            self.serial.close()

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
        """Set basic settings for measure a parameter.

        Valid parameters to write:
        - VOLT: Voltage measurement
        - CURR: Current measurement
        - RES: Resistance measurement
        - CHAR: Charge measurement
        """
        parameters = ("VOLT", "CURR", "RES", "CHAR")

        if parameter in parameters:
            self.write(f"SENS:FUNC '{parameter}'", True)
            self.write(f"SENS:{parameter}:RANG:AUTO ON", True)
            self.set_zero()
        else:
            raise ValueError(
                f"Invalid parameter {parameter} for the set_measure() method."
            )

    def read_data(self) -> float:
        """Return the value of the parameter under measurement."""
        self.write("FORM:ELEM READ", True)
        self.write("ARM:COUNT 1", True)
        self.write("READ?", True)
        return float(self.read())
