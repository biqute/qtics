"""Base Experiment classes."""

import sys
from abc import ABC, abstractmethod
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from threading import Event

import yaml

from qinst import log
from qinst.instrument import Instrument


class BaseExperiment(ABC):
    """Base experiment class."""

    def __init__(self, name):
        """Initialize."""
        self.name = name
        self.instruments = []

    @abstractmethod
    def main(self):
        """Execute main part of the experiment."""

    def run(self):
        """Run the experiment."""
        self.main()

    def add_instrument(self, inst: Instrument):
        """Add an instrument."""
        name = inst.name
        if name not in self.instruments:
            self.instruments.append(name)
            setattr(self, name, inst)
        else:
            log.warning(f"Instrument name {name} already in use")

    def from_yaml(self, filename: str):
        """Initialize experiment from configuration file."""
        config = self.dict_from_yaml(filename)
        self.from_dict(config)

    def dict_from_yaml(self, filename: str):
        """Load yaml file as dictionary."""
        with open(filename) as f:
            config = yaml.safe_load(f)
        return config

    def from_dict(self, config: dict):
        """Initialize experiment from configuration dictionary."""
        self.instruments_from_dict(config["instruments"])
        if "variables" in config.keys():
            self.variables_from_dict(config)

    def instruments_from_dict(self, config: dict):
        """Initialize instruments from configuration dictionary."""
        for inst_name, inst_conf in config.items():
            inst_class = getattr(sys.modules["qinst"], inst_conf["class"])
            inst = inst_class(inst_name, **inst_conf["init"])
            if "set" in inst_conf.keys():
                inst.connect()
                inst.set(**inst_conf["set"])
            if "safe" in inst_conf.keys():
                inst.set_safe_options(**inst_conf["safe"])
            self.add_instrument(inst)

    def variables_from_dict(self, config: dict):
        """Initialize bonus attributes from configuration dictionary."""
        for key, value in config.items():
            if hasattr(self, key):
                raise RuntimeError(
                    f"experiment already has attribute {key}, choose another name."
                )
            else:
                setattr(self, key, value)

    def safe_reset(self):
        """Reset instruments to safe options."""
        log.info(f"Setting safe parameters for instruments in {self.name}.")
        for name in self.instruments:
            getattr(self, name).safe_reset()


class MonitorExperiment(BaseExperiment):
    """Base monitoring experiment class."""

    def watch(self, event: Event):
        """Run the experiment continuously until event is set."""
        while True:
            self.main()
            if event.is_set():
                log.debug(f"Trigger event set, {self.name} shutting down.")
                return


class Experiment(BaseExperiment):
    """Experiment with monitoring functions."""

    def __init__(self, name):
        """Initialize."""
        super().__init__(name)
        self.monitors = []

    def add_monitor(self, monitor: MonitorExperiment):
        """Add monitoring experiment."""
        self.monitors.append(monitor)

    def run(self):
        """Run the experiment with parallel monitoring functions."""
        self.event = Event()
        with ThreadPoolExecutor(1 + len(self.monitors)) as executor:
            futures = []
            log.debug(f"Starting experiment {self.name} and monitors.")
            for m in self.monitors:
                futures.append(executor.submit(m.watch, self.event))
            futures.append(executor.submit(self.main))
            done, _ = wait(futures, return_when=FIRST_COMPLETED)
            if len(done) > 0 and len(done) != len(futures):
                future = done.pop()
                if future.exception() != None:
                    log.warning(
                        f"One task failed with: {future.exception()}, shutting down."
                    )
                else:
                    log.debug(
                        "Main experiment finished succesfully, shutting down monitors."
                    )
                self.event.set()
                for future in futures:
                    future.cancel()

    def monitor_failed(self) -> bool:
        """Check if monitoring condition has failed and restore safe values."""
        if self.event.is_set():
            self.safe_reset()
            return True
        return False

    def from_dict(self, config: dict):
        """Initialize experiment from configuration dictionary."""
        super().from_dict(config)
        if "monitors" in config.keys():
            for name, class_name in config["monitors"].items():
                monitor_class = getattr(sys.modules["qinst"], class_name)
                self.add_monitor(monitor_class(name))
