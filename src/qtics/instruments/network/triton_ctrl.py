"""
Controller of the Triton cryostat.

module: triton_ctrl.py
moduleauthor: Rodolfo Carobene <rodolfo.carobene@mib.infn.it>
"""

import time

from qtics.instruments import NetworkInst

ENABLE_SETTERS = False


class Triton(NetworkInst):
    """Controller of Triton dilution refrigerator by Oxford Instruments."""

    def __init__(
        self,
        name: str,
        address: str = "212.189.204.22",
        port: int = 33576,
        timeout: int = 10,
        sleep: float = 0.1,
        no_delay: bool = True,
    ):
        """Initialize."""
        super().__init__(name, address, port, timeout, sleep, no_delay)
        self._mixing_chamber_ch = 8

    def query(self, cmd: str) -> str:
        """Send a message, then read from the serial port."""
        self.write(cmd)
        time.sleep(self.sleep)
        return self.read()[len(cmd) + 1 :]

    @property
    def mixing_chamber_ch(self) -> int:
        """Return mixing chamber channel.

        If it is not already cached as an attribute, ask to the instrument.
        """
        if self._mixing_chamber_ch is not None:
            return self._mixing_chamber_ch
        self._mixing_chamber_ch = int(
            self.query("READ:SYS:DR:CHAN:MC")[1:]
        )  # return is like "T5"
        return self._mixing_chamber_ch

    @mixing_chamber_ch.setter
    def mixing_chamber_ch(self, channel: int):
        self._mixing_chamber_ch = channel

    @property
    def heater_range(self) -> float:
        """Return heater range."""
        answer = self.query(f"READ:DEV:T{self.mixing_chamber_ch}:TEMP:LOOP:RANGE")
        if answer == "NOT_FOUND":
            raise RuntimeError("Range not set.")
        conversions = {"uA": 1e-3, "mA": 1}
        return float(answer[:-2]) * conversions[answer[-2:]]

    @heater_range.setter
    def heater_range(self, hrange: float):
        if not ENABLE_SETTERS:
            raise RuntimeError("Setter not enabled!")
        ranges = (31.6 / 1e3, 100 / 1e3, 316 / 1e3, 1, 3.16, 10, 31.6, 100)
        if hrange not in ranges:
            raise ValueError(f"Range {hrange} not allowed. Choose between {ranges}.")

        self.write(f"SET:DEV:T{self.mixing_chamber_ch}:TEMP:LOOP:RANGE:{hrange/1000}")

    def get_mixing_chamber_temp(self):
        """Return mixing chamber temperature in mK."""
        answer = self.query(f"READ:DEV:T{self.mixing_chamber_ch}:TEMP:SIG:TEMP")
        return float(answer[:-1]) * 1000

    @property
    def mixing_chamber_tset(self) -> float:
        """Return mixing chamber set temperature in mK."""
        answer = self.query(f"READ:DEV:T{self.mixing_chamber_ch}:TEMP:LOOP:TSET")
        if answer == "NOT_FOUND":
            raise RuntimeError("Temperature mixing not set.")
        return float(answer[:-1]) * 1000

    @mixing_chamber_tset.setter
    def mixing_chamber_tset(self, temp: float):
        if not ENABLE_SETTERS:
            raise RuntimeError("Setter not enabled!")
        if temp > 200:
            raise ValueError(f"Temperature set too high! Was {temp}.")
        self.write(f"SET:DEV:T{self.mixing_chamber_ch}:TEMP:LOOP:TSET:{temp/1000}")
