"""Base Experiment classes."""

import time
from abc import ABC, abstractmethod
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from threading import Event

import h5py

from qinst import log
from qinst.instrument import Instrument


class BaseExperiment(ABC):
    """Base experiment class."""

    def __init__(self, name, data_file=""):
        """Initialize."""
        inst_names = []
        if hasattr(self, "__annotations__"):
            for attr_name, attr_type in self.__annotations__.items():
                if Instrument in attr_type.__mro__:
                    inst_names.append(attr_name)
        self.inst_names = inst_names
        self.name = name
        if not data_file.endswith(".hdf5"):
            data_file = f"{name}_{time.strftime('%m/%d_%H:%M:%S')}.hdf5"
        self.data_file = data_file

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
        except Exception as e:
            log.error("\n\nException occured: %s", e)
            self.all_instruments("safe_reset")
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
            inst = getattr(self, name)
            func = getattr(inst, func_name)
            func(*args, **kwargs)

    def append_data_group(self, name: str, datasets: dict, **attributes):
        """Save data appending to hdf5 file."""
        with h5py.File(self.data_file, "a") as file:
            group = file.create_group(name)
            for data_name, data in datasets.items():
                group.create_dataset(data_name, data=data)
            if attributes is not None:
                for attr_name, attr in attributes.items():
                    group.attrs[attr_name] = attr


class MonitorExperiment(BaseExperiment):
    """Base monitoring experiment class."""

    def watch(self, event: Event):
        """Run the experiment continuously until event is set."""
        self.all_instruments("connect")
        while True:
            self.main()
            if event.is_set():
                log.debug("Trigger event set, %s shutting down.", self.name)
                self.all_instruments("safe_reset")
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
        if len(self.monitors) == 0:
            super().run()
        else:
            with ThreadPoolExecutor(1 + len(self.monitors)) as executor:
                futures = []
                log.debug("Starting experiment %s and monitors.", self.name)
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
                        log.debug(
                            "Main experiment finished successfully, shutting down monitors."
                        )
                    self.event.set()
                    for future in futures:
                        future.cancel()

    def monitor_failed(self) -> bool:
        """Check if monitoring condition has failed and restore safe values."""
        if self.event.is_set():
            self.all_instruments("safe_reset")
            return True
        return False
