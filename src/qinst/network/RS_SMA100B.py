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

    def cal(self, opt) -> str:
        """Query the device to perform internal adjustments.

        Valid options to query:
        - MEAS: Starts all internal adjustments that do not need external measuring equipment
        - DATE: Queries the date of the most recently executed full adjustment
        - INF: Queries the current state of the internal adjustment
        - TEMP: Queries the temperature deviation compared to the calibration temperature
        - TIME: Queries the time elapsed since the last full adjustment
        - FACT:DATE: Queries the date of the last factory calibration
        """
        opts = ("MEAS", "DATE", "INF", "TEMP", "TIME")
        if opt in opts:
            return self.query(f"CAL:ALL:{opt}?")
        raise ValueError(f"Invalid option selected, choose between {opts}.")

    def diag(self, opt):
        """Query the device to perform diagnosis and servicing.

        Valid options to query:
        - OTIM: Queries the operating hours of the instrument so far
        - POC: Queris how often the instrument has been turned on so far
        """
        opts = ("OTIM", "POC")
        if opt in opts:
            return self.query(f"DIAG:INFO:{opt}?")
        raise ValueError(f"Invalid option selected, choose between {opts}.")

    def set_screen_saver(self, time=10):
        """Set the wait time for the screen saver mode of the display."""
        if time in range(1, 61):
            self.write(f":DISP:PSAV:HOLD {time}")
        else:
            raise ValueError(
                "The wait time for the screen saver mode of the display must be 1 to 60 minutes."
            )

    def screen_saver_mode(self, state: str):
        """Activate the screen saver mode of the display."""
        states = ("ON", "OFF")
        if state in states:
            self.write(f"DISP:PSAV:STAT {state}")
        else:
            raise ValueError(f"Invalid option selected, choose between {states}.")

    @property
    def f_mode(self) -> str:
        """Return the frequency mode for generating the RF output signal."""
        return self.query("SOUR:FREQ:MODE?")

    @f_mode.setter
    def f_mode(self, mode):
        """Set the frequency mode for generating the RF output signal.

        The selected mode determines the parameters to be used for further frequency settings.
        """
        allowed = ("CW", "SWEEP")
        if mode in allowed:
            self.write(f"SOUR:FREQ:MODE {mode}")
        else:
            raise ValueError(f"Invalid mode selected, choose between {allowed}.")

    @property
    def f_fixed(self) -> float:
        """Return the frequency of the RF output signal in the selected path."""
        return float(self.query("SOUR:FREQ:CW?"))

    @f_fixed.setter
    def f_fixed(self, f):
        """Set the frequency of the RF output signal in the selected path."""
        self.write(f"SOUR:FREQ:CW {f}")

    @property
    def f_min(self) -> float:
        """Return the start frequency for the RF sweep."""
        return float(self.query("SOUR:FREQ:STAR?"))

    @f_min.setter
    def f_min(self, f: float):
        """Set the start frequency for the RF sweep."""
        self.write(f"SOUR:FREQ:STAR {f}")

    @property
    def f_max(self) -> float:
        """Return the stop frequency for the RF sweep."""
        return float(self.query("SOUR:FREQ:STOP?"))

    @f_max.setter
    def f_max(self, f: float):
        """Set the stop frequency for the RF sweep."""
        self.write(f"SOUR:FREQ:STOP {f}")

    @property
    def f_center(self) -> float:
        """Return the center frequency of the sweep."""
        return float(self.query("SOUR:FREQ:CENT?"))

    @f_center.setter
    def f_center(self, f: float):
        """Set the center frequency of the sweep."""
        self.write(f"SOUR:FREQ:CENT {f}")

    @property
    def f_span(self) -> float:
        """Return the span of the frequency sweep range."""
        return float(self.query("SOUR:FREQ:SPAN?"))

    @f_span.setter
    def f_span(self, f: float):
        """Set the span of the frequency sweep range."""
        self.write(f"SOUR:FREQ:SPAN {abs(f)}")

    @property
    def f_mult(self) -> float:
        """Return the multiplication factor of a subsequent downstream instrument."""
        return float(self.query("SOUR:FREQ:MULT?"))

    @f_mult.setter
    def f_mult(self, n):
        """Set the multiplication factor of a subsequent downstream instrument."""
        self.write(f"SOUR:FREQ:MULT {n}")

    @property
    def f_offset(self) -> float:
        """Return the frequency offset of a downstream instrument."""
        return float(self.query("SOUR:FREQ:OFFS?"))

    @f_offset.setter
    def f_offset(self, f):
        """Set the frequency offset of a downstream instrument."""
        self.write(f"SOUR:FREQ:OFFS {f}")

    @property
    def is_f_sweep_completed(self) -> bool:
        """Return the status of the frequency sweep that is running."""
        status = self.query("SOUR:SWE:FREQ:RUNN?")
        return status == "0"

    def f_sweep(self):
        """Perform a one-off RF frequency sweep."""
        self.write("SOUR:SWE:FREQ:EXEC")

    def set_phase(self, deg: float):
        """Set the phase variation relative to the current phase."""
        if deg in range(-36000, 36000):
            self.write(f"SOUR1:PHAS {deg} DEG")
        else:
            raise ValueError(
                "The phase variation relative to the current phase must be -36000 to 36000 degrees."
            )

    def set_phase_ref(self):
        """Assign the value set as the reference phase."""
        self.write("SOUR:PHAS:REF")

    @property
    def p_mode(self) -> str:
        """Return the operating mode of the instrument of the set output level."""
        return str(self.query("SOUR:POW:MODE?"))

    @p_mode.setter
    def p_mode(self, mode):
        """Select the operating mode of the instrument to set the output level."""
        allowed = ("CW", "SWEEP")
        if mode in allowed:
            self.write(f"SOUR:POW:MODE {mode}")
        else:
            raise ValueError(f"Invalid mode selected, choose between {allowed}.")

    @property
    def p_fixed(self) -> float:
        """Return the RF level applied to the DUT."""
        return float(self.query("SOUR:POW:LEV:IMM:AMPL?"))

    @p_fixed.setter
    def p_fixed(self, p):
        """Set the RF level applied to the DUT."""
        self.write(f"SOUR:POW:LEV:IMM:AMPL {p}")

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

    def p_sweep(self):
        """Perform a one-off RF level sweep."""
        self.write("SOUR:SWE:POW:EXEC")

    @property
    def is_p_sweep_completed(self) -> bool:
        """Return the status of the RF level sweep that is running."""
        status = self.query("SOUR:SWE:POW:RUNN?")
        return status == "0"
