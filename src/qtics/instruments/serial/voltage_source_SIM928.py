"""Keithely device 6514."""

import time
from typing import Literal

import serial

from qtics import log
from qtics.instruments import SerialInst


class SIM928(SerialInst):
    """
    SIM928 isolated voltage source by Stanford Research Systems.

    Works in conjunction with the SIM900 mainframe.
    """

    def __init__(
        self,
        name: str,
        address: str,
        baudrate: int = 9600,
        bytesize: int = serial.EIGHTBITS,
        parity: Literal["N"] = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        timeout: int = 10,
        sleep: float = 0.1,
        mainframe_port: int = 1,
    ):
        """Initialize the class."""
        super().__init__(
            name,
            address,
            baudrate,
            bytesize,
            parity,
            stopbits,
            timeout,
            sleep,
        )
        self._mainframe_port = mainframe_port

    def connect(self):
        """Connect to the device."""
        super().connect()
        time.sleep(self.sleep)
        self.connect_port(self._mainframe_port)
        log.info(f"Instrument connected to port {self._mainframe_port}")

    def connect_port(self, port: int):
        """Connect to the a specific port in the mainframe."""
        self._mainframe_port = port
        self.write(f'CONN {port}, "esc"')

    def disconnect(self):
        """
        Disconnect from the device.

        Reset the mainframe before disconnecting to avoid problems when connecting again.
        """
        if self.serial.is_open:
            self.write("esc")
            self.reset()
            time.sleep(self.sleep)
            self.serial.close()
            log.info(f"Instrument {self.name} disconnected.")
        else:
            log.info(f"No connection to close for instrument {self.name}.")

    def output_on(self):
        """Turn the output on."""
        self.write("OPON")

    def output_off(self):
        """Turn the output off."""
        self.write("OPOF")

    @property
    def voltage(self) -> str:
        """Output voltage."""
        return self.query("VOLT?")

    @voltage.setter
    def voltage(self, value: float):
        """Set the output voltage."""
        self._voltage = value
        self.write(f"VOLT {value}")

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
        return options[int(a)]

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
        return options[int(a)]
