"""Base Experiment classes."""

import time
from abc import ABC, abstractmethod
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from threading import Event

import h5py

from qtics import log
from qtics.instrument import Instrument


class BaseExperiment(ABC):
    """Base experiment class."""

    def __init__(self, name, data_file=""):
        """Initialize."""
        self.name = name
        if not data_file.endswith(".hdf5"):
            data_file = f"{name}_{time.strftime('%m_%d_%H_%M_%S')}.hdf5"
        self.data_file = data_file
        self.inst_names = []
        for attr_name, value in self.__class__.__dict__.items():
            if not attr_name.startswith("_") and Instrument in type(value).__mro__:
                self.inst_names.append(attr_name)
        if hasattr(self, "__annotations__"):
            for attr_name, attr_type in self.__annotations__.items():
                if Instrument in attr_type.__mro__:
                    self.inst_names.append(attr_name)

    def __del__(self):
        """Disconnect all devices and delete."""
        self.all_instruments("disconnect")

    @abstractmethod
    def main(self):
        """Execute main part of the experiment."""

    def run(self):
        """Run the experiment."""
        log.info("Starting experiment %s.", self.name)
        try:
            self.main()
        except KeyboardInterrupt:
            log.warning("Interrupt signal received, exiting")
            self.all_instruments("reset")
        except Exception as e:
            log.error("\n\nException occured: %s", e)
            self.all_instruments("reset")
        finally:
            log.info("Experiment run succesfully.")

    def add_instrument(self, inst: Instrument):
        """Add an instrument."""
        name = inst.name
        if name not in self.inst_names:
            log.warning(
                "Instrument name %s not in allowed instruments %s.",
                name,
                self.inst_names,
            )
        else:
            setattr(self, name, inst)
            log.info("Added instrument %s.", name)

    def all_instruments(self, func_name, *args, **kwargs):
        """Apply function to all instruments."""
        for name in self.inst_names:
            if hasattr(self, name):
                inst = getattr(self, name)
                func = getattr(inst, func_name)
                _ = func(*args, **kwargs)

    def append_data_group(
        self, group_name: str, parent_name="", datasets=None, **attributes
    ):
        """Save data appending to hdf5 file."""
        with h5py.File(self.data_file, "a") as file:
            if parent_name != "":
                if hasattr(file, parent_name):
                    parent_group = getattr(file, parent_name)
                else:
                    parent_group = file.create_group(parent_name)
                group = parent_group.create_group(group_name)
            else:
                group = file.create_group(group_name)
            if datasets is not None:
                for data_name, data in datasets.items():
                    group.create_dataset(data_name, data=data)
            if attributes:
                group.attrs.update(attributes)


class MonitorExperiment(BaseExperiment):
    """Base monitoring experiment class."""

    def watch(self, event: Event):
        """Run the experiment continuously until event is set."""
        self.all_instruments("connect")
        log.info("Running monitor %s", self.name)
        while True:
            self.main()
            if event.is_set():
                log.info("Trigger event set, %s shutting down.", self.name)
                return


class Experiment(BaseExperiment):
    """Experiment with monitoring functions."""

    def __init__(self, name, data_file=""):
        """Initialize."""
        super().__init__(name, data_file=data_file)
        self.monitors = []
        self.event = Event()

    def add_monitor(self, monitor: MonitorExperiment):
        """Add monitoring experiment."""
        self.monitors.append(monitor)

    def run(self):
        """Run the experiment with parallel monitoring functions."""
        self.event.clear()
        if len(self.monitors) == 0:
            super().run()
        else:
            with ThreadPoolExecutor(1 + len(self.monitors)) as executor:
                futures = []
                log.info("Starting experiment %s and monitors.", self.name)
                for m in self.monitors:
                    futures.append(executor.submit(m.watch, self.event))
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
