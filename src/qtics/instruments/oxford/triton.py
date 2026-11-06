"""
Controller of the Triton cryostat.

module: triton.py
moduleauthor: Rodolfo Carobene <rodolfo.carobene@mib.infn.it>
"""

import math
import time
from typing import Union

from qtics.instruments.base import MessageInstrument
from qtics.transport import Transport

ENABLE_SETTERS = False
HEATER_RANGES = (31.6e-6, 100e-6, 316e-6, 1e-3, 3.16e-3, 10e-3, 31.6e-3, 100e-3)
"""Allowed mixing chamber heater ranges [A]."""
MAX_TSET = 0.2
"""Maximum mixing chamber set temperature [K], as a safety limit."""


class Triton(MessageInstrument):
    """Controller of Triton dilution refrigerator by Oxford Instruments.

    Temperatures are in K and currents in A. Setters are disabled unless the module
    flag ``ENABLE_SETTERS`` is set to True.
    """

    transport_defaults = {"port": 33576, "timeout": 10, "delay": 0.1}

    def __init__(
        self, transport: Union[Transport, str], name: str = "Triton", **transport_kwargs
    ):
        """Initialize, ``transport`` is a transport or the address of the cryostat."""
        super().__init__(transport, name, **transport_kwargs)

    def query(self, cmd: str) -> str:
        """Send a message, then read the answer stripping the echoed command."""
        with self.transport.lock:
            self.write(cmd)
            time.sleep(self.transport.delay)
            return self.read()[len(cmd) + 1 :]

    @property
    def heater_range(self) -> float:
        """Mixing chamber heater range [A], one of ``HEATER_RANGES``."""
        answer = self.query(f"READ:DEV:T8:TEMP:LOOP:RANGE")
        if answer == "NOT_FOUND":
            raise RuntimeError("Range not set.")
        conversions = {"uA": 1e-6, "mA": 1e-3}
        unit = answer[-2:]
        if unit not in conversions:
            raise RuntimeError(f"Unexpected heater range answer {answer}.")
        return float(answer[:-2]) * conversions[unit]

    @heater_range.setter
    def heater_range(self, hrange: float):
        if not ENABLE_SETTERS:
            raise RuntimeError("Setter not enabled!")
        if not any(math.isclose(hrange, r) for r in HEATER_RANGES):
            raise ValueError(
                f"Range {hrange} A not allowed. Choose between {HEATER_RANGES}."
            )
        # The cryostat takes the range in mA, as it reports it
        self.write(f"SET:DEV:T8:TEMP:LOOP:RANGE:{hrange * 1e3:g}")

    def get_mixing_chamber_temp(self):
        """Return mixing chamber temperature in K."""
        answer = self.query(f"READ:DEV:T8:TEMP:SIG:TEMP")
        return float(answer[:-1])

    def get_still_temp(self):
        """Return still temperature in K."""
        answer = self.query(f"READ:DEV:T3:TEMP:SIG:TEMP")
        return float(answer[:-1])

    def get_cool_temp(self):
        """Return cold plate temperature in K."""
        answer = self.query(f"READ:DEV:T5:TEMP:SIG:TEMP")
        return float(answer[:-1])

    def get_pt1_temp(self):
        """Return pt1 temperature in K."""
        answer = self.query(f"READ:DEV:T7:TEMP:SIG:TEMP")
        return float(answer[:-1])

    def get_pt2_temp(self):
        """Return pt2 temperature in K."""
        answer = self.query(f"READ:DEV:T2:TEMP:SIG:TEMP")
        return float(answer[:-1])

    def get_sorb_temp(self):
        """Return sorb temperature in K."""
        answer = self.query(f"READ:DEV:T11:TEMP:SIG:TEMP")
        return float(answer[:-1])

    @property
    def mixing_chamber_tset(self) -> float:
        """Return mixing chamber set temperature in K."""
        answer = self.query(f"READ:DEV:T8:TEMP:LOOP:TSET")
        if answer == "NOT_FOUND":
            raise RuntimeError("Temperature mixing not set.")
        return float(answer[:-1])

    @mixing_chamber_tset.setter
    def mixing_chamber_tset(self, temp: float):
        if not ENABLE_SETTERS:
            raise RuntimeError("Setter not enabled!")
        if not 0 <= temp <= MAX_TSET:
            raise ValueError(f"Set temperature {temp} K not in [0, {MAX_TSET}] K.")
        value = f"{temp:.6f}".rstrip("0").rstrip(".") or "0"
        self.write(f"SET:DEV:T8:TEMP:LOOP:TSET:{value}")

    def get_state(self) -> str:
        """Return state of the cryostat."""
        return self.query("READ:SYS:DR:STATUS")

    def get_action(self) -> str:
        """Return current action of the cryostat."""
        state = self.get_state()
        if state == "OK":
            mapped = {
                "PCL": "Precooling",
                "EPCL": "Empty precool loop",
                "COND": "Condensing",
                "NONE": "Idle",
                "COLL": "Collecting mixture",
            }
            msg = self.query("READ:SYS:DR:ACTN")
            if msg in mapped:
                res = mapped[msg]
            else:
                res = "Unknown"
            # No action running with a cold mixing chamber means circulating
            if res == "Idle" and self.get_mixing_chamber_temp() < 2.0:
                res = "Circulating"
            return res
        raise RuntimeError(f"Current state is {state}")
