"""Controller of the Tektronix DPO3014 oscilloscope (MSO3000/DPO3000 series)."""

import time
from typing import Dict, Sequence, Tuple

import numpy as np

from qtics.instruments.base import SCPIInstrument
from qtics.instruments.utils import to_bool
from qtics.transport import SocketTransport, Transport

CHANNELS = (1, 2, 3, 4)
MEASUREMENTS = (
    "AMPlitude",
    "FALL",
    "FREQuency",
    "HIGH",
    "LOW",
    "MAXimum",
    "MEAN",
    "MINImum",
    "PERIod",
    "PK2Pk",
    "RISe",
    "RMS",
)
RECORD_LENGTHS = (1000, 10000, 100000, 1000000, 5000000)
# Value returned by the instrument when a measurement fails
MEASUREMENT_ERROR = 9.9e37


def _keyword(value: str, allowed: tuple) -> str:
    """Return the entry of ``allowed`` matching ``value`` ignoring case."""
    for item in allowed:
        if str(value).upper() == item.upper():
            return item
    raise RuntimeError(f"Invalid option provided, choose between {allowed}")


class DPOChannel:
    """Analog input of a :class:`DPO3014`, obtained with :meth:`DPO3014.channel`."""

    def __init__(self, scope: "DPO3014", number: int):
        """Initialize."""
        self.scope = scope
        self.number = scope.validate_opt(number, CHANNELS)

    def _prefix(self) -> str:
        return f"CH{self.number}"

    def _query_float(self, setting: str) -> float:
        return float(self.scope.query(f"{self._prefix()}:{setting}?"))

    @property
    def enabled(self) -> bool:
        """Whether the waveform is displayed (and acquired)."""
        return to_bool(self.scope.query(f"SELect:{self._prefix()}?"))

    @enabled.setter
    def enabled(self, state: bool):
        self.scope.write(f"SELect:{self._prefix()} {int(state)}")

    @property
    def scale(self) -> float:
        """Vertical scale in V/div."""
        return self._query_float("SCAle")

    @scale.setter
    def scale(self, volts: float):
        volts = self.scope.validate_range(volts, 1e-3, 10)
        self.scope.write(f"{self._prefix()}:SCAle {volts}")

    @property
    def offset(self) -> float:
        """Vertical offset in V."""
        return self._query_float("OFFSet")

    @offset.setter
    def offset(self, volts: float):
        self.scope.write(f"{self._prefix()}:OFFSet {volts}")

    @property
    def position(self) -> float:
        """Vertical position in divisions from the center of the screen."""
        return self._query_float("POSition")

    @position.setter
    def position(self, divisions: float):
        divisions = self.scope.validate_range(divisions, -8, 8)
        self.scope.write(f"{self._prefix()}:POSition {divisions}")

    @property
    def coupling(self) -> str:
        """Input coupling: AC, DC or GND."""
        return self.scope.query(f"{self._prefix()}:COUPling?").upper()

    @coupling.setter
    def coupling(self, mode: str):
        mode = _keyword(mode, ("AC", "DC", "GND"))
        self.scope.write(f"{self._prefix()}:COUPling {mode}")

    @property
    def termination(self) -> float:
        """Input impedance in ohm: 50 or 1e6 (50 ohm is not available on all models)."""
        return self._query_float("TERmination")

    @termination.setter
    def termination(self, ohm: int):
        self.scope.validate_opt(ohm, (50, 1_000_000))
        self.scope.write(
            f"{self._prefix()}:TERmination {'FIFty' if ohm == 50 else 'MEG'}"
        )

    @property
    def bandwidth(self) -> str:
        """Bandwidth limit: TWEnty (20 MHz), ONEfifty (150 MHz) or FULl."""
        return self.scope.query(f"{self._prefix()}:BANdwidth?").upper()

    @bandwidth.setter
    def bandwidth(self, limit: str):
        limit = _keyword(limit, ("TWEnty", "ONEfifty", "FULl"))
        self.scope.write(f"{self._prefix()}:BANdwidth {limit}")


class DPO3014(SCPIInstrument):
    """Tektronix DPO3014 4-channel oscilloscope, through the socket server.

    The socket server must be enabled on the instrument (Utility > I/O > Socket
    Server, protocol None, default port 4000).
    """

    default_transport = SocketTransport
    transport_defaults = {"port": 4000, "timeout": 10}

    def __init__(
        self, transport: Transport | str, name: str = "DPO3014", **transport_kwargs
    ):
        """Initialize instrument."""
        super().__init__(transport, name, **transport_kwargs)
        self._channels: Dict[int, DPOChannel] = {}

    def _after_connect(self):
        """Switch headers off, so that queries return bare values."""
        self.write("HEADer OFF")
        self.write("VERBose ON")

    def channel(self, number: int) -> DPOChannel:
        """Analog channel 1-4."""
        number = self.validate_opt(number, CHANNELS)
        if number not in self._channels:
            self._channels[number] = DPOChannel(self, number)
        return self._channels[number]

    # ============================================================
    # Horizontal
    # ============================================================

    @property
    def horizontal_scale(self) -> float:
        """Time scale in s/div."""
        return float(self.query("HORizontal:SCAle?"))

    @horizontal_scale.setter
    def horizontal_scale(self, seconds: float):
        seconds = self.validate_range(seconds, 1e-9, 1000)
        self.write(f"HORizontal:SCAle {seconds}")

    @property
    def record_length(self) -> int:
        """Record length, one of 1000, 10000, 100000, 1000000, 5000000."""
        return int(float(self.query("HORizontal:RECOrdlength?")))

    @record_length.setter
    def record_length(self, n: int):
        self.validate_opt(n, RECORD_LENGTHS)
        self.write(f"HORizontal:RECOrdlength {n}")

    @property
    def horizontal_position(self) -> float:
        """Percentage of the record acquired before the trigger."""
        return float(self.query("HORizontal:POSition?"))

    @horizontal_position.setter
    def horizontal_position(self, percent: float):
        percent = self.validate_range(percent, 0, 100)
        self.write(f"HORizontal:POSition {percent}")

    # ============================================================
    # Trigger (A, edge)
    # ============================================================

    @property
    def trigger_source(self) -> str:
        """Edge trigger source: CH1-CH4, EXT or LINE."""
        return self.query("TRIGger:A:EDGe:SOUrce?").upper()

    @trigger_source.setter
    def trigger_source(self, source: str):
        source = _keyword(source, ("CH1", "CH2", "CH3", "CH4", "EXT", "LINE"))
        self.write(f"TRIGger:A:EDGe:SOUrce {source}")

    @property
    def trigger_level(self) -> float:
        """Trigger level in V, for the selected source."""
        return float(self.query("TRIGger:A:LEVel?"))

    @trigger_level.setter
    def trigger_level(self, volts: float):
        self.write(f"TRIGger:A:LEVel {volts}")

    @property
    def trigger_slope(self) -> str:
        """Edge trigger slope: RISE or FALL."""
        return self.query("TRIGger:A:EDGe:SLOpe?").upper()

    @trigger_slope.setter
    def trigger_slope(self, slope: str):
        slope = _keyword(slope, ("RISe", "FALL"))
        self.write(f"TRIGger:A:EDGe:SLOpe {slope}")

    @property
    def trigger_mode(self) -> str:
        """Trigger mode: AUTO or NORMAL."""
        return self.query("TRIGger:A:MODe?").upper()

    @trigger_mode.setter
    def trigger_mode(self, mode: str):
        mode = _keyword(mode, ("AUTO", "NORMal"))
        self.write(f"TRIGger:A:MODe {mode}")

    def force_trigger(self):
        """Force a trigger event."""
        self.write("TRIGger FORCe")

    # ============================================================
    # Acquisition
    # ============================================================

    @property
    def acquire_mode(self) -> str:
        """Acquisition mode: SAMPLE, PEAKDETECT, HIRES, AVERAGE or ENVELOPE."""
        return self.query("ACQuire:MODe?").upper()

    @acquire_mode.setter
    def acquire_mode(self, mode: str):
        mode = _keyword(mode, ("SAMple", "PEAKdetect", "HIRes", "AVErage", "ENVelope"))
        self.write(f"ACQuire:MODe {mode}")

    @property
    def averages(self) -> int:
        """Number of acquisitions of an averaged waveform."""
        return int(float(self.query("ACQuire:NUMAVg?")))

    @averages.setter
    def averages(self, n: int):
        n = self.validate_range(int(n), 2, 512)
        self.write(f"ACQuire:NUMAVg {n}")

    @property
    def running(self) -> bool:
        """Whether the acquisition is running."""
        return to_bool(self.query("ACQuire:STATE?"))

    def run(self):
        """Start continuous acquisitions."""
        self.write("ACQuire:STOPAfter RUNSTop")
        self.write("ACQuire:STATE ON")

    def stop(self):
        """Stop the acquisitions."""
        self.write("ACQuire:STATE OFF")

    def single(self, timeout: float = 10, poll: float = 0.05):
        """Acquire a single sequence and wait for it, stopping it on timeout.

        With the NORMAL trigger mode the acquisition waits for a trigger event.
        """
        self.write("ACQuire:STOPAfter SEQuence")
        self.write("ACQuire:STATE ON")
        deadline = time.monotonic() + timeout
        while self.running:
            if time.monotonic() > deadline:
                self.stop()
                raise TimeoutError(f"No acquisition completed within {timeout} s.")
            time.sleep(poll)

    def read_waveform(
        self, channel: int, width: int = 1
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Read the whole record of a channel, without acquiring.

        The channel must be enabled. Returns ``(time, volts)``, with ``width`` bytes
        per point (1 or 2).
        """
        channel = self.validate_opt(channel, CHANNELS)
        self.validate_opt(width, (1, 2))
        with self.transport.lock:
            self.write(f"DATa:SOUrce CH{channel}")
            self.write("DATa:ENCdg RIBinary")
            self.write(f"DATa:WIDth {width}")
            self.write("DATa:STARt 1")
            self.write(f"DATa:STOP {self.record_length}")
            ymult = float(self.query("WFMOutpre:YMUlt?"))
            yoff = float(self.query("WFMOutpre:YOFf?"))
            yzero = float(self.query("WFMOutpre:YZEro?"))
            xincr = float(self.query("WFMOutpre:XINcr?"))
            xzero = float(self.query("WFMOutpre:XZEro?"))
            pt_off = float(self.query("WFMOutpre:PT_Off?"))
            raw = self._read_curve()
        data = np.frombuffer(raw, dtype=f">i{width}")
        volts = yzero + ymult * (data - yoff)
        times = xzero + xincr * (np.arange(len(data)) - pt_off)
        return times, volts

    def _read_curve(self) -> bytes:
        """Send CURVe? and return the payload of the binary block."""
        with self.transport.lock:
            self.write("CURVe?")
            if self.read_raw(1) != b"#":
                raise ValueError("Data in buffer is not in binblock format.")
            n_digits = int(self.read_raw(1).decode())
            n_bytes = int(self.read_raw(n_digits).decode())
            payload = self.read_raw(n_bytes)
            if self.read_raw(1) != b"\n":
                raise ValueError("Data not terminated correctly.")
        return payload

    def acquire(
        self, channels: Sequence[int] = (1,), timeout: float = 10, width: int = 1
    ) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
        """Acquire a single sequence and read the channels as ``{n: (time, volts)}``."""
        for channel in channels:
            self.validate_opt(channel, CHANNELS)
        self.single(timeout)
        return {ch: self.read_waveform(ch, width) for ch in channels}

    # ============================================================
    # Measurements
    # ============================================================

    def measure(self, kind: str, channel: int = 1) -> float:
        """Immediate measurement of a channel, e.g. FREQuency, PK2Pk, MEAN, RMS.

        Returns NaN if the instrument cannot take the measurement.
        """
        kind = _keyword(kind, MEASUREMENTS)
        channel = self.validate_opt(channel, CHANNELS)
        with self.transport.lock:
            self.write(f"MEASUrement:IMMed:SOUrce1 CH{channel}")
            self.write(f"MEASUrement:IMMed:TYPe {kind}")
            value = float(self.query("MEASUrement:IMMed:VALue?"))
        return float("nan") if value >= MEASUREMENT_ERROR else value
