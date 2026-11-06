"""PicoScope 5000 Series (A API) oscilloscope driver.

Calls the C library of the PicoSDK (``libps5000a.so`` on Linux, ``ps5000a.dll`` on
Windows) through ctypes, so only the PicoSDK is needed, no Python package. The
function names, enums and status codes are those of the "PicoScope 5000 Series (A API)
Programmer's Guide" (ps5000apg.en r4) and of ``PicoStatus.h``.
"""

import ctypes
import ctypes.util
import sys
import time
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np

from qtics import log
from qtics.instruments.base import Instrument

# PICO_STATUS codes (PicoStatus.h)
PICO_OK = 0x00
PICO_INVALID_TIMEBASE = 0x0E
PICO_INVALID_SAMPLE_INTERVAL = 0x2B
PICO_POWER_SUPPLY_NOT_CONNECTED = 0x11A
PICO_USB3_0_DEVICE_NON_USB3_0_PORT = 0x11E
STATUS_NAMES = {
    0x00: "PICO_OK",
    0x01: "PICO_MAX_UNITS_OPENED",
    0x03: "PICO_NOT_FOUND",
    0x05: "PICO_OPEN_OPERATION_IN_PROGRESS",
    0x06: "PICO_OPERATION_FAILED",
    0x07: "PICO_NOT_RESPONDING",
    0x0C: "PICO_INVALID_HANDLE",
    0x0D: "PICO_INVALID_PARAMETER",
    0x0E: "PICO_INVALID_TIMEBASE",
    0x0F: "PICO_INVALID_VOLTAGE_RANGE",
    0x10: "PICO_INVALID_CHANNEL",
    0x16: "PICO_NULL_PARAMETER",
    0x1D: "PICO_TOO_MANY_SAMPLES",
    0x1E: "PICO_TOO_MANY_SEGMENTS",
    0x25: "PICO_NO_SAMPLES_AVAILABLE",
    0x26: "PICO_SEGMENT_OUT_OF_RANGE",
    0x27: "PICO_BUSY",
    0x2B: "PICO_INVALID_SAMPLE_INTERVAL",
    0x37: "PICO_INVALID_BUFFER",
    0x45: "PICO_INVALID_COUPLING",
    0x46: "PICO_BUFFERS_NOT_SET",
    0x50: "PICO_INVALID_ANALOGUE_OFFSET",
    0x11A: "PICO_POWER_SUPPLY_NOT_CONNECTED",
    0x11B: "PICO_POWER_SUPPLY_REQUEST_INVALID",
    0x11C: "PICO_POWER_SUPPLY_UNDERVOLTAGE",
    0x11E: "PICO_USB3_0_DEVICE_NON_USB3_0_PORT",
    0x11F: "PICO_NOT_SUPPORTED_BY_THIS_DEVICE",
    0x120: "PICO_INVALID_DEVICE_RESOLUTION",
    0x121: "PICO_INVALID_NUMBER_CHANNELS_FOR_RESOLUTION",
    0x122: "PICO_CHANNEL_DISABLED_DUE_TO_USB_POWERED",
    0x12F: "PICO_ARGUMENT_OUT_OF_RANGE",
    0x185: "PICO_NO_OF_CAPTURES_OUT_OF_RANGE",
}  # fmt: skip

# PS5000A_DEVICE_RESOLUTION: bits -> enum value
RESOLUTIONS = {8: 0, 12: 1, 14: 2, 15: 3, 16: 4}
# Analog channels usable at once in the resolutions limiting them
MAX_CHANNELS = {15: 2, 16: 1}
# PS5000A_CHANNEL
CHANNELS = {"A": 0, "B": 1, "C": 2, "D": 3}
# PS5000A_COUPLING
COUPLINGS = {"AC": 0, "DC": 1}
# PS5000A_RANGE: the enum value is the index in this tuple (+-V, PS5000A_10MV..20V)
RANGES = (0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0)
# PS5000A_THRESHOLD_DIRECTION
DIRECTIONS = {"ABOVE": 0, "BELOW": 1, "RISING": 2, "FALLING": 3, "RISING_OR_FALLING": 4}
RATIO_MODE_NONE = 0
# autoTrigger_ms of ps5000aSetSimpleTrigger is an int16
MAX_AUTO_TRIGGER_MS = 32767
# Timebases tried above the nearest one if it is invalid for the enabled channels
TIMEBASE_TRIES = 16
MAX_TIMEBASE = 2**32 - 1
POLL_INTERVAL = 1e-3

# Timebases per resolution, from the guide: (fastest, first of the linear ones, offset,
# rate). Timebase n is (n - offset) / rate seconds from the first linear one on, and
# 2**n ns before (8 and 12 bit only).
TIMEBASES = {
    8: (0, 3, 2, 125e6),
    12: (1, 4, 3, 62.5e6),
    14: (3, 3, 2, 125e6),
    15: (3, 3, 2, 125e6),
    16: (4, 4, 3, 62.5e6),
}

_i16, _i32, _u32, _u64 = (
    ctypes.c_int16,
    ctypes.c_int32,
    ctypes.c_uint32,
    ctypes.c_uint64,
)
_ptr = ctypes.c_void_p
# argtypes of the functions used (restype is always PICO_STATUS, a uint32)
PROTOTYPES = {
    "ps5000aOpenUnit": [_ptr, ctypes.c_char_p, _i32],
    "ps5000aCloseUnit": [_i16],
    "ps5000aStop": [_i16],
    "ps5000aChangePowerSource": [_i16, _u32],
    "ps5000aSetDeviceResolution": [_i16, _i32],
    "ps5000aMaximumValue": [_i16, _ptr],
    "ps5000aSetChannel": [_i16, _i32, _i16, _i32, _i32, ctypes.c_float],
    "ps5000aGetTimebase2": [_i16, _u32, _i32, _ptr, _ptr, _u32],
    "ps5000aSetSimpleTrigger": [_i16, _i16, _i32, _i16, _i32, _u32, _i16],
    "ps5000aSetAutoTriggerMicroSeconds": [_i16, _u64],
    "ps5000aRunBlock": [_i16, _i32, _i32, _u32, _ptr, _u32, _ptr, _ptr],
    "ps5000aIsReady": [_i16, _ptr],
    "ps5000aSetDataBuffer": [_i16, _i32, _ptr, _i32, _u32, _i32],
    "ps5000aGetValues": [_i16, _u32, _ptr, _u32, _i32, _u32, _ptr],
    "ps5000aMemorySegments": [_i16, _u32, _ptr],
    "ps5000aSetNoOfCaptures": [_i16, _u32],
    "ps5000aGetValuesBulk": [_i16, _ptr, _u32, _u32, _u32, _i32, _ptr],
}


@lru_cache(maxsize=None)
def load_library(path: str = "") -> Any:
    """Load the ps5000a library of the PicoSDK, found automatically if ``path`` is empty."""
    if sys.platform == "win32":
        names = [path] if path else [
            "ps5000a.dll",
            r"C:\Program Files\Pico Technology\SDK\lib\ps5000a.dll",
        ]  # fmt: skip
        loader: Any = ctypes.WinDLL  # type: ignore[attr-defined]
    else:
        names = [path] if path else [
            ctypes.util.find_library("ps5000a") or "",
            "libps5000a.so",
            "libps5000a.so.2",
            "/opt/picoscope/lib/libps5000a.so.2",
            "/opt/picoscope/lib/libps5000a.so",
            "libps5000a.dylib",
        ]  # fmt: skip
        loader = ctypes.CDLL
    for name in filter(None, names):
        try:
            lib = loader(name)
            break
        except OSError:
            continue
    else:
        raise OSError(
            "PicoScope 5000A library (libps5000a / ps5000a.dll) not found: install "
            "the PicoSDK (https://www.picotech.com/downloads) or pass its path as "
            "library."
        )
    for name, argtypes in PROTOTYPES.items():
        function = getattr(lib, name)
        function.argtypes = argtypes
        function.restype = ctypes.c_uint32
    return lib


class PicoError(RuntimeError):
    """Error status returned by the PicoSDK, kept in ``status``."""

    def __init__(self, message: str, status: int):
        """Initialize."""
        super().__init__(message)
        self.status = status


def _check(status: int, function: str) -> int:
    """Raise a :class:`PicoError` if ``status`` is not ``PICO_OK``, else return it."""
    if status != PICO_OK:
        name = STATUS_NAMES.get(status, f"0x{status:X}")
        raise PicoError(f"{function} failed with status {name}.", status)
    return status


def range_index(range_v: float) -> int:
    """Return the index of the smallest range (+-V) of at least ``range_v``."""
    if range_v <= 0:
        raise ValueError(f"Range must be positive, got {range_v}.")
    for index, value in enumerate(RANGES):
        if value >= range_v * (1 - 1e-9):
            return index
    raise ValueError(f"Range {range_v} V exceeds the maximum of {RANGES[-1]} V.")


def timebase_interval(timebase: int, resolution: int = 8) -> float:
    """Return the sampling interval in seconds of a timebase at a resolution."""
    fastest, first_linear, offset, rate = TIMEBASES[resolution]
    if not fastest <= timebase <= MAX_TIMEBASE:
        raise ValueError(
            f"Timebase {timebase} not available at {resolution} bit, "
            f"the fastest is {fastest}."
        )
    if timebase < first_linear:
        return 2**timebase * 1e-9
    return (timebase - offset) / rate


def nearest_timebase(interval: float, resolution: int = 8) -> int:
    """Return the timebase whose sampling interval is the closest to ``interval``."""
    if interval <= 0:
        raise ValueError(f"Sample interval must be positive, got {interval}.")
    fastest, first_linear, offset, rate = TIMEBASES[resolution]
    linear = min(max(round(interval * rate) + offset, first_linear), MAX_TIMEBASE)
    candidates = [*range(fastest, first_linear), linear]
    return min(
        candidates, key=lambda n: abs(timebase_interval(n, resolution) - interval)
    )


class PicoScope5000A(Instrument):
    """PicoScope 5000 Series oscilloscope (5000A, 5000B and 5000D, A API).

    The lab unit is a PicoScope 5444D, a 4-channel USB oscilloscope with flexible
    resolution (8 to 16 bit). The driver needs the PicoSDK C libraries (see
    :func:`load_library`). The API cannot read back the channel settings, so the
    driver keeps them (:attr:`channels`) and applies them again on connect and when
    the resolution changes.

    Captures use block mode: ``set_timebase`` and ``set_trigger`` configure the
    device, ``acquire`` and ``acquire_segments`` return the time axis and the
    voltages as numpy arrays. Nothing is opened before :meth:`connect`.
    """

    def __init__(
        self,
        serial: str = "",
        name: str = "PicoScope5000A",
        resolution: int = 8,
        library: str = "",
    ):
        """Initialize.

        ``serial`` is the serial number of the unit to open, the first unit found is
        opened if empty. ``library`` is the path of the PicoSDK library.
        """
        super().__init__(name)
        self.serial = serial
        self.library = library
        self.handle: Optional[int] = None
        self.power_source: Optional[str] = None
        self._max_adc = 0
        self._resolution = int(self.validate_opt(resolution, tuple(RESOLUTIONS)))
        self._channels: Dict[str, Dict[str, Any]] = {
            ch: {"enabled": ch == "A", "range_v": 1.0, "coupling": "DC", "offset": 0.0}
            for ch in CHANNELS
        }
        self._trigger: Optional[Dict[str, Any]] = None
        self._requested_interval: Optional[float] = None
        self._n_samples: Optional[int] = None
        self._timebase: Optional[int] = None
        self._interval: Optional[float] = None

    @property
    def lib(self) -> Any:
        """The loaded PicoSDK library."""
        return load_library(self.library)

    @property
    def is_connected(self) -> bool:
        """Whether the unit is open."""
        return self.handle is not None

    def _require_connected(self) -> int:
        if self.handle is None:
            raise ConnectionError(f"Instrument {self.name} is not connected.")
        return self.handle

    def connect(self):
        """Open the unit and apply the stored settings.

        If the unit reports that the AC adaptor is not connected (or a USB 2.0 port
        for a 2-channel 5000D), it is run on USB power: on a 4-channel unit only
        channels A and B are then available.
        """
        if self.is_connected:
            log.info(f"Instrument {self.name} already connected.")
            return
        lib = self.lib
        handle = ctypes.c_int16()
        serial = self.serial.encode() if self.serial else None
        status = lib.ps5000aOpenUnit(
            ctypes.byref(handle), serial, RESOLUTIONS[self._resolution]
        )
        if status in (
            PICO_POWER_SUPPLY_NOT_CONNECTED,
            PICO_USB3_0_DEVICE_NON_USB3_0_PORT,
        ):
            # the handle is valid, complete the two-stage power-up on USB power
            _check(
                lib.ps5000aChangePowerSource(handle.value, status),
                "ps5000aChangePowerSource",
            )
            self.power_source = "USB"
            log.warning(
                f"{self.name} runs on USB power, the 4-channel units only have "
                "channels A and B."
            )
        else:
            _check(status, "ps5000aOpenUnit")
            self.power_source = "DC"
        self.handle = handle.value
        try:
            self._apply_all()
        except BaseException:
            self.disconnect()
            raise
        log.info(f"Instrument {self.name} connected successfully.")

    def disconnect(self):
        """Stop the capture and close the unit."""
        if self.handle is None:
            log.info(f"No connection to close for instrument {self.name}.")
            return
        handle, self.handle = self.handle, None
        try:
            _check(self.lib.ps5000aStop(handle), "ps5000aStop")
        finally:
            _check(self.lib.ps5000aCloseUnit(handle), "ps5000aCloseUnit")
        log.info(f"Instrument {self.name} disconnected.")

    def _apply_all(self):
        """Write the stored settings to the unit."""
        self._read_max_adc()
        for channel in CHANNELS:
            self._apply_channel(channel)
        if self._trigger is not None:
            self._apply_trigger()
        if self._requested_interval is not None and self._n_samples is not None:
            self.set_timebase(self._requested_interval, self._n_samples)

    def _read_max_adc(self):
        """Read the maximum ADC count, which depends on the resolution."""
        value = ctypes.c_int16()
        _check(
            self.lib.ps5000aMaximumValue(
                self._require_connected(), ctypes.byref(value)
            ),
            "ps5000aMaximumValue",
        )
        self._max_adc = value.value

    @property
    def resolution(self) -> int:
        """Resolution in bits: 8, 12, 14, 15 or 16.

        At 15 bit only 2 channels can be enabled, at 16 bit only one. Changing it
        discards the captured data, and re-applies channels, trigger and timebase.
        """
        return self._resolution

    @resolution.setter
    def resolution(self, bits: int):
        bits = int(self.validate_opt(bits, tuple(RESOLUTIONS)))
        self._check_channel_count(bits, self._channels)
        if self.is_connected:
            _check(
                self.lib.ps5000aSetDeviceResolution(self.handle, RESOLUTIONS[bits]),
                "ps5000aSetDeviceResolution",
            )
        self._resolution = bits
        if self.is_connected:
            self._apply_all()

    @staticmethod
    def _check_channel_count(resolution: int, channels: Dict[str, Dict[str, Any]]):
        """Raise if more channels are enabled than the resolution allows."""
        limit = MAX_CHANNELS.get(resolution, len(CHANNELS))
        enabled = [ch for ch, cfg in channels.items() if cfg["enabled"]]
        if len(enabled) > limit:
            raise ValueError(
                f"At {resolution} bit at most {limit} channel(s) can be enabled, "
                f"not {len(enabled)} ({', '.join(enabled)})."
            )

    @property
    def channels(self) -> Dict[str, Dict[str, Any]]:
        """Copy of the settings of each channel: enabled, range_v, coupling, offset."""
        return {ch: dict(cfg) for ch, cfg in self._channels.items()}

    @staticmethod
    def _channel_name(channel: str) -> str:
        name = str(channel).upper()
        if name not in CHANNELS:
            raise ValueError(f"Invalid channel {channel!r}, choose between A, B, C, D.")
        return name

    def set_channel(
        self,
        channel: str,
        enabled: bool = True,
        range_v: float = 1.0,
        coupling: str = "DC",
        offset: float = 0.0,
    ):
        """Set up an input channel.

        ``channel`` is "A" to "D". The input range is the smallest of +-10 mV, 20
        mV, 50 mV, ..., +-20 V of at least ``range_v``. ``coupling`` is "DC" or "AC"
        (1 Mohm). ``offset`` is the voltage [V] added to the input before
        digitization, its allowed span depends on the range.
        """
        name = self._channel_name(channel)
        coupling = str(coupling).upper()
        self.validate_opt(coupling, tuple(COUPLINGS))
        index = range_index(range_v)
        new = {
            "enabled": bool(enabled),
            "range_v": RANGES[index],
            "coupling": coupling,
            "offset": float(offset),
        }
        self._check_channel_count(self._resolution, {**self._channels, name: new})
        if self.is_connected:
            self._apply_channel(name, new)
        self._channels[name] = new
        if self._trigger is not None and self._trigger["source"] == name:
            if self.is_connected:
                self._apply_trigger()

    def _apply_channel(self, channel: str, config: Optional[Dict[str, Any]] = None):
        cfg = config or self._channels[channel]
        _check(
            self.lib.ps5000aSetChannel(
                self._require_connected(),
                CHANNELS[channel],
                int(cfg["enabled"]),
                COUPLINGS[cfg["coupling"]],
                range_index(cfg["range_v"]),
                cfg["offset"],
            ),
            f"ps5000aSetChannel({channel})",
        )

    def _enabled_channels(self) -> List[str]:
        return [ch for ch, cfg in self._channels.items() if cfg["enabled"]]

    def _select_channels(self, channels: Optional[Iterable[str]]) -> List[str]:
        """Return the channels to read: the enabled ones if ``channels`` is None."""
        if channels is None:
            names = self._enabled_channels()
        else:
            names = [self._channel_name(ch) for ch in ([channels] if isinstance(channels, str) else channels)]  # fmt: skip
        if not names:
            raise ValueError("No channel enabled, use set_channel first.")
        for name in names:
            if not self._channels[name]["enabled"]:
                raise ValueError(f"Channel {name} is not enabled.")
        return names

    @property
    def timebase(self) -> Optional[int]:
        """Timebase index chosen by :meth:`set_timebase`, None if not set."""
        return self._timebase

    @property
    def sample_interval(self) -> Optional[float]:
        """Actual sampling interval in seconds, None if no timebase is set."""
        return self._interval

    @property
    def n_samples(self) -> Optional[int]:
        """Samples per capture (including the pre-trigger ones), None if not set."""
        return self._n_samples

    def _get_timebase(
        self, timebase: int, n_samples: int
    ) -> Optional[Tuple[float, int]]:
        """Return (interval [s], max samples) of a timebase, None if not valid."""
        interval = ctypes.c_float()
        max_samples = ctypes.c_int32()
        status = self.lib.ps5000aGetTimebase2(
            self._require_connected(),
            timebase,
            n_samples,
            ctypes.byref(interval),
            ctypes.byref(max_samples),
            0,
        )
        if status in (PICO_INVALID_TIMEBASE, PICO_INVALID_SAMPLE_INTERVAL):
            return None
        _check(status, "ps5000aGetTimebase2")
        return interval.value * 1e-9, max_samples.value

    def set_timebase(self, sample_interval: float, n_samples: int) -> float:
        """Choose the timebase closest to ``sample_interval`` [s] and the capture length.

        The timebase index comes from the formulas of the guide for the current
        resolution. When connected it is checked with ps5000aGetTimebase2, which
        gives the actual interval (returned, and kept in :attr:`sample_interval`);
        timebases too fast for the enabled channels are skipped for the next ones.
        The fastest intervals need few enabled channels: set the channels first.
        """
        n_samples = int(n_samples)
        if n_samples < 1:
            raise ValueError(f"Number of samples must be positive, got {n_samples}.")
        timebase = nearest_timebase(sample_interval, self._resolution)
        interval = timebase_interval(timebase, self._resolution)
        if self.is_connected:
            first = timebase
            for timebase in range(first, min(first + TIMEBASE_TRIES, MAX_TIMEBASE + 1)):
                result = self._get_timebase(timebase, n_samples)
                if result is not None:
                    break
            else:
                raise ValueError(
                    f"No valid timebase from {first} for {n_samples} samples with "
                    f"channels {', '.join(self._enabled_channels())}."
                )
            interval, max_samples = result
            if timebase != first:
                log.warning(
                    f"Timebase {first} not available with the enabled channels, "
                    f"using {timebase}."
                )
            if n_samples > max_samples:
                raise ValueError(
                    f"{n_samples} samples requested, at most {max_samples} available."
                )
        self._requested_interval = float(sample_interval)
        self._n_samples = n_samples
        self._timebase = timebase
        self._interval = interval
        return interval

    @property
    def trigger(self) -> Optional[Dict[str, Any]]:
        """Copy of the trigger settings, None if no trigger was set."""
        return None if self._trigger is None else dict(self._trigger)

    def set_trigger(
        self,
        source: str,
        level_v: float,
        direction: str = "RISING",
        delay: int = 0,
        auto_trigger_ms: int = 0,
        enabled: bool = True,
    ):
        """Set an edge or level trigger on a channel (ps5000aSetSimpleTrigger).

        ``source`` is "A" to "D" and ``level_v`` the threshold [V] of the input (the
        channel offset is accounted for), converted to ADC counts with the range of
        the channel. ``direction`` is one of ABOVE, BELOW, RISING, FALLING and
        RISING_OR_FALLING. ``delay`` is the number of sample periods between the
        trigger and the first sample. The capture starts anyway after
        ``auto_trigger_ms`` if the trigger does not fire; 0 waits forever. With
        ``enabled=False`` captures start immediately.
        """
        name = self._channel_name(source)
        direction = str(direction).upper()
        self.validate_opt(direction, tuple(DIRECTIONS))
        if enabled and not self._channels[name]["enabled"]:
            raise ValueError(f"Trigger source channel {name} is not enabled.")
        if delay < 0 or auto_trigger_ms < 0:
            raise ValueError("Delay and auto trigger time cannot be negative.")
        self._trigger = {
            "source": name,
            "level_v": float(level_v),
            "direction": direction,
            "delay": int(delay),
            "auto_trigger_ms": int(auto_trigger_ms),
            "enabled": bool(enabled),
        }
        if self.is_connected:
            self._apply_trigger()

    def _trigger_counts(self, trigger: Dict[str, Any]) -> int:
        """Convert the trigger level to ADC counts, clipped to the ADC span."""
        cfg = self._channels[trigger["source"]]
        counts = (trigger["level_v"] + cfg["offset"]) / cfg["range_v"] * self._max_adc
        return int(round(self.validate_range(counts, -self._max_adc, self._max_adc)))

    def _apply_trigger(self):
        trigger = self._trigger
        assert trigger is not None
        auto_ms = trigger["auto_trigger_ms"]
        _check(
            self.lib.ps5000aSetSimpleTrigger(
                self._require_connected(),
                int(trigger["enabled"]),
                CHANNELS[trigger["source"]],
                self._trigger_counts(trigger),
                DIRECTIONS[trigger["direction"]],
                trigger["delay"],
                min(auto_ms, MAX_AUTO_TRIGGER_MS),
            ),
            "ps5000aSetSimpleTrigger",
        )
        if auto_ms > MAX_AUTO_TRIGGER_MS:
            _check(
                self.lib.ps5000aSetAutoTriggerMicroSeconds(self.handle, auto_ms * 1000),
                "ps5000aSetAutoTriggerMicroSeconds",
            )

    def _prepare(self, pre_trigger: float) -> Tuple[int, int]:
        """Check the settings and return the pre- and post-trigger sample counts."""
        self._require_connected()
        if self._requested_interval is None or self._n_samples is None:
            raise RuntimeError("Timebase not set, call set_timebase first.")
        before = self._interval
        # enabled channels, resolution and segments change the valid timebases
        self.set_timebase(self._requested_interval, self._n_samples)
        if self._interval != before:
            log.warning(
                f"Sample interval changed from {before} s to {self._interval} s."
            )
        assert self._interval is not None
        if pre_trigger < 0:
            raise ValueError("Pre-trigger time cannot be negative.")
        n_pre = round(pre_trigger / self._interval)
        if n_pre >= self._n_samples:
            raise ValueError(
                f"Pre-trigger time {pre_trigger} s is not shorter than the capture "
                f"({self._n_samples} samples of {self._interval} s)."
            )
        return n_pre, self._n_samples - n_pre

    def _time_axis(self, n_pre: int, n_samples: int) -> np.ndarray:
        """Time of each sample [s] relative to the trigger."""
        assert self._interval is not None
        delay = (
            self._trigger["delay"] if self._trigger and self._trigger["enabled"] else 0
        )
        return (np.arange(n_samples) - n_pre + delay) * self._interval

    def _run_block(self, n_pre: int, n_post: int, timeout: float):
        """Start a block capture in segment 0 and wait until it is ready."""
        lib, handle = self.lib, self._require_connected()
        assert self._timebase is not None
        _check(
            lib.ps5000aRunBlock(
                handle, n_pre, n_post, self._timebase, None, 0, None, None
            ),
            "ps5000aRunBlock",
        )
        ready = ctypes.c_int16(0)
        deadline = time.monotonic() + timeout
        while True:
            _check(lib.ps5000aIsReady(handle, ctypes.byref(ready)), "ps5000aIsReady")
            if ready.value:
                return
            if time.monotonic() >= deadline:
                lib.ps5000aStop(handle)
                raise TimeoutError(
                    f"{self.name} did not finish the capture in {timeout} s, "
                    "check the trigger or set an auto trigger."
                )
            time.sleep(POLL_INTERVAL)

    def _to_volts(self, counts: np.ndarray, channel: str) -> np.ndarray:
        """Convert ADC counts to the input voltage: counts / max * range - offset."""
        cfg = self._channels[channel]
        return (
            counts.astype(np.float64) * (cfg["range_v"] / self._max_adc) - cfg["offset"]
        )

    @staticmethod
    def _warn_overflow(flags: int, channels: List[str], what: str = "capture"):
        for name in channels:
            if flags & (1 << CHANNELS[name]):
                log.warning(
                    f"Channel {name} overrange in the {what}, use a larger range."
                )

    def _block(
        self, channels: List[str], n_pre: int, n_post: int, timeout: float
    ) -> Dict[str, np.ndarray]:
        """Run one block capture and return the voltages of the channels."""
        lib, handle = self.lib, self._require_connected()
        self._run_block(n_pre, n_post, timeout)
        size = n_pre + n_post
        buffers = {ch: (ctypes.c_int16 * size)() for ch in channels}
        for name, buffer in buffers.items():
            _check(
                lib.ps5000aSetDataBuffer(
                    handle, CHANNELS[name], buffer, size, 0, RATIO_MODE_NONE
                ),
                f"ps5000aSetDataBuffer({name})",
            )
        count = ctypes.c_uint32(size)
        overflow = ctypes.c_int16(0)
        _check(
            lib.ps5000aGetValues(
                handle, 0, ctypes.byref(count), 1, RATIO_MODE_NONE, 0,
                ctypes.byref(overflow),
            ),
            "ps5000aGetValues",
        )  # fmt: skip
        self._warn_overflow(overflow.value, channels)
        return {
            name: self._to_volts(np.ctypeslib.as_array(buffer)[: count.value], name)
            for name, buffer in buffers.items()
        }

    def acquire(
        self,
        channels: Union[None, str, Iterable[str]] = None,
        timeout: float = 10.0,
        pre_trigger: float = 0.0,
        averages: int = 1,
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Capture a block of data and return ``(time, {channel: volts})``.

        ``channels`` are the channels to read (default: all the enabled ones).
        ``time`` is in seconds relative to the trigger and ``volts`` are the input
        voltages, ``n_samples`` samples each (see :meth:`set_timebase`), of which the
        first ``pre_trigger`` seconds are before the trigger. Raises
        :class:`TimeoutError` if the capture is not ready after ``timeout`` seconds
        (it is stopped), e.g. a trigger that never fires without auto trigger.

        With ``averages`` > 1, that many captures are run one after the other and
        their voltages averaged in software, which reduces the uncorrelated noise by
        the square root of ``averages`` when every capture has the same trigger. The
        timeout applies to each capture.
        """
        if int(averages) < 1:
            raise ValueError(f"Averages must be at least 1, got {averages}.")
        names = self._select_channels(channels)
        n_pre, n_post = self._prepare(pre_trigger)
        total = {name: np.zeros(n_pre + n_post) for name in names}
        for _ in range(int(averages)):
            for name, volts in self._block(names, n_pre, n_post, timeout).items():
                total[name] = total[name] + volts
        data = {name: volts / int(averages) for name, volts in total.items()}
        return self._time_axis(n_pre, len(data[names[0]])), data

    def acquire_segments(
        self,
        n_captures: int,
        channels: Union[None, str, Iterable[str]] = None,
        timeout: float = 10.0,
        pre_trigger: float = 0.0,
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Capture ``n_captures`` waveforms in rapid block mode.

        The scope memory is divided in ``n_captures`` segments, filled one trigger
        after the other with a minimum dead time between them. Returns
        ``(time, {channel: volts})`` where ``volts`` has shape ``(n_captures,
        n_samples)``; the arguments are those of :meth:`acquire`. The timeout applies
        to the whole run. The memory is merged again afterwards. For an average
        use ``volts.mean(axis=0)``.
        """
        n_captures = int(n_captures)
        if n_captures < 1:
            raise ValueError(
                f"Number of captures must be at least 1, got {n_captures}."
            )
        lib, handle = self.lib, self._require_connected()
        names = self._select_channels(channels)
        n_pre, n_post = self._prepare(pre_trigger)
        size = n_pre + n_post
        max_samples = ctypes.c_int32()
        _check(
            lib.ps5000aMemorySegments(handle, n_captures, ctypes.byref(max_samples)),
            "ps5000aMemorySegments",
        )
        try:
            _check(
                lib.ps5000aSetNoOfCaptures(handle, n_captures), "ps5000aSetNoOfCaptures"
            )
            assert self._timebase is not None
            result = self._get_timebase(self._timebase, size)
            if result is None or result[1] < size:
                available = 0 if result is None else result[1]
                raise ValueError(
                    f"{n_captures} segments of {size} samples do not fit in the "
                    f"memory, at most {available} samples per segment."
                )
            data = self._read_segments(names, n_captures, n_pre, n_post, timeout)
        finally:
            self._merge_segments()
        return self._time_axis(n_pre, size), data

    def _read_segments(
        self,
        channels: List[str],
        n_captures: int,
        n_pre: int,
        n_post: int,
        timeout: float,
    ) -> Dict[str, np.ndarray]:
        lib, handle = self.lib, self._require_connected()
        size = n_pre + n_post
        self._run_block(n_pre, n_post, timeout)
        buffers = {
            ch: [(ctypes.c_int16 * size)() for _ in range(n_captures)]
            for ch in channels
        }
        for name, segments in buffers.items():
            for index, buffer in enumerate(segments):
                _check(
                    lib.ps5000aSetDataBuffer(
                        handle, CHANNELS[name], buffer, size, index, RATIO_MODE_NONE
                    ),
                    f"ps5000aSetDataBuffer({name}, segment {index})",
                )
        count = ctypes.c_uint32(size)
        overflow = (ctypes.c_int16 * n_captures)()
        _check(
            lib.ps5000aGetValuesBulk(
                handle, ctypes.byref(count), 0, n_captures - 1, 1, RATIO_MODE_NONE,
                overflow,
            ),
            "ps5000aGetValuesBulk",
        )  # fmt: skip
        for index, flags in enumerate(overflow):
            self._warn_overflow(flags, channels, f"segment {index}")
        return {
            name: np.stack(
                [
                    self._to_volts(np.ctypeslib.as_array(buffer)[: count.value], name)
                    for buffer in segments
                ]
            )
            for name, segments in buffers.items()
        }

    def _merge_segments(self):
        """Go back to a single memory segment and capture."""
        lib, handle = self.lib, self._require_connected()
        _check(
            lib.ps5000aMemorySegments(handle, 1, ctypes.byref(ctypes.c_int32())),
            "ps5000aMemorySegments",
        )
        _check(lib.ps5000aSetNoOfCaptures(handle, 1), "ps5000aSetNoOfCaptures")
