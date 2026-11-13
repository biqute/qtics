"""Controller of the SIM928 isolated voltage source (SRS), used through a SIM900 mainframe."""

import time

from qtics import log
from qtics.instruments.base import SCPIInstrument
from qtics.instruments.types import DCSource
from qtics.instruments.utils import to_bool
from qtics.transport import SerialTransport, Transport


class SIM928(DCSource, SCPIInstrument):
    """
    SIM928 isolated voltage source by Stanford Research Systems.

    Works in conjunction with the SIM900 mainframe.
    """

    default_transport = SerialTransport
    transport_defaults = {"baudrate": 9600, "terminator": "\n", "delay": 0.1}

    def __init__(
        self,
        transport: Transport | str,
        name: str = "SIM928",
        mainframe_port: int = 1,
        **transport_kwargs,
    ):
        """Initialize, ``mainframe_port`` is the slot of the SIM900 mainframe."""
        super().__init__(transport, name, **transport_kwargs)
        self._mainframe_port = mainframe_port

    def query(self, cmd: str) -> str:
        """Return query without terminal character."""
        return super().query(cmd)[:-1]

    def _after_connect(self):
        """Open the passthrough to the SIM928 in the mainframe port."""
        time.sleep(self.transport.delay)
        self.connect_port(self._mainframe_port)
        log.info(f"Instrument connected to port {self._mainframe_port}")

    def connect_port(self, port: int):
        """Connect to a specific port in the mainframe.

        The port buffers are flushed first: answers left there by a previous program
        would otherwise be read as answers to the next queries.
        """
        self._mainframe_port = port
        self.write(f"FLSH {port}")
        self.write(f'CONN {port}, "esc"')

    def _before_disconnect(self):
        """
        Leave the passthrough and reset the instrument.

        Reset the mainframe before disconnecting to avoid problems when connecting again.
        """
        self.write("esc")
        self.reset()
        time.sleep(self.transport.delay)

    @property
    def output(self) -> bool:
        """Whether the output is on."""
        return to_bool(self.query("EXON?"))

    @output.setter
    def output(self, value: bool):
        self.write("OPON" if value else "OPOF")

    @property
    def voltage(self) -> float:
        """Output voltage."""
        return float(self.query("VOLT?"))

    @voltage.setter
    def voltage(self, value: float):
        """Set the output voltage, sent with the 1 mV resolution of the SIM928."""
        self.write(f"VOLT {round(value, 3) + 0.0:.3f}")  # + 0.0 turns -0.0 into 0.0

    # Battery commands
    def battery_charger_override(self):
        """Force the SIM928 to switch the active output battery."""
        self.write("BCOR")

    def battery_state(self) -> str:
        """
        Query the battery status of the SIM928.

        Return:
          str: A string in the format "<a>,<b>,<x>", where <a> and <b>
          correspond to batteries “A” and “B”, and are equal to
          1 for in use, 2 for charging, and 3 for ready/standby.
          The third parameter, <x>, is normally 0; it is set to 1 if
          the service batteries indicator is lit.
        """
        return self.query("BATS?")

    def battery_spec(self, parameter: str) -> str:
        """Query the battery specification for parameter i.

        Valid parameters to query:
        - PNUM (0): Battery pack part number
        - SERIAL (1): Battery pack serial number
        - MAXCY (2): Design life (# of charge cycles)
        - CYCLES (3): # charge cycles used
        - PDATE (4): Battery pack production date (YYYY-MM-DD)
        """
        parameters = ("PNUM", "SERIAL", "MAXCY", "CYCLES", "PDATE")

        self.validate_opt(parameter, parameters)
        return self.query("BIDN? " + parameter)

    def battery_full_spec(self):
        """Print the full battery specifications."""
        options = (
            "Battery pack part number",
            "Battery pack serial number",
            "Design life (number of charge cycles)",
            "Charge cycles used",
            "Battery pack production date (YYYY-MM-DD)",
        )

        parameters = ("PNUM", "SERIAL", "MAXCY", "CYCLES", "PDATE")

        for i in range(5):
            print(options[i] + ": ")
            print(self.battery_spec(parameters[i]))

    # Error commands
    def exe_error(self) -> str:
        """Get last execution error."""
        a = self.query("LEXE?")
        options = (
            "No execution error since last LEXE?",
            "Illegal value",
            "Wrong token",
            "Invalid bit",
        )
        return _error_name(options, a, "execution error")

    def dev_error(self) -> str:
        """Get last command/device error."""
        a = self.query("LCME?")
        options = (
            "No command error since last LCME?",
            "Illegal command",
            "Undefined command",
            "Illegal query",
            "Illegal set",
            "Missing parameter-s",
            "Extra parameter-s",
            "Null parameter-s",
            "Parameter buffer overflow",
            "Bad floating-point",
            "Bad integer",
            "Bad integer token",
            "Bad token value",
            "Bad hex block",
            "Unknown token",
        )
        return _error_name(options, a, "command error")


def _error_name(names: tuple, answer: str, kind: str) -> str:
    """Name of an error code, also for codes missing from ``names``."""
    code = int(answer)
    return names[code] if 0 <= code < len(names) else f"Unknown {kind} (code {code})"
