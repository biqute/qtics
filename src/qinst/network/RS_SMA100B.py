"""
Controller of the R&S SMA100B RF and microwave signal generator.

.. module:: RS_SMA100B.py
.. moduleauthor:: Marco Gobbo <marco.gobbo@mib.infn.it>
"""
from qinst.network_inst import NetworkInst


class SMA100B(NetworkInst):
    """R&S SMA100B RF and microwave signal generator by Rohde & Schwarz."""

    def reset(self):
        """Reset the instrument to a defined default status."""
        self.write("*RST")

    def clear(self):
        """Clear the output buffer."""
        self.write("*CLS")

    def wait(self):
        """Prevents servicing of the subsequent commands until all preceding commands have been executed and all signals have settled."""
        self.write("*WAI")

    @property
    def is_completed(self) -> bool:
        """Return bool 0 (1) in the event status register (output buffer) when all preceding commands have been executed."""
        return self.query("*OPC?") == "1"

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
        - POC: Queris how often the instrument has been turned on so far
        """
        self.validate_opt(opt, ("OTIM", "POC"))
        return self.query(f"DIAG:INFO:{opt}?")

    @property
    def screen_saver_time(self) -> int:
        """Wait time for the screen saver mode of the display."""
        return int(self.query(f":DISP:PSAV:HOLD?"))

    @screen_saver_time.setter
    def screen_saver_time(self, time: int = 10):
        time = self.validate_range(time, 0, 61)
        self.write(f":DISP:PSAV:HOLD {time}")

    def screen_saver_mode(self, state: str = "OFF"):
        """Activate the screen saver mode of the display."""
        self.validate_opt(state, ("ON", "OFF"))
        self.write(f"DISP:PSAV:STAT {state}")

    @property
    def f_mode(self) -> str:
        """Return the frequency mode for generating the RF output signal."""
        return self.query("SOUR:FREQ:MODE?")

    @f_mode.setter
    def f_mode(self, mode):
        """Set the frequency mode for generating the RF output signal. The selected mode determines the parameters to be used for further frequency settings."""
        self.validate_opt(mode, ("CW", "SWEEP"))
        self.write(f"SOUR:FREQ:MODE {mode}")

    @property
    def f_fixed(self) -> float:
        """Return the frequency of the RF output signal in the selected path."""
        return float(self.query("SOUR:FREQ:CW?"))

    @f_fixed.setter
    def f_fixed(self, f):
        """Set the frequency of the RF output signal in the selected path."""
        f = self.validate_range(f, 8e3, 20e9)
        self.write(f"SOUR:FREQ:CW {f}")

    @property
    def f_mult(self) -> float:
        """Return the multiplication factor of a subsequent downstream instrument."""
        return float(self.query("SOUR:FREQ:MULT?"))

    @f_mult.setter
    def f_mult(self, n: float = 1.0):
        """Set the multiplication factor of a subsequent downstream instrument."""
        n = self.validate_range(n, -10000, 10000)
        self.write(f"SOUR:FREQ:MULT {n}")

    @property
    def f_offset(self) -> float:
        """Return the frequency offset of a downstream instrument."""
        return float(self.query("SOUR:FREQ:OFFS?"))

    @f_offset.setter
    def f_offset(self, f):
        """Set the frequency offset of a downstream instrument."""
        self.validate_range(f, 8e3, 20e9)
        self.write(f"SOUR:FREQ:OFFS {f}")

    @property
    def f_sweep_mode(self) -> str:
        """Return the cycle mode for the frequency sweep."""
        return self.query("TRIG:FSW:SOUR?")

    @property
    def is_f_sweep_completed(self) -> bool:
        """Return the status of the frequency sweep that is running."""
        return self.query("SOUR:SWE:FREQ:RUNN?") == "0"

    @f_sweep_mode.setter
    def f_sweep_mode(self, mode: str = "SING"):
        """Set the cycle mode for the frequency sweep."""
        self.validate_opt(mode, ("EXT", "EAUT"))
        self.write(f"TRIG:FSW:SOUR {mode}")

    @property
    def f_min(self) -> float:
        """Return the start frequency for the RF sweep."""
        return float(self.query("SOUR:FREQ:STAR?"))

    @f_min.setter
    def f_min(self, f: float):
        """Set the start frequency for the RF sweep."""
        f = self.validate_range(f, 8e3, 20e9)
        self.write(f"SOUR:FREQ:STAR {f}")

    @property
    def f_max(self) -> float:
        """Return the stop frequency for the RF sweep."""
        return float(self.query("SOUR:FREQ:STOP?"))

    @f_max.setter
    def f_max(self, f: float):
        """Set the stop frequency for the RF sweep."""
        if 8e3 <= f <= 20e9:
            self.write(f"SOUR:FREQ:STOP {f}")
        else:
            raise ValueError(
                "The maximum frequency of the RF output signal must be 8 kHz to 20 GHz."
            )

    @property
    def f_center(self) -> float:
        """Return the center frequency of the sweep."""
        return float(self.query("SOUR:FREQ:CENT?"))

    @f_center.setter
    def f_center(self, f: float):
        """Set the center frequency of the sweep."""
        f = self.validate_range(f, 8e3, 20e9)
        self.write(f"SOUR:FREQ:STOP {f}")

    @property
    def f_span(self) -> float:
        """Return the span of the frequency sweep range."""
        return float(self.query("SOUR:FREQ:SPAN?"))

    @f_span.setter
    def f_span(self, f: float):
        """Set the span of the frequency sweep range."""
        f = self.validate_range(f, 8e3, 20e9)
        self.write(f"SOUR:FREQ:SPAN {abs(f)}")

    @property
    def f_step(self) -> float:
        """Return the step width for linear sweeps."""
        return float(self.query("SOUR:SWE:FREQ:STEP:LIN?"))

    @f_step.setter
    def f_step(self, value: float = 0.01):
        """Set the step width for linear sweeps."""
        value = self.validate_range(value, 0.001, abs(self.f_max - self.f_min))
        self.write(f"SOUR:SWE:FREQ:STEP:LIN {value} Hz")

    @property
    def f_dwell(self) -> float:
        """Return the dwell time for a frequency sweep step."""
        return float(self.query("SOUR:SWE:FREQ:DWEL?"))

    @f_dwell.setter
    def f_dwell(self, value: float = 0.01):
        """Set the dwell time for a frequency sweep step."""
        value = self.validate_range(value, 0.001, 100)
        self.write(f"SOUR:SWE:FREQ:DWEL {value}")

    @property
    def phase(self) -> float:
        """Return the phase variation relative to the current phase."""
        return float(self.query("SOUR:PHAS?"))

    @phase.setter
    def phase(self, deg: float):
        """Set the phase variation relative to the current phase."""
        deg = self.validate_range(deg, -36000, 36000)
        self.write(f"SOUR:PHAS {deg} DEG")

    def set_phase_ref(self):
        """Assign the value set as the reference phase."""
        self.write("SOUR:PHAS:REF")

    @property
    def p_unit(self) -> str:
        """Return the default unit for all power parameters."""
        return self.query("UNIT:POW?")

    @p_unit.setter
    def p_unit(self, unit: str = "V"):
        """Set the default unit for all power parameters."""
        self.validate_opt(unit, ("V", "DBUV", "DBM"))
        self.write(f"UNIT:POW {unit}")

    @property
    def p_mode(self) -> str:
        """Return the operating mode of the instrument of the set output level."""
        return self.query("SOUR:POW:MODE?")

    @p_mode.setter
    def p_mode(self, mode):
        """Select the operating mode of the instrument to set the output level."""
        self.validate_opt(mode, ("CW", "SWEEP"))
        self.write(f"SOUR:POW:MODE {mode}")

    @property
    def p_fixed(self) -> float:
        """Return the RF level applied to the DUT."""
        return float(self.query("SOUR:POW:LEV:IMM:AMPL?"))

    @p_fixed.setter
    def p_fixed(self, p):
        """Set the RF level applied to the DUT."""
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
        """Return the status of the RF level sweep that is running."""
        return self.query("SOUR:SWE:POW:RUNN?") == "0"

    @property
    def p_min(self) -> float:
        """Return the start RF level for the RF sweep."""
        return float(self.query("SOUR:POW:STAR?"))

    @p_min.setter
    def p_min(self, p: float):
        """Set the start RF level for the RF sweep."""
        self.write(f"SOUR:POW:STAR {p}")

    @property
    def p_max(self) -> float:
        """Return the stop RF level for the RF sweep."""
        return float(self.query("SOUR:POW:STOP?"))

    @p_max.setter
    def p_max(self, p: float):
        """Set the stop RF level for the RF sweep."""
        self.write(f"SOUR:POW:STOP {p}")

    @property
    def p_dwell(self) -> float:
        """Return the dwell time for a level sweep step."""
        return float(self.query("SOUR:SWE:POW:DWEL?"))

    @p_dwell.setter
    def p_dwell(self, value: float = 0.01):
        """Set the dwell time for a level sweep step."""
        value = self.validate_range(value, 0.001, 100)
        self.write(f"SOUR:SWE:POW:DWEL {value}")

    @property
    def p_step(self) -> float:
        """Return a logarithmically determined step size for the RF level sweep."""
        return float(self.query("SOUR:SWE:POW:STEP:LOG?"))

    @p_step.setter
    def p_step(self, value: float = 1.0):
        """Set a logarithmically determined step size for the RF level sweep. The level is increased by a logarithmically calculated fraction of the current level."""
        value = self.validate_range(value, 0.01, 139)
        self.write(f"SOUR:SWE:POW:STEP:LOG {value} DB")

    def sweep(self):
        """Perform a one-off RF frequency/level sweep."""
        self.write("*TRG")