"""
Controller of the N9916A Vector Analyzer by Keysight.

module: NA_N9916A.py
moduleauthor: Pietro Campana <campana.pietro@campus.unimib.it>
"""
import numpy as np

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
        """Clear the error queue and all status registers."""
        self.write_and_hold("*CLS")

    def reset(self):
        """Reset the device and cancel any pending *OPC command or query."""
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

    def single_sweep(self):
        """Perform a single sweep, then hold. Use this sweep mode for reading trace data. Only works with continuous=False."""
        if self.continuous == True:
            self.continuous = False
            self.write_and_hold("INIT:IMM")
            self.continuous = True
        else:
            self.write_and_hold("INIT:IMM")

    @property
    def data_format(self):
        return self.query("FORM:DATA?")

    @data_format.setter
    def data_format(self, form: str):
        allowed = ("REAL,32", "REAL,64", "ASCII,0")
        if form not in allowed:
            raise ValueError(f"Invalid format selected, choose between {allowed}.")
        self.write("FORM:DATA " + form)

    def query_data(self, cmd, datatype="REAL,64") -> np.ndarray:
        """
        Send a command and parses response in IEEE 488.2 binary block format.

        The waveform is formatted as:
        #<x><yyy><data><newline>, where:
        <x> is the number of y bytes.
        NOTE: <x> is a hexadecimal number.
        <yyy> is the number of bytes to transfer. Care must be taken
        when selecting the data type used to interpret the data.
        The dtype argument used to read the data must match the data
        type used by the instrument that sends the data.
        <data> is the data payload in binary format.
        <newline> is a single byte new line character at the end of the data.
        """
        if datatype == "ASCII,0":
            return np.array(self.query(cmd).split(",")).astype(float)
        elif datatype == "REAL,32":
            dtype = np.float32
        elif datatype == "REAL,64":
            dtype = np.float64
        else:
            raise ValueError("Invalid data type selected.")

        self.write(cmd)

        # Read # character, raise exception if not present.
        if self.socket.recv(1) != b"#":
            raise ValueError("Data in buffer is not in binblock format.")

        # Extract header length and number of bytes in binblock.
        headerLength = int(self.socket.recv(1).decode("utf-8"), 16)
        numBytes = int(self.socket.recv(headerLength).decode("utf-8"))

        # Create a buffer object of the correct size and expose a memoryview for efficient socket reading
        rawData = bytearray(numBytes)
        buf = memoryview(rawData)

        # While there is data left to read...
        while numBytes:
            # Read data from instrument into buffer.
            bytesRecv = self.socket.recv_into(buf, numBytes)
            # Slice buffer to preserve data already written to it. This syntax seems odd, but it works correctly.
            buf = buf[bytesRecv:]
            # Subtract bytes received from total bytes.
            numBytes -= bytesRecv

        # Receive termination character.
        term = self.socket.recv(1)
        # If term char is incorrect or not present, raise exception.
        if term != b"\n":
            print("Term char: {}, rawData Length: {}".format(term, len(rawData)))
            raise ValueError("Data not terminated correctly.")

        # Convert binary data to NumPy array of specified data type and return.
        return np.frombuffer(rawData, dtype=dtype).astype(float)


class VNA9916A(N9916A):
    """VNA mode of the N9916A."""

    def __init__(
        self,
        name: str,
        address: str,
        port: int = 5025,
        timeout: int = 1000,
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
        self.set(format="MLOG", IFBW=1000, smoothing=0)

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
        self.write(f"AVER:COUN {min(n_avg, 100)}")

    def clear_average(self):
        """Reset averaging."""
        self.write("AVER:CLE")

    @property
    def IFBW(self):
        """IF bandwidth of the receiver."""
        return float(self.query("BWID?"))

    @IFBW.setter
    def IFBW(self, bw: int):
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

    def read_freqs(self):
        """Read frequencies."""
        return np.array(self.query("FREQ:DATA?").split(",")).astype(float)

    def read_IQ(self) -> np.ndarray:
        """Read unformatted IQ data."""
        self.single_sweep()
        IQ = self.query_data("CALC:DATA:SDATA?")
        len_2 = int(len(IQ) / 2)
        z = np.empty(len_2, dtype=np.complex128)
        z.real = IQ[0::2]
        z.imag = IQ[1::2]
        return z

    def read_formatted_data(self) -> np.ndarray:
        """Read formatted data."""
        self.single_sweep()
        return self.query_data("CALC:DATA:FDATA?")

    def snapshot(self, **kwargs):
        """Get frequency and IQ values for a single sweep."""
        self.set(**kwargs)
        self.clear_average()
        f = self.read_freqs()
        z = self.read_IQ()
        return f, z

    def survey(
        self, f_win_start, f_win_end, f_win_size, n_points=1600, IFBW=3000, **kwargs
    ):
        """Execute multiple scans with higher resolution."""
        f = np.array([])
        z = np.array([])
        for f_min in np.arange(f_win_start, f_win_end, f_win_size):
            f_temp, z_temp = self.snapshot(
                f_min=f_min, f_span=f_win_size, n_points=n_points, IFBW=IFBW, **kwargs
            )
            np.concatenate(f, f_temp)
            np.concatenate(z, z_temp)
        return f, z
