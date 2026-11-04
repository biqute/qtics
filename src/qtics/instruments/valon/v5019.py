"""20GHz Frequency Synthesizer module Valon Model 5019."""

from qtics.instruments.base import MessageInstrument
from qtics.instruments.types import RFSource
from qtics.instruments.utils import to_bool
from qtics.transport import SerialTransport, Transport


class Valon5019(RFSource, MessageInstrument):
    """Frequency synthesizer driver for Valon 5019."""

    default_transport = SerialTransport
    transport_defaults = {
        "baudrate": 9600,
        "timeout": 10,
        "terminator": "\r",
        "delay": 0.3,
    }

    def __init__(
        self, transport: Transport | str, name: str = "Valon5019", **transport_kwargs
    ):
        """Initialize."""
        super().__init__(transport, name, **transport_kwargs)
        self.last_cmd_lenght = 0

    @staticmethod
    def freq_result_to_hz(res):
        """Convert list [value, unit] to Hz value."""
        value, unit = res
        value = float(value)

        match unit:
            case "Hz":
                return value
            case "KHz":
                return value * 1e3
            case "MHz":
                return value * 1e6
            case "GHz":
                return value * 1e9
            case _:
                raise ValueError(f"Unknown frequency unit {unit}.")

    def get_id(self) -> str:
        """Return the name of the device."""
        return " ".join(self.query("ID"))

    def reset(self, defaults: bool = True):
        """Reset all values, then restore the default values."""
        self.write("RST")
        super().reset(defaults)

    def write(self, cmd, sleep=False):
        """Write a message to the serial port."""
        self.last_cmd_lenght = len(cmd + self.transport.terminator) + 2
        super().write(cmd, sleep)

    def read(self):
        """Read a message, removing the echo of the command and splitting in tokens."""
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
    def frequency(self):
        """Output signal frequency in Hz."""
        res = self.query("F")
        return self.freq_result_to_hz(res)

    @frequency.setter
    def frequency(self, freq: float):
        """Set signal frequency in Hz."""
        freq = self.validate_range(freq, 10e6, 20e9)
        self.write(f"F{freq}Hz")

    @property
    def f_offset(self):
        """Offset frequency that can be added or subtracted to the frequency."""
        res = self.query("OFF")
        return self.freq_result_to_hz(res)

    @f_offset.setter
    def f_offset(self, freq_to_set):
        freq_to_set = self.validate_range(freq_to_set, 0, 4.25e9)
        self.write(f"OFF {freq_to_set}Hz")

    @property
    def f_step_cw(self):
        """Step frequency for the CW mode. Used with increment/decrement."""
        res = self.query("FS")
        return self.freq_result_to_hz(res)

    @f_step_cw.setter
    def f_step_cw(self, freq_to_set):
        freq_to_set = self.validate_range(freq_to_set, 0, 4e9)
        self.write(f"FS {freq_to_set}Hz")

    def increment_freq(self):
        """In CW mode, step frequency is used for increment."""
        res = self.query("FINC")
        return self.freq_result_to_hz(res)

    def decrement_freq(self):
        """In CW mode, step frequency is used for decrement."""
        res = self.query("FDEC")
        return self.freq_result_to_hz(res)

    @property
    def f_start(self):
        """Start frequency for Sweep mode."""
        res = self.query("STAR")
        return self.freq_result_to_hz(res)

    @f_start.setter
    def f_start(self, freq_to_set):
        freq_to_set = self.validate_range(freq_to_set, 0, 42.5e9)
        self.write(f"STAR {freq_to_set}Hz")

    @property
    def f_stop(self):
        """Stop frequency for Sweep mode."""
        res = self.query("STOP")
        return self.freq_result_to_hz(res)

    @f_stop.setter
    def f_stop(self, freq_to_set):
        freq_to_set = self.validate_range(freq_to_set, 0, 42.5e9)
        self.write(f"STOP {freq_to_set}Hz")

    @property
    def f_step(self):
        """Step frequency for Sweep mode."""
        res = self.query("STEP")
        return self.freq_result_to_hz(res)

    @f_step.setter
    def f_step(self, freq_to_set):
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
    def list_entry(self, frequencies):
        for idx, freq in enumerate(frequencies):
            self.write(f"LI {idx+1} {freq}Hz")
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
    def output(self) -> bool:
        """Enable or disable the RF output buffer amplifiers, leaving the PLL locked."""
        return self.query("OEN")[0] == "1"  # codespell:ignore

    @output.setter
    def output(self, value: bool):
        state = to_bool(value) if isinstance(value, str) else bool(value)
        self.write(f"OEN {int(state)}")  # codespell:ignore

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
        else:
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
        return self.freq_result_to_hz(res)

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
