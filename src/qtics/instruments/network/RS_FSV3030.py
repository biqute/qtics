"""Controller of the R&S FSV3030 Spectrum Analyzer."""

import numpy as np

from qtics.instruments import NetworkInst

from .utils import query_data


class FSV3030(NetworkInst):
    """R&S FSV3030 Spectrum Analyzer by Rohde & Schwarz."""

    def clear(self):
        """Clear the error queue and status registers."""
        self.write("*CLS")

    def wait(self):
        """Wait until all commands are processed."""
        self.write("*WAI")

    @property
    def is_completed(self) -> bool:
        """Query if last operation is complete."""
        return self.query("*OPC?") == "1"

    # ============================================================
    # Frequency control
    # ============================================================

    @property
    def f_center(self) -> float:
        """Center frequency in Hz."""
        return float(self.query("FREQ:CENT?"))

    @f_center.setter
    def f_center(self, f: float):
        f = self.validate_range(f, 9e3, 30e9)  # FSV3030: 9 kHz – 30 GHz
        self.write(f"FREQ:CENT {f}")

    @property
    def f_span(self) -> float:
        """Frequency span in Hz."""
        return float(self.query("FREQ:SPAN?"))

    @f_span.setter
    def f_span(self, f: float):
        f = self.validate_range(f, 0, 30e9)
        self.write(f"FREQ:SPAN {f}")

    @property
    def f_start(self) -> float:
        """Start frequency in Hz."""
        return float(self.query("FREQ:STAR?"))

    @f_start.setter
    def f_start(self, f: float):
        f = self.validate_range(f, 9e3, 30e9)
        self.write(f"FREQ:STAR {f}")

    @property
    def f_stop(self) -> float:
        """Stop frequency in Hz."""
        return float(self.query("FREQ:STOP?"))

    @f_stop.setter
    def f_stop(self, f: float):
        f = self.validate_range(f, 9e3, 30e9)
        self.write(f"FREQ:STOP {f}")

    # ============================================================
    # Bandwidth and detector
    # ============================================================

    @property
    def rbw(self) -> float:
        """Resolution bandwidth (Hz)."""
        return float(self.query("BAND:RES?"))

    @rbw.setter
    def rbw(self, bw: float):
        bw = self.validate_range(bw, 1, 10e6)
        self.write(f"BAND:RES {bw}")

    @property
    def vbw(self) -> float:
        """Video bandwidth (Hz)."""
        return float(self.query("BAND:VID?"))

    @vbw.setter
    def vbw(self, bw: float):
        bw = self.validate_range(bw, 1, 10e6)
        self.write(f"BAND:VID {bw}")

    @property
    def detector(self) -> str:
        """Detector type."""
        return self.query("DET:FUNC?")

    @detector.setter
    def detector(self, mode: str = "POS"):
        """Set detector mode (POS, NEG, AVER, SAMP, RMS, etc.)."""
        self.validate_opt(mode, ("POS", "NEG", "AVER", "SAMP", "RMS"))
        self.write(f"DET:FUNC {mode}")

    # ============================================================
    # Sweep and trace settings
    # ============================================================

    @property
    def sweep_points(self) -> int:
        """Number of sweep points."""
        return int(self.query("SWE:POIN?"))

    @sweep_points.setter
    def sweep_points(self, n: int):
        n = self.validate_range(n, 101, 10001)
        self.write(f"SWE:POIN {n}")

    @property
    def sweep_time(self) -> float:
        """Sweep time in seconds."""
        return float(self.query("SWE:TIME?"))

    @sweep_time.setter
    def sweep_time(self, t: float):
        t = self.validate_range(t, 1e-3, 1000)
        self.write(f"SWE:TIME {t}")

    def single_sweep(self):
        """Trigger a single sweep and wait until completion."""
        self.write("INIT:CONT OFF")
        self.write("INIT:IMM")
        self.wait()

    def continuous(self, state: bool = True):
        """Set continuous sweep mode."""
        self.write(f"INIT:CONT {int(state)}")

    # ============================================================
    # Trace and measurement
    # ============================================================

    def autoscale(self):
        """Autoscale display (adjust reference level and range)."""
        self.write("DISP:WIND:TRAC:Y:AUTO")

    @property
    def ref_level(self) -> float:
        """Reference level in dBm."""
        return float(self.query("DISP:WIND:TRAC:Y:SCAL:RLEV?"))

    @ref_level.setter
    def ref_level(self, level: float):
        self.write(f"DISP:WIND:TRAC:Y:SCAL:RLEV {level}")

    def read_trace_data(self, trace: int = 1) -> np.ndarray:
        """Read trace data (in dBm) as a numpy array."""
        self.single_sweep()
        data = query_data(self, f"TRAC? TRACE{trace}")
        return data

    def read_freqs(self) -> np.ndarray:
        """Return frequency axis corresponding to current span."""
        start = self.f_start
        stop = self.f_stop
        points = self.sweep_points
        return np.linspace(start, stop, points)

    def snapshot(self, trace: int = 1) -> tuple[np.ndarray, np.ndarray]:
        """Perform single sweep and return (freqs, trace)."""
        self.single_sweep()
        freqs = self.read_freqs()
        trace = self.read_trace_data(trace)
        return freqs, trace

    # ============================================================
    # Marker control
    # ============================================================

    def marker_to_peak(self, marker: int = 1):
        """Move marker to maximum peak."""
        self.write(f"CALC:MARK{marker}:MAX")

    def marker_freq(self, marker: int = 1) -> float:
        """Query marker frequency."""
        return float(self.query(f"CALC:MARK{marker}:X?"))

    def marker_power(self, marker: int = 1) -> float:
        """Query marker power in dBm."""
        return float(self.query(f"CALC:MARK{marker}:Y?"))
