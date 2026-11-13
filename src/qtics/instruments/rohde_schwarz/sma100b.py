"""
Controller of the R&S SMA100B RF and microwave signal generator.

.. moduleauthor:: Marco Gobbo <marco.gobbo@mib.infn.it>
"""

from qtics.instruments.base import SCPIInstrument
from qtics.instruments.types import RFSource
from qtics.instruments.utils import to_bool
from qtics.transport import SocketTransport, Transport


class SMA100B(RFSource, SCPIInstrument):
    """R&S SMA100B RF and microwave signal generator by Rohde & Schwarz.

    The RF level readback depends on the power unit set with ``p_unit``. To
    comply with the :class:`RFSource` interface (``power`` in dBm), the unit is
    set to dBm right after connecting. ``p_unit`` stays available, but changing
    it makes ``power`` read and write in that unit.

    Frequencies are the displayed ones, ``f_rf * f_mult + f_offset``: their range
    follows the multiplier and offset of a downstream instrument. These are read
    when connecting and tracked by the ``f_mult``/``f_offset`` properties (a change
    from the front panel is seen after reading them or reconnecting).
    """

    default_transport = SocketTransport
    transport_defaults = {"port": 5025, "timeout": 10, "delay": 0.1, "no_delay": True}

    rf_min = 8e3
    """Minimum RF output frequency [Hz]."""
    rf_max = 20e9
    """Maximum RF output frequency [Hz], depends on the frequency option."""

    def __init__(
        self, transport: Transport | str, name: str = "SMA100B", **transport_kwargs
    ):
        """Initialize instrument."""
        super().__init__(transport, name, **transport_kwargs)
        self._f_mult = 1.0
        self._f_offset = 0.0

    def _after_connect(self):
        self.write("UNIT:POW DBM")
        _ = self.f_mult, self.f_offset  # read them to set the frequency range

    def reset(self, defaults: bool = True):
        """Reset the instrument (multiplier 1, offset 0), then restore the defaults."""
        self._f_mult, self._f_offset = 1.0, 0.0
        super().reset(defaults)

    def _validate_frequency(self, f: float) -> float:
        """Clip a displayed frequency to the range allowed by multiplier and offset."""
        mult = self._f_mult or 1.0  # a zero multiplier is not a valid setting
        limits = sorted(rf * mult + self._f_offset for rf in (self.rf_min, self.rf_max))
        return self.validate_range(f, *limits)

    def cal(self, opt: str) -> str:
        """Query the device to perform internal adjustments.

        Valid options to query:
        - MEAS: Starts all internal adjustments that do not need external measuring equipment
        - DATE: Queries the date of the most recently executed full adjustment
        - INF: Queries the current state of the internal adjustment
        - TEMP: Queries the temperature deviation compared to the calibration temperature
        - TIME: Queries the time elapsed since the last full adjustment
        """
        self.validate_opt(opt, ("MEAS", "DATE", "INF", "TEMP", "TIME"))
        return self.query(f"CAL:ALL:{opt}?")

    def diag(self, opt: str) -> str:
        """Query the device to perform diagnosis and servicing.

        Valid options to query:
        - OTIM: Queries the operating hours of the instrument so far
        - POC: Queries how often the instrument has been turned on so far
        """
        self.validate_opt(opt, ("OTIM", "POC"))
        return self.query(f"DIAG:INFO:{opt}?")

    @property
    def screen_saver_time(self) -> int:
        """Wait time for the screen saver mode of the display."""
        return int(self.query("DISP:PSAV:HOLD?"))

    @screen_saver_time.setter
    def screen_saver_time(self, time: int = 10):
        time = self.validate_range(time, 0, 61)
        self.write(f"DISP:PSAV:HOLD {time}")

    def screen_saver_mode(self, state: str = "OFF"):
        """Activate the screen saver mode of the display."""
        self.validate_opt(state, ("ON", "OFF"))
        self.write(f"DISP:PSAV:STAT {state}")

    @property
    def output(self) -> bool:
        """Whether the RF output signal is active."""
        return to_bool(self.query("OUTP:STAT?"))

    @output.setter
    def output(self, state: bool):
        self.write(f"OUTP:STAT {'ON' if state else 'OFF'}")

    @property
    def f_mode(self) -> str:
        """Frequency mode for generating the RF output signal."""
        return self.query("SOUR:FREQ:MODE?")

    @f_mode.setter
    def f_mode(self, mode: str):
        self.validate_opt(mode, ("CW", "SWEEP"))
        self.write(f"SOUR:FREQ:MODE {mode}")

    @property
    def frequency(self) -> float:
        """Frequency of the RF output signal in the selected path."""
        return float(self.query("SOUR:FREQ:CW?"))

    @frequency.setter
    def frequency(self, f: float):
        f = self._validate_frequency(f)
        self.write(f"SOUR:FREQ:CW {f}")

    @property
    def f_mult(self) -> float:
        """Multiplication factor of a subsequent downstream instrument."""
        self._f_mult = float(self.query("SOUR:FREQ:MULT?"))
        return self._f_mult

    @f_mult.setter
    def f_mult(self, n: float = 1.0):
        n = self.validate_range(n, -10000, 10000)
        self.write(f"SOUR:FREQ:MULT {n}")
        self._f_mult = n

    @property
    def f_offset(self) -> float:
        """Frequency offset of a downstream instrument."""
        self._f_offset = float(self.query("SOUR:FREQ:OFFS?"))
        return self._f_offset

    @f_offset.setter
    def f_offset(self, f: float):
        # No range in the manual, the instrument shifts the RF range by the offset
        self.write(f"SOUR:FREQ:OFFS {f}")
        self._f_offset = f

    @property
    def f_sweep_mode(self) -> str:
        """Cycle mode for the frequency sweep."""
        return self.query("TRIG:FSW:SOUR?")

    @f_sweep_mode.setter
    def f_sweep_mode(self, mode: str = "SING"):
        """Set the cycle mode for the frequency sweep."""
        self.validate_opt(mode, ("AUTO", "SING", "EXT", "EAUT"))
        self.write(f"TRIG:FSW:SOUR {mode}")

    @property
    def is_f_sweep_completed(self) -> bool:
        """Status of the frequency sweep that is running."""
        return self.query("SOUR:SWE:FREQ:RUNN?") == "0"

    @property
    def f_start(self) -> float:
        """Start frequency for the RF sweep."""
        return float(self.query("SOUR:FREQ:STAR?"))

    @f_start.setter
    def f_start(self, f: float):
        f = self._validate_frequency(f)
        self.write(f"SOUR:FREQ:STAR {f}")

    @property
    def f_stop(self) -> float:
        """Stop frequency for the RF sweep."""
        return float(self.query("SOUR:FREQ:STOP?"))

    @f_stop.setter
    def f_stop(self, f: float):
        f = self._validate_frequency(f)
        self.write(f"SOUR:FREQ:STOP {f}")

    @property
    def f_center(self) -> float:
        """Center frequency of the sweep."""
        return float(self.query("SOUR:FREQ:CENT?"))

    @f_center.setter
    def f_center(self, f: float):
        f = self._validate_frequency(f)
        self.write(f"SOUR:FREQ:CENT {f}")

    @property
    def f_span(self) -> float:
        """Span of the frequency sweep range."""
        return float(self.query("SOUR:FREQ:SPAN?"))

    @f_span.setter
    def f_span(self, f: float):
        f = self.validate_range(
            abs(f), 0, (self.rf_max - self.rf_min) * abs(self._f_mult)
        )
        self.write(f"SOUR:FREQ:SPAN {f}")

    @property
    def f_step(self) -> float:
        """Step width for linear sweeps."""
        return float(self.query("SOUR:SWE:FREQ:STEP:LIN?"))

    @f_step.setter
    def f_step(self, f: float = 0.01):
        f = self.validate_range(f, 0.001, abs(self.f_stop - self.f_start))
        self.write(f"SOUR:SWE:FREQ:STEP:LIN {f} Hz")

    @property
    def f_dwell(self) -> float:
        """Dwell time for a frequency sweep step."""
        return float(self.query("SOUR:SWE:FREQ:DWEL?"))

    @f_dwell.setter
    def f_dwell(self, value: float = 0.01):
        value = self.validate_range(value, 0.001, 100)
        self.write(f"SOUR:SWE:FREQ:DWEL {value}")

    @property
    def phase(self) -> float:
        """Phase variation relative to the current phase."""
        return float(self.query("SOUR:PHAS?"))

    @phase.setter
    def phase(self, deg: float):
        deg = self.validate_range(deg, -36000, 36000)
        self.write(f"SOUR:PHAS {deg} DEG")

    def set_phase_ref(self):
        """Assign the value set as the reference phase."""
        self.write("SOUR:PHAS:REF")

    @property
    def p_unit(self) -> str:
        """Default unit for all power parameters."""
        return self.query("UNIT:POW?")

    @p_unit.setter
    def p_unit(self, unit: str = "V"):
        self.validate_opt(unit, ("V", "DBUV", "DBM"))
        self.write(f"UNIT:POW {unit}")

    @property
    def p_mode(self) -> str:
        """Operating mode of the instrument of the set output level."""
        return self.query("SOUR:POW:MODE?")

    @p_mode.setter
    def p_mode(self, mode):
        self.validate_opt(mode, ("CW", "SWEEP"))
        self.write(f"SOUR:POW:MODE {mode}")

    @property
    def power(self) -> float:
        """RF level applied to the DUT [dBm, unless ``p_unit`` was changed]."""
        return float(self.query("SOUR:POW:LEV:IMM:AMPL?"))

    @power.setter
    def power(self, p):
        self.write(f"SOUR:POW:LEV:IMM:AMPL {p}")

    @property
    def p_sweep_mode(self) -> str:
        """Mode of the power sweep."""
        return self.query("TRIG:PSW:SOUR?")

    @p_sweep_mode.setter
    def p_sweep_mode(self, mode: str = "SING"):
        self.validate_opt(mode, ("AUTO", "SING", "EXT", "EAUT"))
        self.write(f"TRIG:PSW:SOUR {mode}")

    @property
    def is_p_sweep_completed(self) -> bool:
        """Status of the RF level sweep that is running."""
        return self.query("SOUR:SWE:POW:RUNN?") == "0"

    @property
    def p_start(self) -> float:
        """Start RF level for the RF sweep."""
        return float(self.query("SOUR:POW:STAR?"))

    @p_start.setter
    def p_start(self, p: float):
        self.write(f"SOUR:POW:STAR {p}")

    @property
    def p_stop(self) -> float:
        """Stop RF level for the RF sweep."""
        return float(self.query("SOUR:POW:STOP?"))

    @p_stop.setter
    def p_stop(self, p: float):
        self.write(f"SOUR:POW:STOP {p}")

    @property
    def p_step(self) -> float:
        """Logarithmically determined step size for the RF level sweep."""
        return float(self.query("SOUR:SWE:POW:STEP:LOG?"))

    @p_step.setter
    def p_step(self, p: float = 1.0):
        p = self.validate_range(p, 0.01, 139)
        self.write(f"SOUR:SWE:POW:STEP:LOG {p} DB")

    @property
    def p_dwell(self) -> float:
        """Dwell time for a level sweep step."""
        return float(self.query("SOUR:SWE:POW:DWEL?"))

    @p_dwell.setter
    def p_dwell(self, value: float = 0.01):
        value = self.validate_range(value, 0.001, 100)
        self.write(f"SOUR:SWE:POW:DWEL {value}")

    def sweep(self):
        """Perform a one-off RF frequency/level sweep."""
        self.write("*TRG")
