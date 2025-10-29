"""
Controller of the R&S ZNB Vector Network Analyzer.

.. module:: RS_ZNB.py
.. moduleauthor:: Pietro Campana <p.campana1@campus.unimib.it>
"""

import time
from typing import Tuple

import numpy as np

from qtics import log
from qtics.instruments import NetworkInst

from .utils import query_data

MEAS_TIME_FACTOR = 1.02


class RSZNB(NetworkInst):
    """R&S ZNB Vector Network Analyzer by Rohde & Schwarz."""

    def __init__(
        self,
        name: str,
        address: str,
        port: int = 5025,
        timeout: int = 8000,
        sleep: float = 0.1,
        no_delay: bool = True,
        max_points: int = 100001,
        channel: int = 1,
    ):
        """Initialize instrument."""
        super().__init__(name, address, port, timeout, sleep, no_delay)
        self._max_points = max_points
        self._channel = channel
        self._active_trace = "Trc1"

    def connect(self):
        """Connect to the device and initialize VNA mode."""
        super().connect()
        self.clear()
        self.reset()
        self.setup()

    def setup(self, s_par="S21"):
        """Configure standard measurement."""
        # Create default trace if it doesn't exist
        self.write(
            f"CALCulate{self._channel}:PARameter:SDEFine '{self._active_trace}', '{s_par}'"
        )
        self.write(f"DISPlay:WINDow1:TRACe1:FEED '{self._active_trace}'")
        self.s_par = s_par
        self.activate_trace()
        self.hold()
        self.set(yformat="MLOG", IFBW=1000, smoothing=0, average=1)
        self.data_format = "REAL,64"

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

    def activate_trace(self):
        """Make active the selected trace."""
        self.write(f"CALCulate{self._channel}:PARameter:SELect '{self._active_trace}'")

    @property
    def f_min(self) -> float:
        """Minimum frequency."""
        return float(self.query(f"SENSe{self._channel}:FREQuency:STARt?"))

    @f_min.setter
    def f_min(self, f: float):
        self.write(f"SENSe{self._channel}:FREQuency:STARt {abs(f)}")

    @property
    def f_max(self) -> float:
        """Maximum frequency."""
        return float(self.query(f"SENSe{self._channel}:FREQuency:STOP?"))

    @f_max.setter
    def f_max(self, f: float):
        self.write(f"SENSe{self._channel}:FREQuency:STOP {abs(f)}")

    @property
    def f_center(self) -> float:
        """Central frequency."""
        return (self.f_min + self.f_max) / 2

    @f_center.setter
    def f_center(self, f: float):
        span = self.f_span
        self.f_min = f - span / 2
        self.f_max = f + span / 2

    @property
    def f_span(self) -> float:
        """Frequency span."""
        return self.f_max - self.f_min

    @f_span.setter
    def f_span(self, f: float):
        """Frequency span."""
        center = self.f_center
        self.f_min = center - abs(f) / 2
        self.f_max = center + abs(f) / 2

    @property
    def sweep_points(self) -> int:
        """Number of points in sweep."""
        return int(self.query(f"SENSe{self._channel}:SWEep:POINts?"))

    @sweep_points.setter
    def sweep_points(self, npoints):
        npoints = min(abs(npoints), self._max_points)
        self.write(f"SENSe{self._channel}:SWEep:POINts {npoints}")

    @property
    def sweep_time(self) -> float:
        """Time to complete a measurement sweep."""
        return float(self.query(f"SENSe{self._channel}:SWEep:TIME?"))

    @property
    def sweep_meas_time(self) -> float:
        """Time to complete a measurement sweep (same as sweep_time for R&S ZNB)."""
        return self.sweep_time

    @property
    def average(self) -> int:
        """The number of sweep averages."""
        return int(self.query(f"SENSe{self._channel}:AVERage:COUNt?"))

    @average.setter
    def average(self, n_avg: int):
        n_avg = self.validate_range(n_avg, 1, 65536)
        self.write(f"SENSe{self._channel}:AVERage:COUNt {n_avg}")
        if n_avg > 1:
            self.write(f"SENSe{self._channel}:AVERage:STATe ON")
        else:
            self.write(f"SENSe{self._channel}:AVERage:STATe OFF")

    @property
    def continuous(self) -> bool:
        """Acquisition mode."""
        return self.query(f"INITiate{self._channel}:CONTinuous?") != "0"

    @continuous.setter
    def continuous(self, status: bool):
        self.write_and_hold(f"INITiate{self._channel}:CONTinuous {int(status)}")

    def single_sweep(self):
        """Perform a single sweep, then hold. Use this sweep mode for reading trace data."""
        if self.continuous:
            log.warning("Setting continuous=False to perform single sweep triggering.")
            self.continuous = False
        self.write_and_hold(f"INITiate{self._channel}:IMMediate")

    @property
    def data_format(self) -> str:
        """Get data format."""
        return self.query("FORMat:DATA?")

    @data_format.setter
    def data_format(self, form: str):
        self.validate_opt(form, ("REAL,32", "REAL,64", "ASC,0"))
        self.write("FORMat:DATA " + form)

    @property
    def s_par(self) -> str:
        """The current scattering matrix parameter."""
        return self.query(
            f"CALCulate{self._channel}:PARameter:DEFine? '{self._active_trace}'"
        )

    @s_par.setter
    def s_par(self, par="S21"):
        # Common S-parameters for ZNB
        valid_spars = (
            "S11",
            "S21",
            "S12",
            "S22",
            "S31",
            "S32",
            "S33",
            "S41",
            "S42",
            "S43",
            "S44",
        )
        if not any(par.upper().startswith(sp) for sp in valid_spars):
            log.warning(f"S-parameter {par} may not be supported. Continuing anyway.")
        self.write(
            f"CALCulate{self._channel}:PARameter:MEASure '{self._active_trace}', '{par}'"
        )

    @property
    def yformat(self) -> str:
        """Scale and format of data."""
        return self.query(f"CALCulate{self._channel}:FORMat?")

    @yformat.setter
    def yformat(self, data_format="MLOG"):
        valid_formats = (
            "MLOG",
            "MLIN",
            "REAL",
            "IMAG",
            "UPHase",
            "PHASe",
            "POLar",
            "SMITh",
            "SWR",
        )
        if data_format.upper() not in [fmt.upper() for fmt in valid_formats]:
            log.warning(
                f"Format {data_format} may not be supported. Continuing anyway."
            )
        self.write(f"CALCulate{self._channel}:FORMat {data_format}")

    @property
    def smoothing(self) -> int:
        """Number of points in smoothing window."""
        status = self.query(f"CALCulate{self._channel}:SMOothing:STATe?")
        if status == "1":
            aperture = int(self.query(f"CALCulate{self._channel}:SMOothing:APERture?"))
            return aperture
        return 0

    @smoothing.setter
    def smoothing(self, aperture: int):
        if aperture > 0:
            self.write(f"CALCulate{self._channel}:SMOothing:STATe ON")
            self.write(f"CALCulate{self._channel}:SMOothing:APERture {abs(aperture)}")
        else:
            self.write(f"CALCulate{self._channel}:SMOothing:STATe OFF")

    def clear_average(self):
        """Reset averaging."""
        self.write(f"SENSe{self._channel}:AVERage:CLEar")

    @property
    def IFBW(self) -> float:
        """IF bandwidth of the receiver."""
        return float(self.query(f"SENSe{self._channel}:BANDwidth:RESolution?"))

    @IFBW.setter
    def IFBW(self, bw: int):
        # R&S ZNB typically supports 1 Hz to 5 MHz
        bw = self.validate_range(bw, 1, 5_000_000)
        self.write(f"SENSe{self._channel}:BANDwidth:RESolution {bw}")

    @property
    def power(self) -> float:
        """Output signal power."""
        return float(
            self.query(f"SOURce{self._channel}:POWer:LEVel:IMMediate:AMPLitude?")
        )

    @power.setter
    def power(self, pwd: float):
        # R&S ZNB typically supports -45 to +13 dBm
        pwd = self.validate_range(pwd, -45, 13)
        self.write(
            f"SOURce{self._channel}:POWer:LEVel:IMMediate:AMPLitude {round(pwd, 1)}"
        )

    def autoscale(self):
        """Autoscale selected trace."""
        self.write(f"DISPlay:WINDow1:TRACe1:Y:SCALe:AUTO ONCE")

    def read_freqs(self) -> np.ndarray:
        """Read frequencies."""
        return np.linspace(self.f_min, self.f_max, self.sweep_points)

    def sweep(self):
        """Perform a frequency sweep measurement considering averaging and sweep mode."""
        if self.average > 1:
            self.clear_average()

        self.autoscale()

        if self.continuous:
            meas_time = self.sweep_time * self.average * MEAS_TIME_FACTOR
            time.sleep(meas_time)
        else:
            if self.average > 1:
                for _ in range(self.average):
                    self.write_and_hold(f"INITiate{self._channel}:IMMediate")
            else:
                self.write_and_hold(f"INITiate{self._channel}:IMMediate")

    def read_trace_data(self, yformat=None) -> np.ndarray:
        """Read unformatted IQ data or formatted trace data."""
        if yformat is None:
            # Read complex S-parameter data
            self.sweep()
            self.activate_trace()
            IQ = query_data(self, f"CALCulate{self._channel}:DATA? SDATa")
            len_2 = int(len(IQ) / 2)
            z = np.empty(len_2, dtype=np.complex128)
            z.real = IQ[0::2]
            z.imag = IQ[1::2]
            return z
        else:
            # Read formatted data
            self.yformat = yformat
            self.sweep()
            self.activate_trace()
            return query_data(self, f"CALCulate{self._channel}:DATA? FDATa")

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

    # Calibration methods
    def start_calibration(self, cal_type="TOSM", ports=None):
        """Start a calibration procedure.

        Args:
            cal_type: Calibration type ("TOSM", "SOLT", "FOPORT", etc.)
            ports: List of ports to calibrate (e.g., [1, 2])
        """
        if ports is None:
            ports = [1, 2]

        port_str = ", ".join(map(str, ports))
        cal_name = f"Cal_{cal_type}_{port_str.replace(', ', '_')}"

        self.write(
            f"SENSe{self._channel}:CORRection:COLLect:METHod:DEFine '{cal_name}', {cal_type}, {port_str}"
        )
        log.info(f"Started {cal_type} calibration on ports {ports}")

    def measure_standard(self, standard, port=None):
        """Measure a calibration standard.

        Args:
            standard: Standard type ("OPEN", "SHORT", "LOAD", "THROUGH")
            port: Port number for single-port standards
        """
        if port is not None:
            self.write(
                f"SENSe{self._channel}:CORRection:COLLect:ACQuire:SELected {standard}, {port}"
            )
        else:
            self.write(
                f"SENSe{self._channel}:CORRection:COLLect:ACQuire:SELected {standard}"
            )
        log.info(f"Measured {standard} standard" + (f" on port {port}" if port else ""))

    def apply_calibration(self):
        """Apply the calibration."""
        self.write(f"SENSe{self._channel}:CORRection:COLLect:SAVE:SELected")
        log.info("Calibration applied successfully")

    # Trace management
    def create_trace(self, trace_name: str, s_parameter: str):
        """Create a new trace with specified S-parameter."""
        self.write(
            f"CALCulate{self._channel}:PARameter:SDEFine '{trace_name}', '{s_parameter}'"
        )
        self._active_trace = trace_name
        log.info(f"Created trace '{trace_name}' for {s_parameter}")

    def select_trace(self, trace_name: str):
        """Select active trace."""
        self.write(f"CALCulate{self._channel}:PARameter:SELect '{trace_name}'")
        self._active_trace = trace_name

    def delete_trace(self, trace_name: str):
        """Delete a trace."""
        self.write(f"CALCulate{self._channel}:PARameter:DELete '{trace_name}'")
        if self._active_trace == trace_name:
            self._active_trace = "Trc1"

    def list_traces(self):
        """List all traces in the current channel."""
        response = self.query(f"CALCulate{self._channel}:PARameter:CATalog?")
        # Response format: 'TraceName,S-Parameter,TraceName,S-Parameter,...'
        if response.strip():
            traces = response.split(",")
            return [(traces[i], traces[i + 1]) for i in range(0, len(traces), 2)]
        return []
