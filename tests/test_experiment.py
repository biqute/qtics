"""Test experiment class."""

from time import sleep

import h5py
import pytest

from qtics.experiment import BaseExperiment, Experiment, MonitorExperiment
from qtics.instrument import Instrument


class DummyInstrument(Instrument):
    """Dummy instrument class."""

    def connect(self):
        """Connect to the instrument."""
        pass

    def disconnect(self):
        """Disonnect from the instrument."""
        pass

    def write(self, cmd, sleep=False):
        """Send a command to the instrument."""
        pass

    def read(self):
        """Read from the instrument."""
        return 1

    def query(self, cmd) -> float:
        """Send a command and read from the instrument."""
        self.write(cmd)
        return self.read()


class DummyExperiment(Experiment):
    """Dummy experiment class."""

    instrument1 = DummyInstrument("instrument1", "address")
    instrument2: DummyInstrument
    exp_attr = "attr value"

    def main(self):
        """Run main part of the experiment."""
        sleep(0.1)
        _ = self.monitor_failed()


class DummyMonitor(MonitorExperiment):
    """Dummy monitor experiment class."""

    inst = DummyInstrument("inst", "address")
    max_read = 1

    def main(self):
        """Run main part of the experiment."""
        sleep(0.05)
        if self.inst.read() > self.max_read:
            raise Exception("Read value over allowed maximum.")


@pytest.fixture
def instrument():
    """Dummy instrument fixture."""
    return DummyInstrument("instrument2", "address")


@pytest.fixture
def experiment(tmpdir):
    """Dummy experiment fixture."""
    datafile = str(tmpdir.join("datafile.hdf5"))
    return DummyExperiment("exp", data_file=datafile)


@pytest.fixture
def monitor():
    """Dummy monitor fixture."""
    return DummyMonitor("testmonitor")


def test_init(experiment, tmpdir):
    """Test initialization."""
    assert isinstance(experiment, DummyExperiment)
    assert isinstance(experiment, Experiment)
    assert isinstance(experiment, BaseExperiment)
    assert experiment.name == "exp"
    assert experiment.inst_names == ["instrument1", "instrument2"]
    assert experiment.data_file == str(tmpdir.join("datafile.hdf5"))
    assert experiment.monitors == []
    assert not experiment.monitor_failed()


def test_add_instrument(experiment, instrument):
    """Test adding instruments."""
    assert not hasattr(experiment, "instrument2")
    experiment.add_instrument(instrument)
    assert hasattr(experiment, "instrument2")
    instrument.name = "not_allowed"
    experiment.add_instrument(instrument)
    assert not hasattr(experiment, "not_allowed")


def test_add_monitor(experiment, monitor):
    """Test adding monitors."""
    experiment.add_monitor(monitor)
    assert experiment.monitors == [monitor]


def test_all_instruments(experiment, instrument):
    """Test applying function to all instruments."""
    experiment.add_instrument(instrument)
    experiment.all_instruments("set", address="setaddr")

    assert experiment.instrument1.address == "setaddr"
    assert experiment.instrument2.address == "setaddr"


def test_append_data_group(experiment):
    """Test appending to data file."""
    datasets = {"data1": [1, 2, 3], "data2": [4, 5, 6]}
    attributes = {"attr1": "value1", "attr2": "value2"}

    experiment.append_data_group("group1", datasets=datasets, **attributes)

    with h5py.File(experiment.data_file, "r") as file:
        assert "group1" in file
        group1 = file["group1"]

        for name, data in datasets.items():
            assert name in list(group1)
            assert list(group1[name]) == data

        for key, value in attributes.items():
            assert key in group1.attrs
            assert group1.attrs[key] == value


def test_save_config(experiment):
    """Test saving config to data file."""
    experiment.instrument1.update_defaults(address="default address")
    experiment.instrument1.set_defaults()
    experiment.save_config()
    with h5py.File(experiment.data_file, "r") as file:
        assert "config" in file
        config = file["config"]
        assert dict(config.attrs) == {
            "exp_attr": "attr value",
            "name": experiment.name,
            "data_file": experiment.data_file,
        }
        assert dict(config["instrument1"].attrs) == {"address": "default address"}


def test_successful_run(experiment, monitor):
    """Test succesful run."""
    experiment.instrument1.update_defaults(name="reset occurred")
    experiment.add_monitor(monitor)
    experiment.run()
    assert experiment.instrument1.name == "instrument1"


def test_unsuccessful_run(experiment, monitor):
    """Test run with monitor failure."""
    monitor.max_read = 0
    experiment.instrument1.update_defaults(name="reset occurred")
    experiment.add_monitor(monitor)
    experiment.run()
    assert experiment.instrument1.name == "reset occurred"


if __name__ == "__main__":
    pytest.main()
