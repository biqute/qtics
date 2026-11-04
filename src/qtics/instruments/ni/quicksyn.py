"""QuickSyn microwave synthesizers by National Instruments."""

from qtics.instruments.base import SCPIInstrument
from qtics.instruments.types import RFSource
from qtics.instruments.utils import to_bool
from qtics.transport import SerialTransport, Transport

DEFAULT_FREQ_SCALE = 1e-3  # Convert mHz to Hz


class QuickSyn(RFSource, SCPIInstrument):
    """QuickSyn microwave synthesizer by National Instruments."""

    min_freq = 0.5e9
    max_freq = 10e9

    default_transport = SerialTransport
    transport_defaults = {"baudrate": 115200, "timeout": 10, "delay": 0.1}

    def __init__(
        self, transport: Transport | str, name: str = "QuickSyn", **transport_kwargs
    ):
        """Initialize."""
        super().__init__(transport, name, **transport_kwargs)

    @property
    def frequency(self) -> float:
        """Output signal frequency in Hz."""
        return float(self.query("FREQ?")) * DEFAULT_FREQ_SCALE

    @frequency.setter
    def frequency(self, freq: float):
        freq = self.validate_range(freq, self.min_freq, self.max_freq)
        self.write(f"FREQ {freq / DEFAULT_FREQ_SCALE}mlHz")

    @property
    def output(self) -> bool:
        """Whether the RF output is on."""
        return to_bool(self.query("OUTP:STAT?"))

    @output.setter
    def output(self, on: bool):
        self.write("OUTP:STAT ON" if on else "OUTP:STAT OFF")

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


class FSL0010(QuickSyn):
    """FSL_0010 QuickSyn."""

    min_freq = 0.65e9
    max_freq = 10e9


class FSL0020(QuickSyn):
    """FSL_0020 QuickSyn."""

    min_freq = 0.65e9
    max_freq = 20e9


class FSW0010(QuickSyn):
    """FSW_0010 QuickSyn."""

    min_freq = 0.5e9
    max_freq = 10e9


class FSW0020(QuickSyn):
    """FSW_0020 QuickSyn."""

    min_freq = 0.5e9
    max_freq = 20e9
