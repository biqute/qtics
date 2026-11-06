"""
Controller of the Keithley6514 Electrometer.

.. module:: k6514.py
"""

from qtics.instruments.base import SCPIInstrument
from qtics.transport import SerialTransport, Transport


class Keithley6514(SCPIInstrument):
    """Keithley 6514 Programmable Electrometer by Keithley Instruments."""

    default_transport = SerialTransport
    transport_defaults = {"baudrate": 9600, "terminator": "\n", "delay": 0.3}

    def __init__(
        self,
        transport: Transport | str,
        name: str = "Keithley6514",
        **transport_kwargs,
    ):
        """Initialize."""
        super().__init__(transport, name, **transport_kwargs)

    def _after_connect(self):
        """Put the electrometer in remote."""
        self.write("SYST:REM")

    def _before_disconnect(self):
        """Take the electrometer out of remote."""
        self.write("SYST:LOC")

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
