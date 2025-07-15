"""
20GHz Frequency Synthesizer module Valon Model 5019.

.. module:: valon_5019.py
"""

from typing import Literal

import serial

from qtics.instruments import SerialInst


def freq_result_to_hz(res):
    """Convert list [value, unit] to Hz value."""
    if res[1] == "MHz":
        return float(res[0]) * 1e6
    if res[1] == "KHz":
        return float(res[0]) * 1e3
    if res[1] == "Hz":
        return float(res[0])
    return res


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
        sleep: float = 0.3,
    ):
        """Initialize."""
        super().__init__(
            name, address, baudrate, bytesize, parity, stopbits, timeout, sleep, "\r"
        )
        self.last_cmd_lenght = 0

    def get_id(self):
        """Return name of the device from SCPI standard query."""
        return " ".join(self.query("ID"))

    def reset(self):
        """Reset all values."""
        self.write("RST")

    def write(self, cmd, sleep=False):
        """Write a message to the serial port."""
        self.last_cmd_lenght = len(cmd + self.terminator) + 2
        super().write(cmd, sleep)

    def read(self):
        """Read a message from the serial port."""
        res = super().read()
        if res != "":
            res = res[self.last_cmd_lenght :]
            res = res.split(";")[0]
            res = res.split("\r\n\r-->")[0]
            res = res.split(" ")
        return res[1:]

    @property
    def mode(self):
        """Return current mode of operation (continuous tone, sweep, list)."""
        return self.query("MOD")[0]

    @mode.setter
    def mode(self, mode_to_set):
        """Set mode of operation (continuous tone, sweep, list)."""
        if mode_to_set not in ("CW", "SWE", "LIST"):
            raise ValueError(f"Mode {mode_to_set} not supported.")
        self.write(f"MOD {mode_to_set}")

    @property
    def freq(self):
        """Output signal frequency in Hz."""
        res = self.query("F")
        return freq_result_to_hz(res)

    @freq.setter
    def freq(self, freq: float):
        """Set signal frequency in Hz."""
        freq = self.validate_range(freq, 10e6, 15e9)
        self.write(f"F{freq}Hz")

    @property
    def freq_offset(self):
        """Offset frequency that can be added or subtracted to the frequency."""
        res = self.query("OFF")
        return freq_result_to_hz(res)

    @freq_offset.setter
    def freq_offset(self, freq_to_set):
        freq_to_set = self.validate_range(freq_to_set, 0, 4.25e9)
        self.write(f"OFF {freq_to_set}Hz")

    @property
    def freq_step(self):
        """Step frequency for the CW mode. Used with increment/decrement."""
        res = self.query("FS")
        return freq_result_to_hz(res)

    @freq_step.setter
    def freq_step(self, freq_to_set):
        freq_to_set = self.validate_range(freq_to_set, 0, 4e9)
        self.write(f"FS {freq_to_set}Hz")

    def increment_freq(self):
        """In CW mode, step frequency is used for increment."""
        res = self.query("FINC")
        return freq_result_to_hz(res)

    def decrement_freq(self):
        """In CW mode, step frequency is used for decrement."""
        res = self.query("FDEC")
        return freq_result_to_hz(res)

    @property
    def sweep_start(self):
        """Start frequency for Sweep mode."""
        res = self.query("STAR")
        return freq_result_to_hz(res)

    @sweep_start.setter
    def sweep_start(self, freq_to_set):
        freq_to_set = self.validate_range(freq_to_set, 0, 42.5e9)
        self.write(f"STAR {freq_to_set}Hz")

    @property
    def sweep_stop(self):
        """Stop frequency for Sweep mode."""
        res = self.query("STOP")
        return freq_result_to_hz(res)

    @sweep_stop.setter
    def sweep_stop(self, freq_to_set):
        freq_to_set = self.validate_range(freq_to_set, 0, 42.5e9)
        self.write(f"STOP {freq_to_set}Hz")

    @property
    def sweep_step(self):
        """Step frequency for Sweep mode."""
        res = self.query("STEP")
        return freq_result_to_hz(res)

    @sweep_step.setter
    def sweep_step(self, freq_to_set):
        freq_to_set = self.validate_range(freq_to_set, 10, 4.25e9)
        self.write(f"STEP {freq_to_set}Hz")

    @property
    def sweep_rate(self):
        """Sweep rate in milliseconds for Sweep mode."""
        return float(self.query("RATE")[0])

    @sweep_rate.setter
    def sweep_rate(self, rate_to_set):
        self.write(f"RATE {rate_to_set}")

    @property
    def sweep_rtime(self):
        """Sweep retrace time."""
        return float(self.query("RTIME")[0])

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
        return self.query("TMOD")[0]

    @sweep_tmode.setter
    def sweep_tmode(self, value):
        if value not in ("AUTO", "MAN", "EXT", "EXTS"):
            raise ValueError(f"Mode {value} non existent")
        self.write(f"TMOD {value}")

    def sweep_trigger(self):
        """Start trigger for manual sweep mode."""
        self.write("TRGR")

    @property
    def list_entry(self):
        """Frequencies in the table for list mode."""
        raise NotImplementedError(
            "Reading frequencies list is currently not compatible with the split in read()."
        )

    @list_entry.setter
    def list_entry(self, frequencies, powers=None):
        for idx, freq in frequencies:
            if powers is None:
                self.write(f"LI {idx+1} {freq}Hz")
            else:
                self.write(f"LI {idx+1} {freq}Hz {powers[idx]}")
        self.write("SAVE")

    @property
    def power(self):
        """Power of the output in dBm."""
        return float(self.query("PWR")[0])

    @power.setter
    def power(self, pow_to_set):
        pow_to_set = self.validate_range(pow_to_set, -50, 20)
        self.write(f"PWR {pow_to_set}")

    @property
    def power_oen(self):
        """Enable or disable the RF output buffer amplifiers while leaving the synthesizer PLL locked."""
        return self.query("OEN")[0] == "1"

    @power_oen.setter
    def power_oen(self, value):
        if value in (True, 1, "True"):
            self.write(f"OEN 1")
        elif value in (False, 0, "False"):
            self.write(f"OEN 0")
        raise ValueError(f"Value {value} not supported.")

    @property
    def power_pdn(self):
        """Place the synthesizer in a low power mode by disabling most of the synthesizer internal circuits."""
        return self.query("PDN")[0] == "1"

    @power_pdn.setter
    def power_pdn(self, value):
        if value in (True, 1, "True"):
            self.write(f"PDN 1")
        elif value in (False, 0, "False"):
            self.write(f"PDN 0")
        raise ValueError(f"Value {value} not supported.")

    @property
    def am_modulation(self):
        """Enables AM modulation (value in dB)."""
        return float(self.query("AMD")[0])

    @am_modulation.setter
    def am_modulation(self, value):
        value = self.validate_range(value, 0, 50)
        self.write(f"AMD {value}")

    @property
    def am_frequency(self):
        """AM frequency from 1Hz to 2 kHz."""
        return float(self.query("AMF")[0])

    @am_frequency.setter
    def am_frequency(self, freq):
        freq = self.validate_range(freq, 0.5, 1e4)
        self.write(f"AMF {freq}")

    @property
    def ref_freq(self):
        """Expected value of the external reference frequency."""
        res = self.query("REF")
        return freq_result_to_hz(res)

    @ref_freq.setter
    def ref_freq(self, value):
        self.write(f"REF {value}Hz")

    @property
    def ref_source(self):
        """Check which clock reference is used."""
        ret = int(self.query("REFS")[0])
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
