"""
Controller of the Keithley2231A DC Power Supply.

.. module:: keithley2231a.py
.. moduleauthor:: Marco Gobbo <marco.gobbo@mib.infn.it>
"""

from qtics import log
from qtics.instruments import SerialInst


class Keithley2231A(SerialInst):
    """Keithley Model 2231A-30-3 Triple Channel DC Power Supply by Keithley Instruments."""

    def connect(self):
        """Put Keithley 2231A DC Power Supply in remote."""
        self.serial.open()
        self.write("SYST:REM")
        log.info(f"Instrument {self.name} connected successfully.")

    def disconnect(self):
        """Take Keithley 2231A DC Power Supply out of remote."""
        if self.serial.is_open:
            self.write("SYST:LOC")
            self.serial.close()
            log.info(f"Instrument {self.name} disconnected.")

    @property
    def is_completed(self) -> bool:
        """Return the OPC bit in the standard event register to 1 when all commands are complete."""
        return self.query("*OPC?") == "1"

    def clear(self):
        """Clear the event registers and error queues."""
        self.write("*CLS")

    def save(self, memory: int):
        """Save the current setups of the power supply into specified memory."""
        self.write(f"*SAV {self.validate_range(memory, 0, 30)}")

    def load(self, memory: int):
        """Load the setups saved in the specified memory location."""
        self.write(f"*RCL {self.validate_range(memory, 0, 30)}")

    def wait(self):
        """Prevent the instrument from executing commands until all commands are completed."""
        self.write("*WAI")

    @property
    def channel(self) -> int:
        """Select the channel to use."""
        return int(self.query("INST:NSEL?").split()[-1])

    @channel.setter
    def channel(self, ch: int):
        self.write(f"INST:NSEL {self.validate_opt(ch, (1,2,3))}")

    @property
    def voltage(self) -> float:
        """Voltage of the selected the channel."""
        return float(self.query("SOUR:VOLT:LEV:IMM:AMPL?"))

    @voltage.setter
    def voltage(self, value: float):
        v_max = 5 if self.channel == 3 else 30
        self.write(f"SOUR:VOLT:LEV:IMM:AMPL {self.validate_range(value, 0, v_max)}")

    @property
    def current(self) -> float:
        """Current of the selected the channel."""
        return float(self.query("SOUR:CURR:LEV:IMM:AMPL?"))

    @current.setter
    def current(self, value: float):
        self.write(f"SOUR:CURR:LEV:IMM:AMPL {self.validate_range(value, 0, 3)}")

    @property
    def voltage_limit(self) -> float:
        """Voltage limit of the selected the channel."""
        return float(self.query("SOUR:VOLT:LIMIT:LEV?"))

    @voltage_limit.setter
    def voltage_limit(self, value: float):
        v_max = 5 if self.channel == 3 else 30
        self.write(f"SOUR:VOLT:LIMIT:LEV {self.validate_range(value, 0, v_max)}")

    @property
    def current_limit(self) -> float:
        """Current limit of the selected the channel."""
        return float(self.query("SOUR:CURR:LIMIT:LEV?"))

    @current_limit.setter
    def current_limit(self, value: float):
        self.write(f"SOUR:VOLT:LIMIT:LEV {self.validate_range(value, 0, 3)}")
