"""
Controller of the Triton cryostat.

module: triton_ctrl.py
moduleauthor: Rodolfo Carobene <rodolfo.carobene@mib.infn.it>
"""


from typing import Optional

from qinst.network_inst import NetworkInst


class Triton(NetworkInst):
    """CTriton controllery by Oxford Instruments."""

    def __init__(
        self,
        name: str,
        address: str,
        port: int = 33576,
        timeout: int = 10,
        sleep: float = 0.1,
        no_delay=True,
    ):
        """Initialize."""
        super().__init__(name, address, port, timeout, sleep, no_delay)
        self._mixing_chamber_ch: Optional[int] = None

    @property
    def mixing_chamber_ch(self) -> int:
        """Return mixing chamber channel.

        If it is not already cached as an attribute, ask to the instrument.
        """
        if self._mixing_chamber_ch is not None:
            return self._mixing_chamber_ch
        self._mixing_chamber_ch = int(
            self.query("READ:SYS:DR:CHAN:MC")[len("STAT:SYS:DR:CHAN:MC:") + 1 :]
        )
        return self._mixing_chamber_ch

    @property
    def heater_range(self) -> float:
        """Return heater range."""
        query = f"READ:DEV:T{self.mixing_chamber_ch}:TEMP:LOOP:RANGE"
        answer = self.query(query)[len(query)]
        conversions = {"uA": 1e-3, "mA": 1}
        return float(answer[:-2]) * conversions[answer[-2:]]

    @heater_range.setter
    def heater_range(self, hrange: float):
        ranges = (31.6 / 1e3, 100 / 1e3, 316 / 1e3, 1, 3.16, 10, 31.6, 100)
        if hrange not in ranges:
            raise ValueError(f"Range {hrange} not allaowed. Choose between {ranges}.")
        self.write(f"SET:DEV:T{self.mixing_chamber_ch}:TEMP:LOOP:RANGE:{hrange/1000}")

    def get_mixing_chamber_temp(self):
        """Return mixing chamber temperature in mK."""
        query = f"READ:DEV:T{self.mixing_chamber_ch}:TEMP:SIG:TEMP"
        answer = self.query(query)
        return float(answer[len(query) : -1]) * 1000

    @property
    def mixing_chamber_tset(self) -> float:
        """Return mixing chamber set temperature in mK."""
        query = f"READ:DEV:T{self.mixing_chamber_ch}:TEMP:LOOP:TSET"
        answer = self.query(query)
        return float(answer[len(query) : -1]) * 1000

    @mixing_chamber_tset.setter
    def mixing_chamber_tset(self, temp: float):
        """Return mixing chamber set temperature in mK."""
        if temp > 200:
            raise ValueError(f"Temperature set too high! Was {temp}.")
        self.write(f"SET:DEV:T{self.mixing_chamber_ch}:TEMP:LOOP:TSET:{temp/1000}")
