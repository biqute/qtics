"""Test the PicoScope 5000A driver against a stand-in PicoSDK library."""

import ctypes
import sys

import numpy as np
import pytest

from qtics.instruments.pico import ps5000a
from qtics.instruments.pico.ps5000a import PicoError, PicoScope5000A

OK = 0
BUSY = 0x27
NOT_FOUND = 0x03
INVALID_TIMEBASE = 0x0E
NO_PSU = ps5000a.PICO_POWER_SUPPLY_NOT_CONNECTED
NON_USB3 = ps5000a.PICO_USB3_0_DEVICE_NON_USB3_0_PORT
BITS = {value: bits for bits, value in ps5000a.RESOLUTIONS.items()}


class FakeLib:
    """Mimics the used functions of libps5000a, recording the calls."""

    def __init__(self):
        """Initialize."""
        self.calls = []
        self.status = {}  # function name -> status returned instead of PICO_OK
        self.open_status = OK
        self.resolution = 8
        self.min_timebase = 0
        self.max_total = 1_000_000  # samples shared by the segments
        self.segments = 1
        self.ready_after = 0  # polls answering "not ready" first, None: never ready
        self.polls = 0
        self.runs = 0
        self.data = {}  # channel index -> ADC counts
        self.drift = 0  # counts added for each run after the first
        self.overflow = 0
        self.buffers = {}

    def _call(self, name, *args):
        self.calls.append((name, args))
        return self.status.get(name, OK)

    def names(self):
        """Names of the functions called, in order."""
        return [name for name, _ in self.calls]

    def args(self, name):
        """Arguments of each call of a function."""
        return [args for called, args in self.calls if called == name]

    def ps5000aOpenUnit(
        self, handle, serial, resolution
    ):  # pylint: disable=invalid-name
        """Open a unit."""
        status = self._call("ps5000aOpenUnit", serial, resolution)
        handle._obj.value = 7
        self.resolution = BITS[resolution]
        return status or self.open_status

    def ps5000aCloseUnit(self, handle):  # pylint: disable=invalid-name
        """Close the unit."""
        return self._call("ps5000aCloseUnit", handle)

    def ps5000aStop(self, handle):  # pylint: disable=invalid-name
        """Stop the capture."""
        return self._call("ps5000aStop", handle)

    def ps5000aChangePowerSource(self, handle, state):  # pylint: disable=invalid-name
        """Change the power source."""
        return self._call("ps5000aChangePowerSource", handle, state)

    def ps5000aSetDeviceResolution(
        self, handle, resolution
    ):  # pylint: disable=invalid-name
        """Set the resolution."""
        self.resolution = BITS[resolution]
        return self._call("ps5000aSetDeviceResolution", handle, resolution)

    def ps5000aMaximumValue(self, handle, value):  # pylint: disable=invalid-name
        """Maximum ADC count."""
        value._obj.value = 32512 if self.resolution == 8 else 32767
        return self._call("ps5000aMaximumValue", handle)

    def ps5000aSetChannel(self, *args):  # pylint: disable=invalid-name
        """Set up a channel."""
        return self._call("ps5000aSetChannel", *args)

    def ps5000aGetTimebase2(  # pylint: disable=invalid-name
        self, handle, timebase, n_samples, interval, max_samples, segment
    ):
        """Interval in ns and maximum samples of a timebase."""
        self._call("ps5000aGetTimebase2", timebase, n_samples)
        if timebase < self.min_timebase:
            return INVALID_TIMEBASE
        interval._obj.value = ps5000a.timebase_interval(timebase, self.resolution) * 1e9
        max_samples._obj.value = self.max_total // self.segments
        return self.status.get("ps5000aGetTimebase2", OK)

    def ps5000aSetSimpleTrigger(self, *args):  # pylint: disable=invalid-name
        """Set a trigger."""
        return self._call("ps5000aSetSimpleTrigger", *args)

    def ps5000aSetAutoTriggerMicroSeconds(self, *args):  # pylint: disable=invalid-name
        """Set the auto trigger time."""
        return self._call("ps5000aSetAutoTriggerMicroSeconds", *args)

    def ps5000aRunBlock(  # pylint: disable=invalid-name
        self, handle, n_pre, n_post, timebase, time_ms, segment, callback, parameter
    ):
        """Start a capture."""
        self.runs += 1
        self.polls = 0
        self.buffers = {}
        return self._call("ps5000aRunBlock", n_pre, n_post, timebase, segment)

    def ps5000aIsReady(self, handle, ready):  # pylint: disable=invalid-name
        """Poll the capture."""
        self.polls += 1
        ready._obj.value = int(
            self.ready_after is not None and self.polls > self.ready_after
        )
        return self._call("ps5000aIsReady")

    def ps5000aSetDataBuffer(  # pylint: disable=invalid-name
        self, handle, channel, buffer, size, segment, mode
    ):
        """Register a buffer."""
        self.buffers[(channel, segment)] = (buffer, size)
        return self._call("ps5000aSetDataBuffer", channel, size, segment, mode)

    def _fill(self, segment, offset):
        for (channel, index), (buffer, size) in self.buffers.items():
            if index == segment:
                counts = self.data[channel][:size] + offset
                ctypes.memmove(buffer, counts.astype(np.int16).tobytes(), 2 * size)

    def ps5000aGetValues(  # pylint: disable=invalid-name
        self, handle, start, count, ratio, mode, segment, overflow
    ):
        """Copy the data of the segment in the registered buffers."""
        self._fill(segment, self.drift * (self.runs - 1))
        overflow._obj.value = self.overflow
        return self._call("ps5000aGetValues", start, count._obj.value, segment)

    def ps5000aMemorySegments(
        self, handle, n_segments, max_samples
    ):  # pylint: disable=invalid-name
        """Divide the memory."""
        self.segments = n_segments
        max_samples._obj.value = self.max_total // n_segments
        return self._call("ps5000aMemorySegments", n_segments)

    def ps5000aSetNoOfCaptures(
        self, handle, n_captures
    ):  # pylint: disable=invalid-name
        """Set the number of captures of the run."""
        return self._call("ps5000aSetNoOfCaptures", n_captures)

    def ps5000aGetValuesBulk(  # pylint: disable=invalid-name
        self, handle, count, first, last, ratio, mode, overflow
    ):
        """Copy the segments in the registered buffers, segment i is shifted by i."""
        for segment in range(first, last + 1):
            self._fill(segment, segment)
            overflow[segment - first] = self.overflow
        return self._call("ps5000aGetValuesBulk", count._obj.value, first, last)


@pytest.fixture
def lib(monkeypatch):
    """Replace the library loader with a fake, which is never the real PicoSDK."""
    fake = FakeLib()
    fake.data = {
        0: np.array([0, 16256, -32512, 32512, 8128, 0, 0, 0]),
        1: np.array([100, 200, 300, 400, 500, 600, 700, 800]),
    }
    monkeypatch.setattr(ps5000a, "load_library", lambda path="": fake)
    return fake


@pytest.fixture
def scope(lib):
    """Connected oscilloscope, channels A and B at +-1 V, 4 samples of 1 us."""
    inst = PicoScope5000A()
    inst.connect()
    inst.set_channel("B")
    inst.set_timebase(1e-6, 4)
    lib.calls.clear()
    yield inst
    inst.disconnect()


def test_connect_disconnect(lib):
    """Open with the serial and resolution, apply the channels, close on exit."""
    inst = PicoScope5000A(serial="AB123/456", resolution=12)
    assert not inst.is_connected
    with inst:
        assert inst.is_connected
        assert inst.handle == 7
        assert inst.power_source == "DC"
    assert not inst.is_connected
    assert lib.args("ps5000aOpenUnit") == [(b"AB123/456", 1)]
    assert len(lib.args("ps5000aSetChannel")) == 4
    assert lib.names()[-2:] == ["ps5000aStop", "ps5000aCloseUnit"]
    assert lib.args("ps5000aCloseUnit") == [(7,)]
    inst.disconnect()  # nothing to close
    assert lib.names().count("ps5000aCloseUnit") == 1


def test_open_first_unit(lib):
    """Without serial the first unit is opened."""
    PicoScope5000A().connect()
    assert lib.args("ps5000aOpenUnit") == [(None, 0)]


@pytest.mark.parametrize("status", [NO_PSU, NON_USB3])
def test_power_source_status(lib, status):
    """The status of OpenUnit is passed to ChangePowerSource to run on USB power."""
    lib.open_status = status
    inst = PicoScope5000A()
    inst.connect()
    assert lib.args("ps5000aChangePowerSource") == [(7, status)]
    assert inst.power_source == "USB"
    assert inst.is_connected


def test_open_failure(lib):
    """A failing OpenUnit raises with the status name and leaves it closed."""
    lib.open_status = NOT_FOUND
    inst = PicoScope5000A()
    with pytest.raises(RuntimeError, match="PICO_NOT_FOUND"):
        inst.connect()
    assert not inst.is_connected
    assert "ps5000aCloseUnit" not in lib.names()


def test_setup_failure_closes(lib):
    """If applying the settings fails the unit is closed again."""
    lib.status["ps5000aSetChannel"] = 0x10
    inst = PicoScope5000A()
    with pytest.raises(PicoError, match="PICO_INVALID_CHANNEL") as info:
        inst.connect()
    assert info.value.status == 0x10
    assert not inst.is_connected
    assert "ps5000aCloseUnit" in lib.names()


def test_status_names():
    """Known codes are named, the others shown in hexadecimal."""
    assert ps5000a._check(OK, "f") == OK
    with pytest.raises(RuntimeError, match="PICO_BUSY"):
        ps5000a._check(BUSY, "f")
    with pytest.raises(RuntimeError, match=r"g failed with status 0x1234\."):
        ps5000a._check(0x1234, "g")


def test_power_status_names():
    """The power source codes of PicoStatus.h are named."""
    assert ps5000a.STATUS_NAMES[0x11A] == "PICO_POWER_SUPPLY_NOT_CONNECTED"
    assert ps5000a.STATUS_NAMES[0x11E] == "PICO_USB3_0_DEVICE_NON_USB3_0_PORT"


@pytest.mark.parametrize(
    "value, index",
    [(0.01, 0), (0.015, 1), (0.05, 2), (1.0, 6), (1.1, 7), (19.9, 10), (20, 10)],
)
def test_range_index(value, index):
    """The smallest range containing the value is selected."""
    assert ps5000a.range_index(value) == index


@pytest.mark.parametrize("value", [0, -1, 20.5, 50])
def test_range_index_invalid(value):
    """Zero, negative and ranges above +-20 V are refused."""
    with pytest.raises(ValueError):
        ps5000a.range_index(value)


def test_set_channel(scope, lib):
    """The channel setup reaches the driver and is kept in channels."""
    scope.set_channel("c", range_v=0.3, coupling="ac", offset=0.25)
    assert lib.args("ps5000aSetChannel") == [(7, 2, 1, 0, 5, 0.25)]
    assert scope.channels["C"] == {
        "enabled": True,
        "range_v": 0.5,
        "coupling": "AC",
        "offset": 0.25,
    }
    scope.channels["C"]["enabled"] = False  # a copy
    assert scope.channels["C"]["enabled"]
    scope.set_channel("C", enabled=False)
    assert lib.args("ps5000aSetChannel")[-1][2] == 0


def test_set_channel_validation(scope, lib):
    """Invalid arguments raise before reaching the driver."""
    for kwargs in (
        {"channel": "E"},
        {"channel": "A", "coupling": "GND"},
        {"channel": "A", "range_v": 100},
    ):
        with pytest.raises((ValueError, RuntimeError)):
            scope.set_channel(**kwargs)
    assert not lib.args("ps5000aSetChannel")
    assert scope.channels["A"]["range_v"] == 1.0


def test_channels_kept_while_disconnected(lib):
    """Settings given before connecting are applied by connect."""
    inst = PicoScope5000A()
    inst.set_channel("A", range_v=2, coupling="AC")
    inst.set_channel("D", offset=0.1)
    assert not lib.calls
    inst.connect()
    setups = {args[1]: args for args in lib.args("ps5000aSetChannel")}
    assert setups[0] == (7, 0, 1, 0, 7, 0.0)
    assert setups[1][2] == 0
    assert setups[3] == (7, 3, 1, 1, 6, pytest.approx(0.1))


def test_resolution(scope, lib):
    """Changing the resolution calls the driver and applies the channels again."""
    assert scope.resolution == 8
    scope.resolution = 12
    assert scope.resolution == 12
    assert lib.args("ps5000aSetDeviceResolution") == [(7, 1)]
    assert lib.names().index("ps5000aSetDeviceResolution") < lib.names().index(
        "ps5000aSetChannel"
    )
    assert len(lib.args("ps5000aSetChannel")) == 4
    assert scope.get("resolution") == {"resolution": 12}
    scope.set(resolution=8)
    assert scope.resolution == 8


def test_resolution_invalid():
    """Only 8, 12, 14, 15 and 16 bit exist."""
    with pytest.raises(RuntimeError):
        PicoScope5000A(resolution=10)
    with pytest.raises(RuntimeError):
        PicoScope5000A().set(resolution=13)


def test_resolution_channel_limits(scope, lib):
    """At 15 bit two channels are allowed, at 16 bit one."""
    scope.set_channel("C")
    with pytest.raises(ValueError, match="15 bit at most 2"):
        scope.resolution = 15
    scope.set_channel("C", enabled=False)
    scope.resolution = 15
    with pytest.raises(ValueError):
        scope.set_channel("C")
    with pytest.raises(ValueError, match="16 bit at most 1"):
        scope.resolution = 16
    assert scope.resolution == 15
    assert lib.args("ps5000aSetDeviceResolution") == [(7, 3)]
    scope.set_channel("B", enabled=False)
    scope.resolution = 16
    assert scope.resolution == 16


@pytest.mark.parametrize(
    "resolution, timebase, interval",
    [
        (8, 0, 1e-9),
        (8, 1, 2e-9),
        (8, 2, 4e-9),
        (8, 3, 8e-9),
        (8, 127, 1e-6),
        (12, 1, 2e-9),
        (12, 3, 8e-9),
        (12, 4, 16e-9),
        (12, 65, 62 / 62.5e6),
        (14, 3, 8e-9),
        (15, 4, 16e-9),
        (16, 4, 16e-9),
        (16, 5, 32e-9),
    ],
)
def test_timebase_formulas(resolution, timebase, interval):
    """Intervals of the timebase tables of the guide."""
    assert ps5000a.timebase_interval(timebase, resolution) == pytest.approx(interval)
    assert ps5000a.nearest_timebase(interval, resolution) == timebase


def test_nearest_timebase():
    """The closest interval is chosen, also between the power-of-two timebases."""
    assert ps5000a.nearest_timebase(1e-6, 8) == 127
    assert ps5000a.nearest_timebase(1.001e-6, 8) == 127
    assert ps5000a.nearest_timebase(5e-9, 8) == 2
    assert ps5000a.nearest_timebase(1e-12, 8) == 0
    assert ps5000a.nearest_timebase(1e-12, 12) == 1
    assert ps5000a.nearest_timebase(1e-12, 16) == 4
    assert ps5000a.nearest_timebase(16e-6, 16) == 1003
    assert ps5000a.nearest_timebase(1e6, 8) == 2**32 - 1


def test_timebase_invalid():
    """Non-positive intervals and timebases faster than the resolution allows."""
    with pytest.raises(ValueError):
        ps5000a.nearest_timebase(0)
    with pytest.raises(ValueError):
        ps5000a.timebase_interval(0, 12)


def test_set_timebase(scope, lib):
    """The timebase is chosen and verified with ps5000aGetTimebase2."""
    interval = scope.set_timebase(1e-6, 1000)
    assert scope.timebase == 127
    assert interval == pytest.approx(1e-6)
    assert scope.sample_interval == interval
    assert scope.n_samples == 1000
    assert lib.args("ps5000aGetTimebase2") == [(127, 1000)]


def test_set_timebase_skips_invalid(scope, lib):
    """Timebases too fast for the enabled channels give the next valid one."""
    lib.min_timebase = 2
    interval = scope.set_timebase(1e-9, 10)
    assert scope.timebase == 2
    assert interval == pytest.approx(4e-9)
    assert [args[0] for args in lib.args("ps5000aGetTimebase2")] == [0, 1, 2]


def test_set_timebase_no_valid_one(scope, lib):
    """No valid timebase near the requested one."""
    lib.min_timebase = 100
    with pytest.raises(ValueError, match="No valid timebase"):
        scope.set_timebase(1e-9, 10)


def test_set_timebase_too_many_samples(scope, lib):
    """More samples than the memory holds are refused."""
    lib.max_total = 500
    with pytest.raises(ValueError, match="at most 500"):
        scope.set_timebase(1e-6, 1000)
    assert scope.n_samples == 4  # unchanged


def test_set_timebase_disconnected():
    """Without connection the timebase comes from the formulas."""
    inst = PicoScope5000A(resolution=16)
    assert inst.set_timebase(16e-6, 100) == pytest.approx(16e-6, rel=1e-3)
    assert inst.timebase == 1003


def test_set_timebase_follows_resolution(scope, lib):
    """After a resolution change the timebase is chosen again."""
    assert scope.timebase == 127
    scope.set_channel("B", enabled=False)
    scope.resolution = 16
    assert scope.timebase == 65
    assert scope.sample_interval == pytest.approx(62 / 62.5e6)


def test_trigger_counts(scope, lib):
    """The level is converted to ADC counts of the channel range."""
    scope.set_trigger("A", 0.5)
    assert lib.args("ps5000aSetSimpleTrigger") == [(7, 1, 0, 16256, 2, 0, 0)]
    scope.set_trigger("a", -0.25, direction="falling", delay=10, auto_trigger_ms=100)
    assert lib.args("ps5000aSetSimpleTrigger")[-1] == (7, 1, 0, -8128, 3, 10, 100)
    scope.set_channel("B", range_v=0.1, offset=0.02)
    scope.set_trigger("B", 0.03, "RISING_OR_FALLING")
    assert lib.args("ps5000aSetSimpleTrigger")[-1][2:5] == (1, 16256, 4)
    assert scope.trigger["direction"] == "RISING_OR_FALLING"


def test_trigger_clipped(scope, lib):
    """Levels outside the range are limited to the ADC counts."""
    scope.set_trigger("A", 5)
    assert lib.args("ps5000aSetSimpleTrigger")[-1][3] == 32512


def test_trigger_long_auto_time(scope, lib):
    """Auto trigger times above the int16 limit use the microseconds function."""
    scope.set_trigger("A", 0, auto_trigger_ms=40000)
    assert lib.args("ps5000aSetSimpleTrigger")[-1][-1] == 32767
    assert lib.args("ps5000aSetAutoTriggerMicroSeconds") == [(7, 40_000_000)]


def test_trigger_disabled(scope, lib):
    """A disabled trigger is passed with enable 0."""
    scope.set_trigger("A", 0, enabled=False)
    assert lib.args("ps5000aSetSimpleTrigger")[-1][1] == 0


def test_trigger_validation(scope, lib):
    """Invalid source, direction and disabled source channels are refused."""
    with pytest.raises(ValueError):
        scope.set_trigger("E", 0)
    with pytest.raises(RuntimeError):
        scope.set_trigger("A", 0, direction="SIDEWAYS")
    with pytest.raises(ValueError, match="not enabled"):
        scope.set_trigger("C", 0)
    assert scope.trigger is None
    assert not lib.args("ps5000aSetSimpleTrigger")


def test_trigger_follows_channel_and_resolution(scope, lib):
    """The counts are computed again when range or resolution change."""
    scope.set_trigger("A", 0.5)
    scope.set_channel("A", range_v=2)
    assert lib.args("ps5000aSetSimpleTrigger")[-1][3] == 8128
    scope.resolution = 12
    assert lib.args("ps5000aSetSimpleTrigger")[-1][3] == round(0.25 * 32767)


def test_acquire(scope, lib):
    """Counts are converted to volts and the time axis is relative to the trigger."""
    scope.set_channel("B", range_v=0.5, offset=0.1)
    time, data = scope.acquire()
    assert lib.args("ps5000aRunBlock") == [(0, 4, 127, 0)]
    assert lib.args("ps5000aGetValues") == [(0, 4, 0)]
    np.testing.assert_allclose(time, np.arange(4) * 1e-6, atol=1e-12)
    assert set(data) == {"A", "B"}
    np.testing.assert_allclose(data["A"], [0, 0.5, -1, 1])
    np.testing.assert_allclose(
        data["B"], np.array([100, 200, 300, 400]) / 32512 * 0.5 - 0.1
    )


def test_acquire_16bit_scale(scope, lib):
    """The ADC maximum of the resolution is used."""
    scope.set_channel("B", enabled=False)
    scope.resolution = 12
    lib.data[0] = np.array([32767, -32767, 0, 16383])
    _, data = scope.acquire("A")
    np.testing.assert_allclose(data["A"], [1, -1, 0, 16383 / 32767])


def test_acquire_channels_and_pre_trigger(scope, lib):
    """A channel subset can be read; pre-trigger samples shift the time axis."""
    scope.set_timebase(1e-6, 8)
    scope.set_trigger("A", 0.1, delay=0)
    time, data = scope.acquire(["B"], pre_trigger=3e-6)
    assert set(data) == {"B"}
    assert lib.args("ps5000aSetDataBuffer")[-1][0] == 1
    assert lib.args("ps5000aRunBlock")[-1][:2] == (3, 5)
    assert len(time) == len(data["B"]) == 8
    assert time[0] == pytest.approx(-3e-6)
    assert time[3] == pytest.approx(0, abs=1e-12)


def test_acquire_trigger_delay(scope):
    """The trigger delay in samples offsets the time axis."""
    scope.set_trigger("A", 0, delay=5)
    time, _ = scope.acquire("A")
    assert time[0] == pytest.approx(5e-6)


def test_acquire_validation(scope, lib):
    """Disabled channels, empty selections and bad times are refused."""
    with pytest.raises(ValueError, match="not enabled"):
        scope.acquire("C")
    with pytest.raises(ValueError, match="at least 1"):
        scope.acquire(averages=0)
    with pytest.raises(ValueError, match="Pre-trigger"):
        scope.acquire(pre_trigger=1)
    with pytest.raises(ValueError):
        scope.acquire(pre_trigger=-1e-6)
    assert not lib.args("ps5000aRunBlock")
    scope.set_channel("A", enabled=False)
    scope.set_channel("B", enabled=False)
    with pytest.raises(ValueError, match="No channel enabled"):
        scope.acquire()


def test_acquire_needs_connection_and_timebase(lib):
    """Acquiring before connecting or setting the timebase is an error."""
    inst = PicoScope5000A()
    with pytest.raises(ConnectionError):
        inst.acquire()
    inst.connect()
    with pytest.raises(RuntimeError, match="set_timebase"):
        inst.acquire()


def test_acquire_polls_until_ready(scope, lib):
    """IsReady is polled until the capture is complete."""
    lib.ready_after = 3
    scope.acquire("A")
    assert len(lib.args("ps5000aIsReady")) == 4


def test_acquire_timeout(scope, lib):
    """A capture that never completes is stopped and raises TimeoutError."""
    lib.ready_after = None
    with pytest.raises(TimeoutError, match="0.05 s"):
        scope.acquire("A", timeout=0.05)
    assert lib.names()[-1] == "ps5000aStop"
    assert "ps5000aGetValues" not in lib.names()


def test_acquire_driver_error(scope, lib):
    """A failing driver call raises with the status name."""
    lib.status["ps5000aRunBlock"] = BUSY
    with pytest.raises(PicoError, match="ps5000aRunBlock failed with status PICO_BUSY"):
        scope.acquire("A")
    lib.status.clear()
    lib.status["ps5000aGetValues"] = 0x25
    with pytest.raises(RuntimeError, match="PICO_NO_SAMPLES_AVAILABLE"):
        scope.acquire("A")


def test_acquire_averages(scope, lib):
    """Averaged captures are the mean of the voltages of each run."""
    lib.drift = 3251  # +0.1 V of the +-1 V range for each run
    time, data = scope.acquire("B", averages=3)
    assert lib.runs == 3
    assert len(lib.args("ps5000aGetValues")) == 3
    expected = np.array([100, 200, 300, 400]) / 32512 + 0.1
    np.testing.assert_allclose(data["B"], expected, atol=1e-4)
    assert len(time) == 4


def test_overflow_warning(scope, lib, caplog):
    """Channels over range are reported in the log."""
    lib.overflow = 0b01
    with caplog.at_level("WARNING", logger="qtics"):
        scope.acquire(["A", "B"])
    assert "Channel A overrange" in caplog.text
    assert "Channel B overrange" not in caplog.text


def test_acquire_segments(scope, lib):
    """Rapid block: shape, segment buffers and memory restored afterwards."""
    time, data = scope.acquire_segments(5)
    assert set(data) == {"A", "B"}
    assert data["A"].shape == data["B"].shape == (5, 4)
    assert len(time) == 4
    for index in range(5):
        expected = (np.array([0, 16256, -32512, 32512]) + index) / 32512
        np.testing.assert_allclose(data["A"][index], expected)
    assert lib.args("ps5000aMemorySegments") == [(5,), (1,)]
    assert lib.args("ps5000aSetNoOfCaptures") == [(5,), (1,)]
    assert lib.args("ps5000aRunBlock") == [(0, 4, 127, 0)]
    assert lib.args("ps5000aGetValuesBulk") == [(4, 0, 4)]
    buffers = lib.args("ps5000aSetDataBuffer")
    assert len(buffers) == 10
    assert sorted({(args[0], args[2]) for args in buffers}) == [
        (channel, segment) for channel in (0, 1) for segment in range(5)
    ]
    assert lib.names()[-2:] == ["ps5000aMemorySegments", "ps5000aSetNoOfCaptures"]
    assert lib.segments == 1


def test_acquire_segments_too_large(scope, lib):
    """Segments that do not fit in the memory are refused and memory is restored."""
    lib.max_total = 2000
    scope.set_timebase(1e-6, 1000)
    with pytest.raises(ValueError, match="at most 400 samples per segment"):
        scope.acquire_segments(5)
    assert "ps5000aRunBlock" not in lib.names()
    assert lib.args("ps5000aMemorySegments") == [(5,), (1,)]
    assert lib.args("ps5000aSetNoOfCaptures") == [(5,), (1,)]


def test_acquire_segments_timeout_restores_memory(scope, lib):
    """After a timeout the memory is merged again."""
    lib.ready_after = None
    with pytest.raises(TimeoutError):
        scope.acquire_segments(3, timeout=0.02)
    assert lib.args("ps5000aMemorySegments") == [(3,), (1,)]


def test_acquire_segments_validation(scope):
    """At least one capture is needed."""
    with pytest.raises(ValueError):
        scope.acquire_segments(0)


@pytest.mark.skipif(sys.platform == "win32", reason="Linux and macOS library names")
class TestLoadLibrary:
    """Library loading with a stand-in for ctypes.CDLL, the PicoSDK is never loaded."""

    def test_prototypes(self, monkeypatch):
        """Argument and result types are set for the used functions."""
        loaded = []

        class Function:
            """Accepts argtypes and restype."""

        class FakeCDLL:
            """Any function exists."""

            def __init__(self, name):
                loaded.append(name)

            def __getattr__(self, name):
                function = Function()
                setattr(self, name, function)
                return function

        monkeypatch.setattr(ps5000a.ctypes.util, "find_library", lambda name: None)
        monkeypatch.setattr(ps5000a.ctypes, "CDLL", FakeCDLL)
        ps5000a.load_library.cache_clear()
        try:
            library = ps5000a.load_library()
            assert library is ps5000a.load_library()  # cached
            assert loaded == ["libps5000a.so"]
            assert library.ps5000aOpenUnit.argtypes[1] is ctypes.c_char_p
            assert library.ps5000aRunBlock.restype is ctypes.c_uint32
            assert len(library.ps5000aGetValuesBulk.argtypes) == 7
            for name in ps5000a.PROTOTYPES:
                assert getattr(library, name).restype is ctypes.c_uint32
        finally:
            ps5000a.load_library.cache_clear()

    def test_explicit_path(self, monkeypatch):
        """An explicit path is the only one tried."""
        tried = []

        def failing(name):
            tried.append(name)
            raise OSError(name)

        monkeypatch.setattr(ps5000a.ctypes, "CDLL", failing)
        ps5000a.load_library.cache_clear()
        with pytest.raises(OSError, match="PicoSDK"):
            ps5000a.load_library("/nowhere/libps5000a.so")
        assert tried == ["/nowhere/libps5000a.so"]

    def test_not_found(self, monkeypatch):
        """The error tells to install the PicoSDK."""

        def failing(name):
            raise OSError(name)

        monkeypatch.setattr(ps5000a.ctypes.util, "find_library", lambda name: None)
        monkeypatch.setattr(ps5000a.ctypes, "CDLL", failing)
        ps5000a.load_library.cache_clear()
        with pytest.raises(OSError, match="install the PicoSDK"):
            ps5000a.load_library()
