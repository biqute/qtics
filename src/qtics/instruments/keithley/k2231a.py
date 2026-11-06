"""
Controller of the Keithley2231A DC Power Supply.

.. module:: k2231a.py
"""

from qtics.instruments.base import SCPIInstrument
from qtics.instruments.types import PowerSupply
from qtics.instruments.utils import to_bool
from qtics.transport import SerialTransport, Transport


class Keithley2231A(PowerSupply, SCPIInstrument):
    """Keithley Model 2231A-30-3 Triple Channel DC Power Supply by Keithley Instruments.

    ``voltage``, ``current`` and their limits act on the channel selected with
    ``channel``. The selected channel is state of the device, shared by all the
    properties: changing it from several threads is not thread-safe.
    """

    default_transport = SerialTransport
    transport_defaults = {"baudrate": 9600, "terminator": "\n", "delay": 0.3}

    def __init__(
        self,
        transport: Transport | str,
        name: str = "Keithley2231A",
        **transport_kwargs,
    ):
        """Initialize."""
        super().__init__(transport, name, **transport_kwargs)

    def _after_connect(self):
        """Put the power supply in remote."""
        self.write("SYST:REM")

    def _before_disconnect(self):
        """Take the power supply out of remote."""
        self.write("SYST:LOC")

    def save(self, memory: int):
        """Save the current setups of the power supply into specified memory."""
        self.write(f"*SAV {self.validate_range(memory, 0, 30)}")

    def load(self, memory: int):
        """Load the setups saved in the specified memory location."""
        self.write(f"*RCL {self.validate_range(memory, 0, 30)}")

    @property
    def output(self) -> bool:
        """Whether the output is on (standard SCPI OUTP:STAT, to verify on hardware)."""
        return to_bool(self.query("OUTP:STAT?"))

    @output.setter
    def output(self, value: bool):
        self.write(f"OUTP:STAT {'ON' if value else 'OFF'}")

    @property
    def channel(self) -> int:
        """Select the channel to use (device state shared by voltage and current)."""
        return int(self.query("INST:NSEL?").split()[-1])

    @channel.setter
    def channel(self, ch: int):
        self.validate_opt(ch, (1, 2, 3))
        self.write(f"INST:NSEL {ch}")

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
        self.write(f"SOUR:CURR:LIMIT:LEV {self.validate_range(value, 0, 3)}")
