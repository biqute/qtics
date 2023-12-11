"""Base Experiment classes."""

from abc import ABC, abstractmethod
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from threading import Event

from qinst import log
from qinst.instrument import Instrument


class BaseExperiment(ABC):
    """Base experiment class."""

    def __init__(self, name):
        """Initialize."""
        self.name = name
        self.instruments = {}
        self.safe_opts = {}

    @abstractmethod
    def run(self):
        """Run the experiment."""

    @abstractmethod
    def main(self):
        """Execute main part of the experiment."""

    def add_instrument(self, inst: Instrument, safe_opt=None):
        """Add an instrument."""
        name = inst.name
        if name not in self.instruments.keys():
            self.instruments[name] = inst
            if safe_opt is not None and isinstance(safe_opt, dict):
                self.safe_opts[name] = safe_opt
        else:
            log.warning(f"Instrument name {name} already in use")

    def safe_reset(self):
        """Reset instruments to safe options."""
        log.info(f"Setting safe parameters for instruments in {self.name}.")
        for name, inst in self.instruments.items():
            if name not in self.safe_opts.keys():
                inst.reset()
            else:
                inst.set(**self.safe_opts[name])


class MonitorExperiment(BaseExperiment, ABC):
    """Base monitoring experiment class."""

    def run(self, event: Event):
        """Run the experiment until event is set."""
        while True:
            self.main()
            if event.is_set():
                log.debug(f"Trigger event set, {self.name} shutting down.")
                return


class Experiment(BaseExperiment, ABC):
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
                futures.append(executor.submit(m.run, self.event))
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
