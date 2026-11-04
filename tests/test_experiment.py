"""Test experiments with fake instruments."""

from __future__ import annotations

import time

import pytest

from qtics import Experiment, MonitorExperiment
from qtics.experiment import MonitorError
from qtics.instruments.base import SCPIInstrument
from qtics.transport import FakeTransport


class Source(SCPIInstrument):
    """Fake instrument counting property reads."""

    reads = 0

    @property
    def level(self) -> float:
        """Level, counts reads."""
        Source.reads += 1
        return 0.0


def make_source(name="src"):
    """Fake source with a fake transport."""
    return Source(FakeTransport(default="0"), name=name)


class TempMonitor(MonitorExperiment):
    """Monitor failing on its second check."""

    sleep = 0.01

    def __init__(self, name):
        """Initialize the check counter."""
        super().__init__(name)
        self.checks = 0

    def main(self):
        """Fail on the second check."""
        self.checks += 1
        if self.checks >= 2:
            raise RuntimeError("temperature too high")


class Measure(Experiment):
    """Experiment with a class-level instrument and monitor."""

    src = make_source()
    later: Source  # added with add_instrument
    maybe: Source | None = None  # optional instrument
    monitors = [TempMonitor("temp")]

    def main(self):
        """Wait for the monitor to fail."""
        for _ in range(200):
            if self.monitor_failed():
                return "stopped"
            time.sleep(0.01)
        return "finished"


class Broken(Experiment):
    """Experiment whose main raises."""

    src = make_source()
    monitors = [TempMonitor("never_fails")]

    def main(self):
        """Raise."""
        raise ValueError("bad measurement")


def test_instruments_discovered_without_reading_properties(tmp_path):
    """Instruments in attributes and annotations, properties are not read."""
    Source.reads = 0
    exp = Measure("m", data_dir=str(tmp_path))
    assert exp.inst_names == ["src", "later", "maybe"]
    assert Source.reads == 0


class Unresolvable(Experiment):
    """Experiment with an annotation that cannot be resolved."""

    ghost: UndefinedName  # type: ignore[name-defined]  # noqa: F821
    opt: Source | None

    def main(self):
        """Do nothing."""


class WithInit(Experiment):
    """Experiment assigning an instrument in __init__."""

    def __init__(self, name, data_dir):
        """Assign the instrument after the base initialization."""
        super().__init__(name, data_dir=data_dir)
        self.dynamic = make_source()

    def main(self):
        """Do nothing."""


def test_discovery_robust(tmp_path):
    """Unresolvable annotations are skipped, instance attributes are found."""
    assert Unresolvable("u", data_dir=str(tmp_path)).inst_names == ["opt"]
    assert WithInit("w", str(tmp_path)).inst_names == ["dynamic"]


def test_class_monitors_used(tmp_path, mocker):
    """Monitors declared on the class run; their failure stops main and is raised."""
    exp = Measure("m", data_dir=str(tmp_path))
    assert [m.name for m in exp.monitors] == ["temp"]
    exp.monitors[0].checks = 0
    reset = mocker.spy(Measure.src, "reset")
    with pytest.raises(MonitorError, match="temperature too high"):
        exp.run()
    assert exp.monitors[0].checks == 2  # no extra check after the stop
    reset.assert_called_once()  # by monitor_failed, not again by run


class Quick(Experiment):
    """Experiment finishing before its monitor fails."""

    src = make_source()
    monitors = [TempMonitor("slow")]

    def main(self):
        """Finish at once."""


def test_monitor_failed_false_after_success(tmp_path):
    """A successful run leaves no failure behind, and can run again."""
    exp = Quick("q", data_dir=str(tmp_path))
    exp.monitors[0].checks = 0
    exp.run()
    assert not exp.monitor_failed()
    exp.run()
    assert not exp.monitor_failed()


class Ignoring(Experiment):
    """Experiment never checking its monitors."""

    src = make_source()
    monitors = [TempMonitor("ignored")]

    def main(self):
        """Run longer than the monitor failure."""
        time.sleep(0.2)


def test_monitor_failure_raised_when_ignored(tmp_path, mocker):
    """A monitor failure not handled by main is raised after resetting."""
    exp = Ignoring("i", data_dir=str(tmp_path))
    exp.monitors[0].checks = 0
    reset = mocker.spy(Ignoring.src, "reset")
    with pytest.raises(MonitorError):
        exp.run()
    reset.assert_called_once()


def test_main_exception_reraised_and_reset(tmp_path, mocker):
    """With monitors, a failing main is re-raised after resetting instruments."""
    exp = Broken("b", data_dir=str(tmp_path))
    reset = mocker.spy(Broken.src, "reset")
    with pytest.raises(ValueError, match="bad measurement"):
        exp.run()
    reset.assert_called_once()
    assert exp.event.is_set()


def test_add_instrument(tmp_path):
    """Instruments are added by name, unknown names raise."""
    exp = Measure("m", data_dir=str(tmp_path))
    inst = make_source(name="whatever")
    exp.add_instrument(inst, name="later")
    assert exp.later is inst
    with pytest.raises(ValueError):
        exp.add_instrument(make_source(name="unknown"))


def test_close_disconnects(tmp_path):
    """Closing the experiment (also via with) disconnects the instruments."""
    exp = Measure("m", data_dir=str(tmp_path))
    exp.src.connect()
    exp.src.update_defaults(level=0.0)
    with exp:
        assert exp.src.is_connected
    assert not exp.src.is_connected
    assert exp.src.defaults == {}


class FailsAfterCheck(Experiment):
    """Experiment raising after handling a monitor failure."""

    src = make_source()
    monitors = [TempMonitor("fails")]

    def main(self):
        """Raise once the monitor failure is seen."""
        for _ in range(200):
            if self.monitor_failed():
                raise RuntimeError("aborted")
            time.sleep(0.01)


def test_no_double_reset(tmp_path, mocker):
    """Instruments are reset once, even if main raises after a monitor failure."""
    exp = FailsAfterCheck("f", data_dir=str(tmp_path))
    exp.monitors[0].checks = 0
    reset = mocker.spy(FailsAfterCheck.src, "reset")
    with pytest.raises(RuntimeError, match="aborted"):
        exp.run()
    reset.assert_called_once()


class Containers(Experiment):
    """Experiment with annotations containing instruments but not instruments."""

    many: list[Source]
    table: dict[str, Source]
    numbers: list[int]
    single: Source | None

    def main(self):
        """Do nothing."""


def test_container_annotations_not_instruments(tmp_path):
    """Only instrument classes and Optional/Union of them are instruments."""
    assert Containers("c", data_dir=str(tmp_path)).inst_names == ["single"]
