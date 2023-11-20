from qinst.network_inst import NetworkInst


class N9916A(NetworkInst):
    """N9916A FieldFox Handheld Microwave Analyzer by Keysight."""

    def __init__(
        self,
        name: str,
        address: str,
        port: int = 5025,
        timeout: int = 8000,
        sleep: float = 0.1,
        no_delay: bool = True,
        max_points: int = 10001,
    ):
        super().__init__(name, address, port, timeout, sleep, no_delay)
        self._max_points = max_points

    def write_and_hold(self, cmd: str):
        """Write command and wait until it has been processed."""
        self.write(cmd)
        self.hold()

    def clear(self):
        self.write_and_hold("*CLS")

    def reset(self):
        self.write_and_hold("*RST")

    def hold(self):
        """Wait until all commands have been processed."""
        complete = self.query("*OPC?")
        if complete != "1":
            raise ValueError(
                f"Operation completed query returned value {complete} instead of 1."
            )

    @property
    def _mode(self):
        return self.query("INST:SEL?")

    @_mode.setter
    def _mode(self, mode: str):
        allowed = ("SA", "NA", "CAT")
        if mode in allowed:
            return self.write_and_hold(f'INST:SEL "{mode}"')
        else:
            raise ValueError(f"Invalid mode selected, choose between {allowed}.")

    @property
    def f_min(self):
        """Minimum frequency."""
        return float(self.query("SENS:FREQ:START?"))

    @f_min.setter
    def f_min(self, f: float):
        self.write(f"FREQ:START {abs(f)}")

    @property
    def f_max(self):
        """Maximum frequency."""
        return float(self.query("SENS:FREQ:STOP?"))

    @f_max.setter
    def f_max(self, f: float):
        self.write(f"FREQ:STOP {abs(f)}")

    @property
    def f_center(self):
        """Central frequency."""
        return float(self.query("SENS:FREQ:CENT?"))

    @f_center.setter
    def f_center(self, f: float):
        self.write(f"SENS:FREQ:CENT {abs(f):5.6f}")

    @property
    def f_span(self):
        """Frequency span."""
        return float(self.query("FREQ:SPAN?"))

    @property
    def sweep_points(self):
        """Number of points in sweep."""
        return int(self.query("SENS:SWE:POIN?"))

    @sweep_points.setter
    def sweep_points(self, npoints):
        npoints = min(abs(npoints), self._max_points)
        self.write(f"SWE:POIN {npoints}")

    @property
    def continuous(self):
        """Acquisition mode."""
        return self.query("INIT:CONT?")

    @continuous.setter
    def continuous(self, status: bool):
        self.write_and_hold(f"INIT:CONT {int(status)}")


class VNA9916A(N9916A):
    def __init__(
        self,
        name: str,
        address: str,
        port: int = 5025,
        timeout: int = 10,
        sleep: float = 0.1,
        no_delay=True,
        max_points=100000,
    ):
        super().__init__(name, address, port, timeout, sleep, no_delay, max_points)
        self.connect()
        self.clear()
        self.reset()
        self._mode = "NA"
        self.__trace = 1
        self.setup()

    def setup(self, par="S21"):
        """Configure standard measurement."""
        self.write("DISP:WIND:SPL D1")
        self.S_par = par
        self.activate_trace()
        self.hold()
        self.set(format="MLOG", bandwidth=1000, smoothing=0)

    def activate_trace(self):
        """Make active the selected trace."""
        self.write(f"CALC:PAR{self.__trace}:SEL")

    @property
    def S_par(self):
        """The current scattering matrix parameter."""
        return self.query(f"CALC:PAR{self.__trace}:DEF?")

    @S_par.setter
    def S_par(self, par="S21"):
        allowed = ("S11", "S21", "S12", "S22")
        if par in allowed:
            self.write(f"CALC:PAR{self.__trace}:DEF{par}")
        else:
            raise ValueError(f"Invalid mode selected, choose between {allowed}.")

    @property
    def format(self):
        """Scale and format of data."""
        return self.query("CALC:FORM?")

    @format.setter
    def format(self, data_format="MLOG"):
        allowed = ("MLOG", "MLIN", "REAL", "IMAG", "ZMAG")
        if data_format in allowed:
            self.write(f"CALC:FORM {data_format}")
        else:
            raise ValueError(f"Invalid mode selected, choose between {allowed}.")

    @property
    def smoothing(self):
        """Number of point in smoothing window."""
        status = int(self.query("CALC:SMO?"))
        if status:
            aperture = int(self.query("CALC:SMO:APER?"))
            return aperture
        else:
            return 0

    @smoothing.setter
    def smoothing(self, aperture: int):
        if aperture > 0:
            self.query("CALC:SMO 1")
            self.write(f"CALC:SMO:APER {min(abs(aperture), 25)}")
        else:
            self.write("CALC:SMO 0")

    @property
    def average(self):
        """The number of sweep averages."""
        return int(self.query("AVER:COUN?"))

    @average.setter
    def average(self, n_avg: int):
        if n_avg <= 0:
            self.write("AVER:CLE")

        self.write(f"AVER:COUN {min(n_avg, 100)}")

    @property
    def bandwidth(self):
        """IF bandwidth of the receiver."""
        return float(self.query("BWID?"))

    @bandwidth.setter
    def bandwidth(self, bw: int):
        allowed = (10, 30, 100, 300, 1000, 10000, 30000, 100000)
        self.write(f"BWID {min(allowed, key=lambda x: abs(x - bw))}")

    @property
    def power(self):
        """Output signal power."""
        return float(self.query("SOUR:POW?"))

    @power.setter
    def power(self, pwd: float):
        pwd = max(-45, min(pwd, 3))
        self.write(f"SOUR:POW {round(pwd, 1)}")
