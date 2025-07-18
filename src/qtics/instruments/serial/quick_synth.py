"""
QuickSyn microwave synthesizers by National Instruments.

.. module:: synth_FSL0010.py
.. moduleauthor:: Pietro Campana <campana.pietro@campus.unimib.it>
"""

from typing import Literal

import serial

from qtics.instruments import SerialInst

DEFAULT_FREQ_SCALE = 1e-3  # Convert mHz to Hz


class FSQS(SerialInst):
    """QuickSyn microwave synthesizer by National Instruments."""

    def __init__(
        self,
        name: str,
        address: str,
        baudrate: int = 115200,
        bytesize: int = serial.EIGHTBITS,
        parity: Literal["N"] = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        timeout: int = 10,
        sleep: float = 0.1,
    ):
        """Initialize."""
        super().__init__(
            name, address, baudrate, bytesize, parity, stopbits, timeout, sleep
        )

        self.min_freq = 0.5e9
        self.max_freq = 10e9

    @property
    def freq(self) -> float:
        """Output signal frequency in Hz."""
        return float(self.query("FREQ?")) * DEFAULT_FREQ_SCALE

    @freq.setter
    def freq(self, freq: float):
        freq = self.validate_range(freq, self.min_freq, self.max_freq)
        self.write(f"FREQ {freq / DEFAULT_FREQ_SCALE}mlHz")

    @property
    def output_on(self) -> bool:
        """Turn on RF output."""
        return self.query("OUTP:STAT?") == "ON"

    @output_on.setter
    def output_on(self, on: bool):
        if on:
            self.write("OUTP:STAT ON")
        else:
            self.write("OUTP:STAT OFF")

    @property
    def ext_ref_source(self) -> bool:
        """Use external reference source."""
        return self.query("ROSC:SOUR?") == "EXT"

    @ext_ref_source.setter
    def ext_ref_source(self, ext: bool):
        if ext:
            self.write("ROSC:SOUR EXT")
        else:
            self.write("ROSC:SOUR INT")

    @property
    def temperature(self) -> float:
        """Temperature in degrees Celsius."""
        return float(self.query("DIAG:MEAS? 21"))


class FSL0010(FSQS):
    """FSL_0010 QuickSyn."""

    min_freq = 0.65e9
    max_freq = 10e9


class FSL0020(FSQS):
    """FSW_0020 QuickSyn."""

    min_freq = 0.65e9
    max_freq = 20e9


class FSW0010(FSQS):
    """FSL_0010 QuickSyn."""

    min_freq = 0.5e9
    max_freq = 10e9


class FSW0020(FSQS):
    """FSW_0020 QuickSyn."""

    min_freq = 0.5e9
    max_freq = 20e9
