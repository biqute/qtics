"""
FSW0010 QuickSyn microwave synthesizer by National Instruments.

.. module:: synth_FSW0010.py
.. moduleauthor:: Pietro Campana <campana.pietro@campus.unimib.it>
"""
from typing import Literal

import serial

from qinst.serial_inst import SerialInst


class FSW0010(SerialInst):
    """FSW0010 QuickSyn microwave synthesizer by National Instruments."""

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
        self.__default_freq_scale = 1e-3

    @property
    def freq(self) -> float:
        """Output signal frequency in Hz."""
        return float(self.query("FREQ?")) * self.__default_freq_scale

    @freq.setter
    def freq(self, freq: float):
        freq = self.validate_range(freq, 0.1e9, 10e9)
        self.write(f"FREQ {freq/self.__default_freq_scale}mlHz")

    @property
    def power(self) -> float:
        """Output power in dBm."""
        return float(self.query("POW?"))

    @power.setter
    def power(self, pow: float):
        pow = self.validate_range(pow, -25, 15)
        self.write(f"POW {pow}")

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
