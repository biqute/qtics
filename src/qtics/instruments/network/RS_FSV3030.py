"""Controller of the R&S FSV3030 Spectrum Analyzer."""

import numpy as np

from qtics.instruments import NetworkInst

from .utils import query_data


class FSV3030(NetworkInst):
    """R&S FSV3030 Spectrum Analyzer by Rohde & Schwarz.

    Instantiate with a timeout long enough to cover the longest expected sweep.
    The default NetworkInst timeout of 10 s is too short for slow sweeps (narrow
    RBW, many points, or trace averaging). 60 s is a safer starting point::

        spectrum = FSV3030("spectrum", "192.168.1.x", timeout=60)

    Call ``setup()`` after connecting to put the instrument in a known state
    before any measurement.
    """

    def clear(self):
        """Clear the error queue and status registers."""
        self.write("*CLS")

    def wait(self):
        """Block until all pending instrument operations are complete.

        Implemented via *OPC? (query form): the instrument returns '1' only
        when all preceding commands have finished, so the Python socket read
        blocks until that moment.  The socket timeout must exceed the longest
        expected operation duration.
        """
        result = self.query("*OPC?")
        if result != "1":
            raise RuntimeError(f"*OPC? returned unexpected response: {result!r}")

    @property
    def is_completed(self) -> bool:
        """Query if last operation is complete."""
        return self.query("*OPC?") == "1"

    # ============================================================
    # Initialisation
    # ============================================================

    def setup(self):
        """Put the instrument in a defined state for automated measurements.

        Should be called once after connecting, before any measurement loop.
        Sets single-sweep mode (the correct mode for all remote-controlled
        acquisitions), clears status registers, and resets trace 1 to normal
        write mode.
        """
        self.clear()  # clear error queue and status
        self.write("INIT:CONT OFF")  # single-sweep mode
        self.write("TRAC1:MODE WRIT")  # normal write mode (no max-hold)

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
    def detector(self, mode: str):
        """Set detector mode (POS, NEG, AVER, SAMP, RMS, etc.)."""
        self.validate_opt(mode, ("POS", "NEG", "AVER", "SAMP", "RMS"))
        self.write(f"DET:FUNC {mode}")

    # ============================================================
    # Sweep and trace settings
    # ============================================================

    @property
    def sweep_points(self) -> int:
        """Number of sweep points."""
        return int(self.query("SWE:POIN?"))  # codespell:ignore

    @sweep_points.setter
    def sweep_points(self, n: int):
        n = self.validate_range(n, 101, 100001)
        self.write(f"SWE:POIN {n}")  # codespell:ignore

    @property
    def sweep_time(self) -> float:
        """Sweep time in seconds."""
        return float(self.query("SWE:TIME?"))

    @sweep_time.setter
    def sweep_time(self, t: float):
        t = self.validate_range(t, 1e-3, 1000)
        self.write(f"SWE:TIME {t}")

    @property
    def average(self) -> int:
        """Trace average count (1 means averaging disabled).

        Setting this to n >= 2 enables trace averaging with count n.
        Setting it to 1 disables averaging.
        """
        return int(self.query("AVER:COUN?"))

    @average.setter
    def average(self, n: int):
        n = self.validate_range(n, 1, 32768)
        if n > 1:
            self.write(f"AVER:COUN {n}")
            self.write("AVER:STAT ON")
        else:
            self.write("AVER:STAT OFF")

    def single_sweep(self):
        """Trigger a single sweep and block until it completes.

        Requires that the instrument is already in single-sweep mode
        (INIT:CONT OFF), which ``setup()`` ensures.  Synchronisation is
        performed via ``*OPC?``: the socket read blocks until the instrument
        confirms completion, making the sweep duration the effective timeout
        (see class docstring on setting an appropriate socket timeout).
        """
        self.write("INIT:IMM")
        self.wait()

    def continuous(self, state: bool = True):
        """Set continuous sweep mode on or off."""
        self.write(f"INIT:CONT {int(state)}")

    # ============================================================
    # Trace and measurement
    # ============================================================

    def autoscale(self):
        """Autoscale display once (adjusts reference level and range)."""
        self.write("DISP:WIND:TRAC:Y:SCAL:AUTO ONCE")

    @property
    def ref_level(self) -> float:
        """Reference level in dBm."""
        return float(self.query("DISP:WIND:TRAC:Y:SCAL:RLEV?"))

    @ref_level.setter
    def ref_level(self, level: float):
        self.write(f"DISP:WIND:TRAC:Y:SCAL:RLEV {level}")

    def _read_trace_raw(self, trace: int = 1) -> np.ndarray:
        """Read the current trace buffer without triggering a new sweep.

        Internal method.  Assumes a completed sweep is already in the buffer.
        """
        return query_data(self, f"TRAC? TRACE{trace}", datatype="ASC,0")

    def read_trace_data(self, trace: int = 1) -> np.ndarray:
        """Trigger a single sweep and return the trace data (dBm)."""
        self.single_sweep()
        return self._read_trace_raw(trace)

    def read_freqs(self) -> np.ndarray:
        """Return the frequency axis corresponding to the current span."""
        start = self.f_start
        stop = self.f_stop
        points = self.sweep_points
        return np.linspace(start, stop, points)

    def snapshot(self, trace: int = 1) -> tuple[np.ndarray, np.ndarray]:
        """Trigger a single sweep and return (freqs, trace_data).

        Performs exactly one sweep.  The frequency axis is reconstructed from
        the instrument's start/stop/points settings; the trace data is read
        from the completed sweep buffer.
        """
        n = self.average
        old_timeout = self.timeout
        time_sweep = self.sweep_time
        self.socket.settimeout(max(time_sweep * n * 2, old_timeout))
        self.write("AVER:CLE")
        self.single_sweep()  # blocks via *OPC? until all SWE:COUN sweeps done
        self.socket.settimeout(old_timeout)
        freqs = self.read_freqs()
        trace_data = self._read_trace_raw(trace)
        return freqs, trace_data

    # ============================================================
    # Marker control
    # ============================================================

    def marker_to_peak(self, marker: int = 1):
        """Move marker to maximum peak."""
        self.write(f"CALC:MARK{marker}:MAX")

    def marker_freq(self, marker: int = 1) -> float:
        """Query marker frequency in Hz."""
        return float(self.query(f"CALC:MARK{marker}:X?"))

    def marker_power(self, marker: int = 1) -> float:
        """Query marker power in dBm."""
        return float(self.query(f"CALC:MARK{marker}:Y?"))

    # ============================================================
    # Preamplifier (requires optional preamplifier hardware)
    # ============================================================

    @property
    def preamp_enabled(self) -> bool:
        """Return True if the internal preamplifier is active.

        Requires the optional preamplifier hardware to be installed.
        """
        return self.query("INP:GAIN:STAT?") in ("1", "ON")

    @preamp_enabled.setter
    def preamp_enabled(self, state: bool):
        """Enable or disable the internal preamplifier.

        Parameters
        ----------
        state:
            ``True`` to enable, ``False`` to disable.
        """
        self.write(f"INP:GAIN:STAT {'ON' if state else 'OFF'}")

    @property
    def preamp_gain(self) -> float:
        """Preamplifier gain in dB (15 or 30).

        The instrument only accepts 15 dB and 30 dB; any other value is
        rounded by the firmware to the nearest of those two.  Reading this
        property is only meaningful when the preamplifier is enabled
        (``preamp_enabled`` is ``True``).
        """
        return float(self.query("INP:GAIN:VAL?"))

    @preamp_gain.setter
    def preamp_gain(self, gain: float):
        """Set the preamplifier gain.

        Parameters
        ----------
        gain:
            Gain in dB.  Must be 15 or 30; other values are rejected to
            avoid silent rounding by the firmware.

        Raises
        ------
        ValueError
            If *gain* is not 15 or 30.
        """
        if gain not in (15, 30):
            raise ValueError(f"Preamplifier gain must be 15 or 30 dB, got {gain!r}.")
        self.write(f"INP:GAIN:VAL {gain}")

    def set_preamp(self, gain_db: float):
        """Enable the preamplifier and set its gain in a single call.

        Convenience wrapper that first enables the preamplifier and then
        sets the desired gain.  Equivalent to::

            inst.preamp_enabled = True
            inst.preamp_gain = gain_db

        Parameters
        ----------
        gain_db:
            Gain in dB — must be 15 or 30.
        """
        self.preamp_enabled = True
        self.preamp_gain = gain_db

    # ============================================================
    # Max-hold acquisition
    # ============================================================

    def set_max_hold(self, trace: int = 1):
        """Switch a trace to max-hold mode.

        After calling this, drive sweeps manually with ``single_sweep()``
        for as many acquisitions as needed, then call ``_read_trace_raw()``
        or ``snapshot()`` to retrieve the accumulated result.  Use
        ``clear_max_hold()`` to reset and return to normal write mode.
        """
        self.write(f"TRAC{trace}:MODE MAXH")

    def clear_max_hold(self, trace: int = 1):
        """Reset a max-hold trace and return it to normal write mode."""
        self.write(f"TRAC{trace}:MODE WRIT")

    def read_max_hold(self, trace: int = 1, n_sweeps: int = 1) -> np.ndarray:
        """Accumulate max-hold over ``n_sweeps`` sweeps and return the trace.

        Sets the trace to max-hold mode, triggers ``n_sweeps`` sweeps to
        build the envelope, reads the result, then resets the trace to normal
        write mode.

        Parameters
        ----------
        trace:
            Trace number (default 1).
        n_sweeps:
            Number of sweeps to accumulate before reading.  A value of 1
            is equivalent to a normal sweep; use larger values when the
            signal of interest is intermittent or you want a worst-case
            envelope.
        """
        n_sweeps = max(1, int(n_sweeps))
        self.set_max_hold(trace)
        for _ in range(n_sweeps):
            self.single_sweep()
        data = self._read_trace_raw(trace)
        self.clear_max_hold(trace)
        return data
