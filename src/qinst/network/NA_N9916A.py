"""
Controller of the N9916A Vector Analyzer by Keysight.

..module:: NA_N9916A.py
..moduleauthor:: Pietro Campana <campana.pietro@campus.unimib.it>
The code for query_data() was partially taken from https://github.com/morgan-at-keysight/socketscpi
"""
import time
from typing import Tuple

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
        """Initialize."""
        if type(self) == N9916A:
            raise RuntimeError(
                "You cannot instantiate directly N9916A: use a subclass."
            )
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
    def _mode(self) -> str:
        return self.query("INST:SEL?")

    @_mode.setter
    def _mode(self, mode: str):
        self.validate_opt(mode, ("SA", "NA", "CAT"))
        self.write_and_hold(f'INST:SEL "{mode}"')

    @property
    def f_min(self) -> float:
        """Minimum frequency."""
        return float(self.query("SENS:FREQ:START?"))

    @f_min.setter
    def f_min(self, f: float):
        self.write(f"SENS:FREQ:START {abs(f)}")

    @property
    def f_max(self) -> float:
        """Maximum frequency."""
        return float(self.query("SENS:FREQ:STOP?"))

    @f_max.setter
    def f_max(self, f: float):
        self.write(f"SENS:FREQ:STOP {abs(f)}")

    @property
    def f_center(self) -> float:
        """Central frequency."""
        return float(self.query("SENS:FREQ:CENT?"))

    @f_center.setter
    def f_center(self, f: float):
        self.write(f"SENS:FREQ:CENT {abs(f):5.6f}")

    @property
    def f_span(self) -> float:
        """Frequency span."""
        return float(self.query("SENS:FREQ:SPAN?"))

    @f_span.setter
    def f_span(self, f: float):
        """Frequency span."""
        return self.write(f"SENS:FREQ:SPAN {abs(f)}")

    @property
    def sweep_points(self) -> int:
        """Number of points in sweep."""
        return int(self.query("SENS:SWE:POIN?"))

    @sweep_points.setter
    def sweep_points(self, npoints):
        npoints = min(abs(npoints), self._max_points)
        self.write(f"SWE:POIN {npoints}")

    @property
    def sweep_time(self) -> float:
        """Time to complete a measurement sweep."""
        return float(self.query("SWE:TIME?"))

    @property
    def continuous(self) -> bool:
        """Acquisition mode."""
        return self.query("INIT:CONT?") != "0"

    @continuous.setter
    def continuous(self, status: bool):
        self.write_and_hold(f"INIT:CONT {int(status)}")

    def single_sweep(self):
        """
        Perform a single sweep, then hold. Use this sweep mode for reading trace data.

        Triggering single sweeps is only possible with continuous=False.
        """
        if self.continuous == True:
            self.continuous = False
            self.write_and_hold("INIT:IMM")
            self.continuous = True
        else:
            self.write_and_hold("INIT:IMM")

    @property
    def data_format(self) -> str:
        """Get data format."""
        return self.query("FORM:DATA?")

    @data_format.setter
    def data_format(self, form: str):
        self.validate_opt(form, ("REAL,32", "REAL,64", "ASC,0"))
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
        self.data_format = datatype

        if datatype == "ASC,0":
            return np.array(self.query(cmd).split(",")).astype(float)
        if datatype == "REAL,32":
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
        header_length = int(self.socket.recv(1).decode("utf-8"), 16)
        n_bytes = int(self.socket.recv(header_length).decode("utf-8"))

        # Create a buffer and expose a memoryview for efficient socket reading
        raw_data = bytearray(n_bytes)
        buf = memoryview(raw_data)

        while n_bytes:
            # Read data from instrument into buffer.
            bytes_recv = self.socket.recv_into(buf, n_bytes)
            # Slice buffer to preserve data already written to it.
            buf = buf[bytes_recv:]
            # Subtract bytes received from total bytes.
            n_bytes -= bytes_recv

        # Receive termination character.
        term = self.socket.recv(1)
        if term != b"\n":
            raise ValueError("Data not terminated correctly.")

        return np.frombuffer(raw_data, dtype=dtype).astype(float)


class VNAN9916A(N9916A):
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
        """Initialize super instrument and setup VNA mode."""
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
        self.set(yformat="MLOG", IFBW=1000, smoothing=0)
        self.data_format = "REAL,64"

    def autoscale(self):
        """Autoscale all."""
        self.write(f"DISP:WIND:TRAC{self.__trace}:Y:AUTO")

    def activate_trace(self):
        """Make active the selected trace."""
        self.write(f"CALC:PAR{self.__trace}:SEL")

    @property
    def S_par(self) -> str:
        """The current scattering matrix parameter."""
        return self.query(f"CALC:PAR{self.__trace}:DEF?")

    @S_par.setter
    def S_par(self, par="S21"):
        self.validate_opt(par, ("S11", "S21", "S12", "S22"))
        self.write(f"CALC:PAR{self.__trace}:DEF {par}")

    @property
    def yformat(self) -> str:
        """Scale and format of data."""
        return self.query("CALC:FORM?")

    @yformat.setter
    def yformat(self, data_format="MLOG"):
        self.validate_opt(data_format, ("MLOG", "MLIN", "REAL", "IMAG", "ZMAG"))
        self.write(f"CALC:FORM {data_format}")

    @property
    def smoothing(self) -> int:
        """Number of point in smoothing window."""
        status = int(self.query("CALC:SMO?"))
        if status:
            aperture = int(self.query("CALC:SMO:APER?"))
            return aperture
        return 0

    @smoothing.setter
    def smoothing(self, aperture: int):
        if aperture > 0:
            self.write("CALC:SMO 1")
            self.write(f"CALC:SMO:APER {abs(aperture)}")
        else:
            self.write("CALC:SMO 0")

    @property
    def average(self) -> int:
        """The number of sweep averages."""
        return int(self.query("AVER:COUN?"))

    @average.setter
    def average(self, n_avg: int):
        self.write(f"SENSE:AVER:COUN {min(n_avg, 100)}")

    @property
    def average_mode(self) -> str:
        """The average mode (sweeping or point by point)."""
        return self.query("AVER:MODE?")

    @average_mode.setter
    def average_mode(self, mode: str):
        self.validate_opt(mode, ("SWE", "POINT"))
        self.write(f"AVER:MODE {mode}")

    def clear_average(self):
        """Reset averaging."""
        self.write("AVER:CLE")

    @property
    def IFBW(self) -> float:
        """IF bandwidth of the receiver."""
        return float(self.query("BWID?"))

    @IFBW.setter
    def IFBW(self, bw: int):
        self.write(f"BWID {min(abs(bw), 100_000)}")

    @property
    def power(self) -> float:
        """Output signal power."""
        return float(self.query("SOUR:POW?"))

    @power.setter
    def power(self, pwd: float):
        pwd = max(-45, min(pwd, 3))
        self.write(f"SOUR:POW {round(pwd, 1)}")

    def read_freqs(self) -> np.ndarray:
        """Read frequencies."""
        return self.query_data("FREQ:DATA?", self.data_format)

    def sweep(self):
        """Perform a frequency sweep measurement considering averaging and sweep mode."""
        if self.continuous:
            meas_time = self.sweep_time * self.average * 1.02
            self.clear_average()
            time.sleep.wait(meas_time)
            return
        if self.average_mode == "SWE":
            for _ in range(self.average):
                self.write_and_hold("INIT:IMM")
            return
        if self.average_mode == "POINT":
            self.write_and_hold("INIT:IMM")
            return
        raise RuntimeError(
            f"Bad combination of average mode {self.average_mode} and number {self.average}."
        )

    def read_IQ(self) -> np.ndarray:
        """Read unformatted IQ data."""
        self.sweep()
        IQ = self.query_data("CALC:DATA:SDATA?")
        len_2 = int(len(IQ) / 2)
        z = np.empty(len_2, dtype=np.complex128)
        z.real = IQ[0::2]
        z.imag = IQ[1::2]
        return z

    def read_formatted_data(self) -> np.ndarray:
        """Read formatted data."""
        self.sweep()
        return self.query_data("CALC:DATA:FDATA?")

    def snapshot(self, **kwargs) -> Tuple[np.ndarray, np.ndarray]:
        """Get frequency and IQ values for a single sweep."""
        self.set(**kwargs)
        self.clear_average()
        self.hold()
        self.autoscale()
        z = self.read_IQ()
        f = self.read_freqs()
        self.hold()
        return f, z

    def survey(
        self, f_win_start, f_win_end, f_win_size, **kwargs
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Execute multiple scans with higher resolution."""
        f = []
        z = []
        self.set(**kwargs)
        for f_min in np.arange(f_win_start, f_win_end, f_win_size):
            f_temp, z_temp = self.snapshot(f_min=f_min, f_max=f_min + f_win_size)
            f.append(f_temp[1:])
            z.append(z_temp[1:])
        return np.array(f).flatten(), np.array(z).flatten()
