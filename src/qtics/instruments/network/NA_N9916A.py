"""
Controller of the N9916A Vector Analyzer by Keysight.

.. module:: NA_N9916A.py
.. moduleauthor:: Pietro Campana <campana.pietro@campus.unimib.it>

The code for query_data() was partially taken from https://github.com/morgan-at-keysight/socketscpi
"""

import time
from abc import ABC, abstractmethod
from typing import Tuple

import numpy as np

from qtics import log
from qtics.instruments import NetworkInst

MEAS_TIME_FACTOR = 1.02


class N9916A(NetworkInst, ABC):
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
        """Initialize instrument."""
        super().__init__(name, address, port, timeout, sleep, no_delay)
        self._max_points = max_points

    def write_and_hold(self, cmd: str):
        """Write command and wait until it has been processed."""
        self.write(cmd)
        self.hold()

    def clear(self):
        """Clear the error queue and all status registers."""
        self.write_and_hold("*CLS")

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
    def sweep_meas_time(self) -> float:
        """Time to complete a measurement sweep."""
        return float(self.query("SWE:MTIME?"))

    @property
    def average(self) -> int:
        """The number of sweep averages."""
        return int(self.query("AVER:COUN?"))

    @average.setter
    def average(self, n_avg: int):
        n_avg = self.validate_range(n_avg, 0, 100)
        self.write(f"SENSE:AVER:COUN {n_avg}")

    @property
    def continuous(self) -> bool:
        """Acquisition mode."""
        return self.query("INIT:CONT?") != "0"

    @continuous.setter
    def continuous(self, status: bool):
        self.write_and_hold(f"INIT:CONT {int(status)}")

    def single_sweep(self):
        """Perform a single sweep, then hold. Use this sweep mode for reading trace data."""
        if self.continuous:
            log.warning("Setting continuous=False to perform single sweep triggering.")
            self.continuous = False
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
        map_types = {"REAL,32": np.float32, "REAL,64": np.float64}
        if datatype not in map_types:
            raise ValueError("Invalid data type selected.")

        self.write(cmd)

        # Read # character, raise exception if not present.
        if self.socket is None:
            raise RuntimeError("Socket not initialized.")

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

        return np.frombuffer(raw_data, dtype=map_types[datatype]).astype(float)

    @abstractmethod
    def clear_average(self):
        """Reset averaging."""

    @abstractmethod
    def autoscale(self):
        """Autoscale selected trace."""

    @abstractmethod
    def read_trace_data(self, yformat=None):
        """Read trace data from the instrument."""

    @abstractmethod
    def read_freqs(self):
        """Read trace frequencies from the instrument."""

    def snapshot(self, yformat=None, **kwargs) -> Tuple[np.ndarray, np.ndarray]:
        """Get frequency and trace values for a single sweep."""
        self.set(**kwargs)
        self.hold()
        z = self.read_trace_data(yformat=yformat)
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


class VNAN9916A(N9916A):
    """VNA mode of the N9916A."""

    __trace: int = 1

    def connect(self):
        """Connect to the device and initialize VNA mode."""
        super().connect()
        self.clear()
        self.reset()
        self._mode = "NA"
        self.setup()

    def setup(self, par="S21"):
        """Configure standard measurement."""
        self.write("DISP:WIND:SPL D1")
        self.s_par = par
        self.activate_trace()
        self.hold()
        self.set(yformat="MLOG", IFBW=1000, smoothing=0)
        self.data_format = "REAL,64"

    def autoscale(self):
        """Autoscale selected trace."""
        self.write(f"DISP:WIND:TRAC{self.__trace}:Y:AUTO")

    def activate_trace(self):
        """Make active the selected trace."""
        self.write(f"CALC:PAR{self.__trace}:SEL")

    @property
    def s_par(self) -> str:
        """The current scattering matrix parameter."""
        return self.query(f"CALC:PAR{self.__trace}:DEF?")

    @s_par.setter
    def s_par(self, par="S21"):
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
        self.clear_average()
        self.autoscale()
        if self.continuous:
            meas_time = self.sweep_time * self.average * MEAS_TIME_FACTOR
            time.sleep(meas_time)
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

    def read_trace_data(self, yformat=None) -> np.ndarray:
        """Read unformatted IQ data or formatted trace data."""
        if yformat is None:
            self.sweep()
            IQ = self.query_data("CALC:DATA:SDATA?")
            len_2 = int(len(IQ) / 2)
            z = np.empty(len_2, dtype=np.complex128)
            z.real = IQ[0::2]
            z.imag = IQ[1::2]
            return z
        self.yformat = yformat
        self.sweep()
        return self.query_data("CALC:DATA:FDATA?")


class SAN9916A(N9916A):
    """Spectrum Analyzer mode of the N9916A."""

    __trace: int = 1

    def connect(self):
        """Connect to the device and setup SA mode."""
        super().connect()
        self.clear()
        self.reset()
        self._mode = "SA"
        self.continuous = False
        self.trace_type = "AVG"
        self.data_format = "REAL,64"

    def set_full_span(self):
        """Set the frequency span to the entire span of the FieldFox."""
        self.write("FREQ:SPAN:FULL")

    def set_zero_span(self):
        """Set the frequency span to 0 Hz around the center frequency."""
        self.write("FREQ:SPAN:ZERO")

    @property
    def attenuation(self) -> float:
        """RF attenuation value."""
        return float(self.query("POW:ATT?"))

    @attenuation.setter
    def attenuation(self, att: float):
        att = self.validate_range(att, 0, 100)
        self.write(f"POW:ATT {att}")

    @property
    def auto_attenuation(self) -> bool:
        """Automatic RF attenuation."""
        return self.query("POW:ATT:AUTO?") == "ON"

    @auto_attenuation.setter
    def auto_attenuation(self, auto: bool):
        self.write(f"POW:GAIN:STAT {int(auto)}")

    @property
    def gain(self) -> bool:
        """Automatic gain selection."""
        return self.query("POW:GAIN:STAT?") == "ON"

    @gain.setter
    def gain(self, auto: bool):
        self.write(f"POW:GAIN:state {int(auto)}")

    @property
    def res_bandwidth(self) -> float:
        """Resolution bandwidth value."""
        return float(self.query("BAND:RES?"))

    @res_bandwidth.setter
    def res_bandwidth(self, res: float):
        res = self.validate_range(res, 10, 2e6)
        self.write(f"BAND:RES {res}")

    @property
    def auto_res_bandwidth(self) -> bool:
        """Automatic resolution bandwidth."""
        return self.query("BAND:RES:AUTO?") == "ON"

    @auto_res_bandwidth.setter
    def auto_res_bandwidth(self, auto: bool):
        self.write(f"BAND:RES:AUTO {int(auto)}")

    @property
    def trace_type(self) -> str:
        """Displayed trace mode."""
        return self.query(f"TRAC{self.__trace}:TYPE?")

    @trace_type.setter
    def trace_type(self, opt: str):
        self.validate_opt(opt, ("CLRW", "BLAN", "MAXH", "MINH", "AVG", "VIEW"))
        self.write(f"TRAC{self.__trace}:TYPE " + opt)

    @property
    def average_type(self) -> str:
        """The average type (sweeping or point by point)."""
        return self.query("AVER:TYPE?")

    @average_type.setter
    def average_type(self, mode: str):
        self.validate_opt(mode, ("AUTO", "POW", "POWer", "LOG", "VOLT"))
        self.write(f"AVER:TYPE {mode}")

    def clear_average(self):
        """Restart averaging from 1."""
        self.write_and_hold("INIT:REST")

    @property
    def yformat(self) -> str:
        """Measurement unit of the data amplitude."""
        return self.query("AMPL:UNIT?")

    @yformat.setter
    def yformat(self, data_format="DBM"):
        units = (
            "W",  # watts
            "DBM",  # dBm
            "DBMV",  # dB milliVolts
            "DBUV",  # dB microvolts
            "DBMA",  # dB milliAmps
            "DBUA",  # dB microAmps
            "V",  # volts
            "A",  # amps
        )
        self.validate_opt(data_format, units)
        self.write(f"AMPL:UNIT {data_format}")

    @property
    def yscale(self) -> str:
        """Scale of the amplitude axis."""
        return self.query("AMPL:SCAL?")

    @yscale.setter
    def yscale(self, scale: str):
        self.validate_opt(scale, ("LOG", "LIN"))
        self.write(f"AMPL:SCAL: {scale}")

    def autoscale(self):
        """Autoscale all traces."""
        self.write("DISP:WIND:TRAC:Y:AUTO")

    def read_freqs(self) -> np.ndarray:
        """Compute the measured frequencies array."""
        return np.linspace(self.f_min, self.f_max, self.sweep_points)

    def read_trace_data(self, yformat=None) -> np.ndarray:
        """Read the current data trace values considering averaging."""
        if yformat is not None:
            self.yformat = yformat
        self.clear_average()
        self.autoscale()
        if self.continuous:
            meas_time = self.sweep_meas_time * self.average * MEAS_TIME_FACTOR
            time.sleep(meas_time)
        else:
            for _ in range(self.average):
                self.single_sweep()
        return self.query_data(f"TRAC{self.__trace}:DATA?")
