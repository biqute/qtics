"""
20GHz Frequency Synthesizer module Valon Model 5019.

.. module:: valon_5019.py
"""

from typing import Literal

import serial

from qtics.instruments import SerialInst


class VALON5019(SerialInst):
    """Frequency synthesizer driver for VALON5019."""

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
    ):
        """Initialize."""
        super().__init__(
            name, address, baudrate, bytesize, parity, stopbits, timeout, sleep, "\r"
        )

    def write(self, cmd, sleep=False):
        """Write a message to the serial port."""
        self.last_cmd_lenght = len(cmd + self.terminator)
        super().write(cmd, sleep)

    def read(self) -> str:
        """Read a message from the serial port."""
        res = super().read()
        if res != "":
            res = res[self.last_cmd_lenght :].split(";")[0]
        return res

    @property
    def mode(self):
        """Return current mode of operation (continuous tone, sweep, list)."""
        return self.query("MOD?")

    @mode.setter
    def mode(self, mode_to_set):
        """Set mode of operation (continuous tone, sweep, list)."""
        if mode_to_set not in ("CW", "SWE", "LIST"):
            raise ValueError(f"Mode {mode_to_set} not supported.")
        self.write(f"MOD {mode_to_set}")

    @property
    def freq(self):
        """Output signal frequency in Hz."""
        return float(self.query("F?")) * 1e6

    @freq.setter
    def freq(self, freq: float):
        """Set signal frequency in Hz."""
        freq = self.validate_range(freq, 10e6, 15e9)
        self.write(f"F{freq}Hz")

    @property
    def freq_offset(self):
        """Offset frequency that can be added or subtracted to the frequency."""
        return float(self.query("OFF?")) * 1e6

    @freq_offset.setter
    def freq_offset(self, freq_to_set):
        self.write(f"OFF {freq_to_set}Hz")

    @property
    def freq_step(self):
        """Step frequency for the CW mode. Used with increment/decrement."""
        return float(self.query("FS?")) * 1e6

    @freq_step.setter
    def freq_step(self, freq_to_set):
        self.write(f"FS {freq_to_set}Hz")

    def set_freq_increment(self):
        """In CW mode, step frequency is used for increment."""
        self.write("FINC")

    def set_freq_decrement(self):
        """In CW mode, step frequency is used for decrement."""
        self.write("FDEC")

    def get_cw_direction(self):
        """Check direction of CW sweep."""
        ret = self.query("FINC?")
        if ret == "1":
            return "Increment"
        return "Decrement"

    @property
    def sweep_start(self):
        """Start frequency for Sweep mode."""
        return float(self.query("STAR?")) * 1e6

    @sweep_start.setter
    def sweep_start(self, freq_to_set):
        self.write(f"STAR {freq_to_set}Hz")

    @property
    def sweep_stop(self):
        """Stop frequency for Sweep mode."""
        return float(self.query("STOP?")) * 1e6

    @sweep_stop.setter
    def sweep_stop(self, freq_to_set):
        self.write(f"STOP {freq_to_set}Hz")

    @property
    def sweep_step(self):
        """Step frequency for Sweep mode."""
        return float(self.query("STEP?")) * 1e6

    @sweep_step.setter
    def sweep_step(self, freq_to_set):
        self.write(f"STEP {freq_to_set}Hz")

    @property
    def sweep_rate(self):
        """Sweep rate in milliseconds for Sweep mode."""
        return float(self.query("RATE?"))

    @sweep_rate.setter
    def sweep_rate(self, rate_to_set):
        self.write(f"RATE {rate_to_set}")

    @property
    def sweep_rtime(self):
        """Sweep retrace time."""
        return float(self.query("RTIME?"))

    @sweep_rtime.setter
    def sweep_rtime(self, time_to_set):
        self.write(f"RTIME {time_to_set}")

    def sweep_run(self):
        """Start sweep."""
        self.write("Run")

    def sweep_halt(self):
        """Halt sweep."""
        self.write("Halt")

    @property
    def sweep_tmode(self):
        """Set trigger mode.

        Auto trigger is a free-running mode with internal trigger.
        Manual trigger is a single-sweep mode with TRG command.
        External trigger  expects a positive edge on USER PORT.
        External steps waits for trigger and increments frequency by step
        """
        return self.query("TMOD?")

    @sweep_tmode.setter
    def sweep_tmode(self, value):
        if value not in ("AUT0", "MAN", "EXT", "EXTS"):
            raise ValueError(f"Mode {value} non existent")
        self.write(f"TMOD {value}")

    def sweep_trigger(self):
        """Start trigger for manual sweep mode."""
        self.write("TRGR")

    @property
    def list_entry(self):
        """Frequencies in the table for list mode."""
        ret = self.query("L?")
        return ret

    @list_entry.setter
    def list_entry(self, frequencies, powers=None):
        for idx, freq in frequencies:
            if powers is None:
                self.write(f"L {idx} {freq}Hz")
            else:
                self.write(f"L {idx} {freq}Hz {powers[idx]}")
        self.write("SAVE")

    @property
    def power(self):
        """Power of the output in dBm."""
        return float(self.query("PWR?"))

    @power.setter
    def power(self, pow_to_set):
        self.write(f"PWR {pow_to_set}")

    @property
    def power_oen(self):
        """Enable or disable the RF output buffer amplifiers while leaving the synthesizer PLL locked."""
        return self.query("OEN")

    @power_oen.setter
    def power_oen(self, value):
        self.write(f"OEN {value}")

    @property
    def power_pdn(self):
        """Place the synthesizer in a low power mode by disabling most of the synthesizer internal circuits."""
        return self.query("PDN")

    @power_pdn.setter
    def power_pdn(self, value):
        self.write(f"PDN {value}")

    @property
    def am_modulation(self):
        """Enables AM modulation (value in dB)."""
        return float(self.query("AMD?"))

    @am_modulation.setter
    def am_modulation(self, value):
        self.write(f"AMD {value}")

    @property
    def am_frequency(self):
        """AM frequency from 1Hz to 2 kHz."""
        return float(self.query("AMF?"))

    @am_frequency.setter
    def am_frequency(self, freq):
        freq = self.validate_range(freq, 1, 2e3)
        self.write(f"AMF {freq}")

    @property
    def ref_freq(self):
        """Expected value of the external reference frequency."""
        return self.query("REF?")

    @ref_freq.setter
    def ref_freq(self, value):
        self.write(f"REF {value}Hz")

    @property
    def ref_source(self):
        """Check which clock reference is used."""
        ret = int(self.query("REFS?"))
        dict_par = {0: "Internal", 1: "External"}
        return dict_par[ret]

    @ref_source.setter
    def ref_source(self, value):
        if value not in ("Internal", "External", 0, 1):
            raise ValueError(f"Source {value} not supported.")
        if value in (0, "Internal"):
            self.write("REFS 0")
        else:
            self.write("REFS 1")
