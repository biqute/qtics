from qinst.network_inst import NetworkInst


class SMA100B(NetworkInst):
    """R&S SMA100B RF and microwave signal generator by Rohde & Schwarz."""

    def __init__(
        self,
        name: str,
        address: str,
        port: int = 5025,
        timeout: int = 10,
        sleep: float = 0.1,
        no_delay=True,
    ):
        super().__init__(name, address, port, timeout, sleep, no_delay)

    def reset(self):
        """Resets the instrument to a defined default status."""
        self.write("*RST")

    def clear(self):
        """Clears the output buffer."""
        self.write("*CLS")

    def wait(self):
        """Prevents servicing of the subsequent commands until all preceding commands have been executed and all signals have settled."""
        self.write("*WAI")

    @property
    def is_completed(self) -> bool:
        """Return bool 0 (1) in the event status register (output buffer) when all preceding commands have been executed."""
        status = self.query("*OPC?")
        return status == "0"

    def cal(self, opt):
        """
        Query the device to perform internal adjustments.

        Valid options to query:
        - MEAS: Starts all internal adjustments that do not need external measuring equipment
        - DATE: Queries the date of the most recently executed full adjustment
        - INF: Queries the current state of the internal adjustment
        - TEMP: Queries the temperature deviation compared to the calibration temperature
        - TIME: Queries the time elapsed since the last full adjustment
        - FACT:DATE: Queries the date of the last factory calibration
        """

        opts = ("MEAS", "DATE", "INF", "TEMP", "TIME", "FACT:DATE")
        if opt in opts:
            return self.query(f"CAL:ALL:{opt}?")
        else:
            raise ValueError(f"Invalid option selected, choose between {opts}.")

    def diag(self, opt):
        """
        Query the device to perform diagnosis and servicing.

        Valid options to query:
        - OTIM: Queries the operating hours of the instrument so far
        - POC: Queris how often the instrument has been turned on so far
        """

        opts = ("OTIM", "POC")
        if opt in opts:
            return self.query(f"DIAG:INFO:{opt}?")
        else:
            raise ValueError(f"Invalid option selected, choose between {opts}.")

    def set_screen_saver(self, time=10):
        """
        Sets the wait time for the screen saver mode of the display.
        """
        if time in range(1, 10, 1):
            self.write(f":DISP:PSAV:HOLD {time}")
        else:
            raise ValueError(
                f"The wait time for the screen saver mode of the display must be 1 to 60 minutes."
            )

    def screen_saver_mode(self, state: str):
        """
        Activates the screen saver mode of the display.
        """
        states = ("ON", "OFF")
        if state in states:
            self.write(f"DISP:PSAV:STAT {state}")
        else:
            raise ValueError(f"Invalid option selected, choose between {states}.")

    @property
    def f_mode(self):
        """
        Return the frequency mode for generating the RF output signal.
        """
        return str(self.query("SOUR:FREQ:MODE?"))

    @f_mode.setter
    def f_mode(self, mode):
        """
        Sets the frequency mode for generating the RF output signal. The selected mode determines the parameters to be used for further frequency settings.
        """
        allowed = ("CW", "SWEEP")
        if mode in allowed:
            self.write(f"SOUR:FREQ:MODE {mode}")
        else:
            raise ValueError(f"Invalid mode selected, choose between {allowed}.")

    @property
    def f_fixed(self):
        """
        Return the frequency of the RF output signal in the selected path.
        """
        return float(self.query("SOUR:FREQ:CW?"))

    @f_fixed.setter
    def f_fixed(self, f):
        """
        Sets the frequency of the RF output signal in the selected path.
        """
        self.write(f"SOUR:FREQ:CW {abs(f)}")

    @property
    def f_min(self):
        """
        Return the start frequency for the RF sweep.
        """
        return float(self.query("SOUR:FREQ:STAR?"))

    @f_min.setter
    def f_min(self, f: float):
        """
        Sets the start frequency for the RF sweep.
        """
        self.write(f"SOUR:FREQ:STAR {abs(f)}")

    @property
    def f_max(self):
        """
        Return the stop frequency for the RF sweep.
        """
        return float(self.query("SOUR:FREQ:STOP?"))

    @f_max.setter
    def f_max(self, f: float):
        """
        Sets the stop frequency for the RF sweep.
        """
        self.write(f"SOUR:FREQ:STOP {abs(f)}")

    @property
    def f_center(self):
        """
        Return the center frequency of the sweep.
        """
        return float(self.query("SOUR:FREQ:CENT?"))

    @f_center.setter
    def f_center(self, f: float):
        """
        Sets the center frequency of the sweep.
        """
        self.write(f"SOUR:FREQ:CENT {abs(f)}")

    @property
    def f_span(self):
        """
        Return the span of the frequency sweep range.
        """
        return float(self.query("SOUR:FREQ:SPAN?"))

    @f_span.setter
    def f_span(self, f: float):
        """
        Sets the span of the frequency sweep range.
        """
        self.write(f"SOUR:FREQ:SPAN {abs(f)}")

    @property
    def f_mult(self):
        """
        Return the multiplication factor of a subsequent downstream instrument.
        """
        return float(self.query("SOUR:FREQ:MULT?"))

    @f_mult.setter
    def f_mult(self, n):
        """
        Sets the multiplication factor of a subsequent downstream instrument.
        """
        self.write(f"SOUR:FREQ:MULT {abs(n)}")

    @property
    def f_offset(self):
        """
        Return the frequency offset of a downstream instrument.
        """
        return float(self.query("SOUR:FREQ:OFFS?"))

    @f_offset.setter
    def f_offset(self, f):
        """
        Sets the frequency offset of a downstream instrument.
        """
        self.write(f"SOUR:FREQ:OFFS {abs(f)}")

    def f_sweep(self):
        """
        Perform a one-off RF frequency sweep.
        """
        self.write("SOUR:SWE:FREQ:EXEC")

    @property
    def is_sweep_completed(self) -> bool:
        """
        Return the status of the frequency sweep is running.
        """
        status = self.query("SOUR:SWE:FREQ:RUNN?")
        return not status == "0"

    def set_phase(self, deg: float):
        """
        Sets the phase variation relative to the current phase.
        """
        if deg in range(-36000, 36000):
            self.write(f"SOUR1:PHAS {deg} DEG")
        else:
            raise ValueError(
                f"The phase variation relative to the current phase must be -36000 to 36000 degrees."
            )

    def set_phase_ref(self):
        """
        Assigns the value set as the reference phase.
        """
        self.write("SOUR:PHAS:REF")
