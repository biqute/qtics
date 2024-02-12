"""
Base Experiment classes.

.. module:: experiment.py

"""

import os
import time
from abc import ABC, abstractmethod
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from threading import Event
from typing import List, Optional

import h5py
import numpy as np

from qtics import log
from qtics.instruments import Instrument


class BaseExperiment(ABC):
    """Base experiment class."""

    def __init__(
        self, name: str, data_file: Optional[str] = None, data_dir: Optional[str] = None
    ):
        """Initialize datafile and instruments names."""
        self.name = name
        self.data_dir = data_dir

        if data_file is not None:
            if not data_file.endswith(".hdf5"):
                data_file += ".hdf5"
        else:
            data_file = f"{name}_{time.strftime('%m_%d_%H_%M_%S')}.hdf5"

        if data_dir is not None:
            os.makedirs(data_dir, exist_ok=True)
            self.data_file = os.path.join(data_dir, data_file)
        else:
            self.data_file = data_file

        self._update_intruments_names()

    def _update_intruments_names(self):
        """Update list of instruments stored in the experiment."""
        self.inst_names = []
        for attr_name in dir(self):
            if not attr_name.startswith("_") and isinstance(
                getattr(self, attr_name), Instrument
            ):
                self.inst_names.append(attr_name)
        if hasattr(self, "__annotations__"):
            for attr_name, attr_type in self.__annotations__.items():
                if Instrument in attr_type.__mro__:
                    self.inst_names.append(attr_name)

    def __del__(self):
        """Disconnect all devices and delete."""
        self.all_instruments("clear_defaults")
        self.all_instruments("disconnect")

    @abstractmethod
    def main(self):
        """Execute main part of the experiment."""

    def run(self):
        """Run the experiment."""
        log.info("Starting experiment %s.", self.name)
        try:
            self.main()
        except KeyboardInterrupt as exc:
            log.warning("Interrupt signal received, exiting")
            self.all_instruments("reset")
            raise exc
        except Exception as exc:
            log.error("Exception occurred: %s", exc)
            self.all_instruments("reset")
            raise exc
        log.info("Experiment run successfully.")

    def add_instrument(self, inst: Instrument):
        """Add an instrument with the correct name."""
        name = inst.name
        if name not in self.inst_names:
            log.warning(
                "Instrument %s not allowed, choose between %s.", name, self.inst_names
            )
        else:
            setattr(self, name, inst)
            log.info("Added instrument %s.", name)

    def all_instruments(self, func_name: str, *args, **kwargs):
        """Apply function to all instruments."""
        for name in self.inst_names:
            if hasattr(self, name):
                inst = getattr(self, name)
                func = getattr(inst, func_name)
                _ = func(*args, **kwargs)

    def append_data_group(
        self,
        group_name: str,
        parent_name: Optional[str] = None,
        datasets: Optional[dict] = None,
        **attributes,
    ):
        """Save data appending to hdf5 file."""
        with h5py.File(self.data_file, "a") as file:
            if parent_name is not None:
                parent_group = file.require_group(parent_name)
                group = parent_group.require_group(group_name)
            else:
                group = file.require_group(group_name)

            if datasets is not None:
                for data_name, data in datasets.items():
                    group.create_dataset(data_name, data=data)
            if attributes:
                group.attrs.update(attributes)

    def get_datasets_dict(self, data_file: Optional[str] = None):
        """Load the datasets of an hdf5 file as dictionary."""

        def _recurse(h5file, path):
            data = {}
            group = h5file[path]
            for key in list(group):
                if key != "config":
                    item = group.get(key)
                    if isinstance(item, h5py.Dataset):
                        data[key] = np.asarray(group.get(key))
                    elif isinstance(item, h5py.Group):
                        data[key] = _recurse(h5file, path + key + "/")
            return data

        if not data_file:
            data_file = self.data_file

        with h5py.File(data_file, "r") as h5file:
            return _recurse(h5file, "/")

    def save_config(self):
        """Save experiment's attributes and instruments defaults."""
        config_attr = {
            key: getattr(self, key)
            for key in dir(self)
            if isinstance(getattr(self, key), (int, float, str, bool))
            and not key.startswith("_")
        }
        self.append_data_group("config", **config_attr)
        for inst_name in self.inst_names:
            if hasattr(self, inst_name):
                inst = getattr(self, inst_name)
                self.append_data_group(inst_name, parent_name="config", **inst.defaults)


class MonitorExperiment(BaseExperiment):
    """Base monitoring experiment class."""

    sleep: float = 5

    def watch(self, event: Event):
        """Run the experiment continuously until event is set."""
        self.all_instruments("connect")
        log.info("Running monitor %s", self.name)
        while not event.is_set():
            time.sleep(self.sleep)
            self.main()
        log.info("Trigger event set, %s shutting down.", self.name)


class Experiment(BaseExperiment):
    """Experiment with monitoring functions."""

    def __init__(
        self, name: str, data_file: Optional[str] = None, data_dir: Optional[str] = None
    ):
        """Initialize."""
        super().__init__(name, data_file=data_file, data_dir=data_dir)
        self.monitors: List[MonitorExperiment] = []
        self.event = Event()

    def add_monitor(self, monitor: MonitorExperiment):
        """Add monitoring experiment."""
        self.monitors.append(monitor)

    def run(self):
        """Run the experiment with parallel monitoring functions."""
        self.event.clear()
        if len(self.monitors) == 0:
            super().run()
            return
        with ThreadPoolExecutor(1 + len(self.monitors)) as executor:
            futures = []
            log.info("Starting experiment %s and monitors.", self.name)
            for monitor in self.monitors:
                futures.append(executor.submit(monitor.watch, self.event))
            futures.append(executor.submit(self.main))
            done, _ = wait(futures, return_when=FIRST_COMPLETED)
            if len(done) > 0 and len(done) != len(futures):
                future = done.pop()
                if future.exception() is not None:
                    log.warning(
                        "One task failed with: %s, shutting down.",
                        future.exception(),
                    )
                else:
                    log.info(
                        "Main experiment finished successfully, shutting down monitors."
                    )
                self.event.set()
                for future in futures:
                    future.cancel()

    def monitor_failed(self) -> bool:
        """Check if monitoring condition has failed and restore safe values."""
        if self.event.is_set():
            log.warning("Exception event has occurred.")
            self.all_instruments("reset")
            return True
        return False
