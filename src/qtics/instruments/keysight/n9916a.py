"""
Controller of the N9916A FieldFox Handheld Microwave Analyzer by Keysight.

.. module:: n9916a.py
.. moduleauthor:: Pietro Campana <campana.pietro@campus.unimib.it>
"""

import time
from abc import abstractmethod
from typing import Tuple

import numpy as np

from qtics.instruments.base import SCPIInstrument
from qtics.instruments.types import VNA, SpectrumAnalyzer, SweptInstrument
from qtics.instruments.utils import query_binblock, to_bool
from qtics.transport import Transport

MEAS_TIME_FACTOR = 1.02


class N9916A(SweptInstrument, SCPIInstrument):
    """N9916A FieldFox Handheld Microwave Analyzer by Keysight.

    Common part of the operational modes of the instrument. The modes are
    implemented by :class:`VNAN9916A` and :class:`SAN9916A`.
    """

    def __init__(
        self,
        transport: Transport | str,
        name: str = "",
        max_points: int = 10001,
        **transport_kwargs,
    ):
        """Initialize instrument."""
        super().__init__(transport, name, **transport_kwargs)
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
    def f_start(self) -> float:
        """Start frequency [Hz]."""
        return float(self.query("SENS:FREQ:START?"))

    @f_start.setter
    def f_start(self, f: float):
        self.write(f"SENS:FREQ:START {abs(f)}")

    @property
    def f_stop(self) -> float:
        """Stop frequency [Hz]."""
        return float(self.query("SENS:FREQ:STOP?"))

    @f_stop.setter
    def f_stop(self, f: float):
        self.write(f"SENS:FREQ:STOP {abs(f)}")

    @property
    def f_center(self) -> float:
        """Central frequency [Hz]."""
        return float(self.query("SENS:FREQ:CENT?"))

    @f_center.setter
    def f_center(self, f: float):
        self.write(f"SENS:FREQ:CENT {abs(f):5.6f}")

    @property
    def f_span(self) -> float:
        """Frequency span [Hz]."""
        return float(self.query("SENS:FREQ:SPAN?"))

    @f_span.setter
    def f_span(self, f: float):
        self.write(f"SENS:FREQ:SPAN {abs(f)}")

    @property
    def points(self) -> int:
        """Number of points in sweep."""
        return int(self.query("SENS:SWE:POIN?"))

    @points.setter
    def points(self, npoints: int):
        npoints = min(abs(npoints), self._max_points)
        self.write(f"SWE:POIN {npoints}")

    @property
    def sweep_time(self) -> float:
        """Time to complete a sweep [s]."""
        return float(self.query("SWE:TIME?"))

    @property
    def sweep_meas_time(self) -> float:
        """Time to complete a measurement sweep [s]."""
        return float(self.query("SWE:MTIME?"))

    @property
    def averages(self) -> int:
        """The number of sweep averages."""
        return int(self.query("AVER:COUN?"))

    @averages.setter
    def averages(self, n_avg: int):
        n_avg = self.validate_range(n_avg, 0, 100)
        self.write(f"SENSE:AVER:COUN {n_avg}")

    @property
    def continuous(self) -> bool:
        """Whether the instrument sweeps continuously."""
        return to_bool(self.query("INIT:CONT?"))

    @continuous.setter
    def continuous(self, status: bool):
        self.write_and_hold(f"INIT:CONT {int(status)}")

    def _trigger_sweep(self):
        """Trigger one sweep and wait until it is done (continuous mode must be off)."""
        self.write_and_hold("INIT:IMM")

    @property
    def data_format(self) -> str:
        """Get data format."""
        return self.query("FORM:DATA?")

    @data_format.setter
    def data_format(self, form: str):
        self.validate_opt(form, ("REAL,32", "REAL,64", "ASC,0"))
        self.write("FORM:DATA " + form)

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
        """Set the given parameters, sweep once and return (frequencies, trace)."""
        self.set(**kwargs)
        self.hold()
        self.sweep()
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
        for f_start in np.arange(f_win_start, f_win_end, f_win_size):
            f_temp, z_temp = self.snapshot(f_start=f_start, f_stop=f_start + f_win_size)
            f.append(f_temp[1:])
            z.append(z_temp[1:])
        return np.array(f).flatten(), np.array(z).flatten()


# N9916A comes first so that its implementations override the abstract properties
# of the type interface (averages, points, ...).
class VNAN9916A(N9916A, VNA):
    """VNA mode of the N9916A.

    The same physical instrument is driven in SA mode by :class:`SAN9916A`: connect
    only one of the two classes at a time, since each one switches the mode of the
    instrument when connecting.
    """

    _trace: int = 1

    def _after_connect(self):
        """Initialize VNA mode."""
        self.clear()
        self.reset()
        self._mode = "NA"
        self.setup()

    def setup(self, s_parameter="S21"):
        """Configure standard measurement."""
        self.write("DISP:WIND:SPL D1")
        self.s_parameter = s_parameter
        self.activate_trace()
        self.hold()
        self.set(yformat="MLOG", ifbw=1000, smoothing=0)
        self.data_format = "REAL,64"

    def autoscale(self):
        """Autoscale selected trace."""
        self.write(f"DISP:WIND:TRAC{self._trace}:Y:AUTO")

    def activate_trace(self):
        """Make active the selected trace."""
        self.write(f"CALC:PAR{self._trace}:SEL")

    @property
    def s_parameter(self) -> str:
        """The current scattering matrix parameter."""
        return self.query(f"CALC:PAR{self._trace}:DEF?")

    @s_parameter.setter
    def s_parameter(self, par="S21"):
        self.validate_opt(par, ("S11", "S21", "S12", "S22"))
        self.write(f"CALC:PAR{self._trace}:DEF {par}")

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
    def ifbw(self) -> float:
        """IF bandwidth of the receiver [Hz]."""
        return float(self.query("BWID?"))

    @ifbw.setter
    def ifbw(self, bw: float):
        self.write(f"BWID {min(abs(bw), 100_000)}")

    @property
    def power(self) -> float:
        """Output signal power [dBm]."""
        return float(self.query("SOUR:POW?"))

    @power.setter
    def power(self, pwd: float):
        pwd = max(-45, min(pwd, 3))
        self.write(f"SOUR:POW {round(pwd, 1)}")

    def read_freqs(self) -> np.ndarray:
        """Read frequencies."""
        return query_binblock(self, "FREQ:DATA?", self.data_format)

    def sweep(self):
        """Perform a sweep measurement considering averaging and average mode."""
        self.clear_average()
        self.autoscale()
        if self.continuous:
            meas_time = self.sweep_time * self.averages * MEAS_TIME_FACTOR
            time.sleep(meas_time)
            return
        if self.average_mode == "SWE":
            for _ in range(self.averages):
                self._trigger_sweep()
            return
        if self.average_mode == "POINT":
            self._trigger_sweep()
            return
        raise RuntimeError(
            f"Bad combination of average mode {self.average_mode} and number {self.averages}."
        )

    def read_trace_data(self, yformat=None) -> np.ndarray:
        """Read unformatted IQ data (complex) or formatted trace data.

        The data of the last sweep is read, call :meth:`sweep` first.
        """
        if yformat is None:
            iq = query_binblock(self, "CALC:DATA:SDATA?")
            z = np.empty(len(iq) // 2, dtype=np.complex128)
            z.real = iq[0::2]
            z.imag = iq[1::2]
            return z
        self.yformat = yformat
        return query_binblock(self, "CALC:DATA:FDATA?")


class SAN9916A(N9916A, SpectrumAnalyzer):
    """Spectrum Analyzer mode of the N9916A.

    The same physical instrument is driven in VNA mode by :class:`VNAN9916A`:
    connect only one of the two classes at a time, since each one switches the mode
    of the instrument when connecting.
    """

    _trace: int = 1

    def _after_connect(self):
        """Initialize SA mode."""
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
        return to_bool(self.query("POW:ATT:AUTO?"))

    @auto_attenuation.setter
    def auto_attenuation(self, auto: bool):
        self.write(f"POW:ATT:AUTO {int(auto)}")

    @property
    def gain(self) -> bool:
        """Automatic gain selection."""
        return to_bool(self.query("POW:GAIN:STAT?"))

    @gain.setter
    def gain(self, auto: bool):
        self.write(f"POW:GAIN:state {int(auto)}")

    @property
    def rbw(self) -> float:
        """Resolution bandwidth value [Hz]."""
        return float(self.query("BAND:RES?"))

    @rbw.setter
    def rbw(self, res: float):
        res = self.validate_range(res, 10, 2e6)
        self.write(f"BAND:RES {res}")

    @property
    def auto_rbw(self) -> bool:
        """Automatic resolution bandwidth."""
        return to_bool(self.query("BAND:RES:AUTO?"))

    @auto_rbw.setter
    def auto_rbw(self, auto: bool):
        self.write(f"BAND:RES:AUTO {int(auto)}")

    @property
    def trace_type(self) -> str:
        """Displayed trace mode."""
        return self.query(f"TRAC{self._trace}:TYPE?")

    @trace_type.setter
    def trace_type(self, opt: str):
        self.validate_opt(opt, ("CLRW", "BLAN", "MAXH", "MINH", "AVG", "VIEW"))
        self.write(f"TRAC{self._trace}:TYPE " + opt)

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
        self.write(f"AMPL:SCAL {scale}")

    def autoscale(self):
        """Autoscale all traces."""
        self.write("DISP:WIND:TRAC:Y:AUTO")

    def read_freqs(self) -> np.ndarray:
        """Compute the measured frequencies array."""
        return np.linspace(self.f_start, self.f_stop, self.points)

    def sweep(self):
        """Perform a sweep considering averaging (continuous mode waits instead)."""
        self.clear_average()
        self.autoscale()
        if self.continuous:
            meas_time = self.sweep_meas_time * self.averages * MEAS_TIME_FACTOR
            time.sleep(meas_time)
        else:
            for _ in range(self.averages):
                self._trigger_sweep()

    def read_trace_data(self, yformat=None) -> np.ndarray:
        """Read the trace of the last sweep, call :meth:`sweep` first."""
        if yformat is not None:
            self.yformat = yformat
        return query_binblock(self, f"TRAC{self._trace}:DATA?")
