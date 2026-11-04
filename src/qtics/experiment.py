"""
Base Experiment classes.

.. module:: experiment.py

"""

import inspect
import os
import sys
import time
import types
import typing
from abc import ABC, abstractmethod
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from threading import Event
from typing import List, Optional

import h5py
import numpy as np

from qtics import log
from qtics.instruments import Instrument


class MonitorError(RuntimeError):
    """A monitor of the experiment failed."""


def _is_instrument_type(hint) -> bool:
    """Whether a type hint is an instrument class, also inside Optional/Union."""
    origin = typing.get_origin(hint)
    if origin is None:
        # Generic aliases like list[int] are not classes (inspect.isclass is True
        # for them on Python 3.10)
        return isinstance(hint, type) and issubclass(hint, Instrument)
    if origin in (typing.Union, types.UnionType):
        return any(_is_instrument_type(arg) for arg in typing.get_args(hint))
    return False


def _class_annotations(cls) -> dict:
    """Resolve the annotations of a class and its bases, skipping invalid ones."""
    try:
        return typing.get_type_hints(cls)
    except Exception:  # pylint: disable=broad-except
        pass
    hints = {}
    for klass in reversed(cls.__mro__):
        try:
            annotations = inspect.get_annotations(klass)
        except Exception:  # pylint: disable=broad-except
            continue
        module = vars(sys.modules.get(klass.__module__, typing))
        for name, hint in annotations.items():
            if isinstance(hint, str):
                try:
                    hint = eval(hint, module, dict(vars(klass)))  # noqa: S307
                except Exception:  # pylint: disable=broad-except
                    continue
            hints[name] = hint
    return hints


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

    @property
    def inst_names(self) -> List[str]:
        """Names of the instruments of the experiment.

        Instruments are attributes holding an instrument, or class annotations with an
        instrument type (set later with :meth:`add_instrument`). Attributes are
        inspected without reading properties.
        """
        names: List[str] = []
        namespaces = [vars(cls) for cls in reversed(type(self).__mro__)]
        for namespace in [*namespaces, vars(self)]:
            for attr_name, value in namespace.items():
                if isinstance(value, Instrument):
                    names.append(attr_name)
        for attr_name, hint in _class_annotations(type(self)).items():
            if _is_instrument_type(hint):
                names.append(attr_name)
        return [name for name in dict.fromkeys(names) if not name.startswith("_")]

    def close(self):
        """Clear the instruments defaults and disconnect them."""
        self.all_instruments("clear_defaults")
        self.all_instruments("disconnect")

    def __enter__(self):
        """Use the experiment in a ``with`` block, closing it at the end."""
        return self

    def __exit__(self, *exc):
        """Close the experiment."""
        self.close()

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
            self.reset_instruments()
            raise exc
        except Exception as exc:
            log.error("Exception occurred: %s", exc)
            self.reset_instruments()
            raise exc
        log.info("Experiment run successfully.")

    def reset_instruments(self):
        """Reset all instruments, logging (not raising) individual failures."""
        for name in self.inst_names:
            inst = getattr(self, name, None)
            if inst is None:
                continue
            try:
                inst.reset()
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Reset of %s failed: %s", name, exc)

    def add_instrument(self, inst: Instrument, name: Optional[str] = None):
        """Add an instrument as attribute ``name`` (default: the instrument name)."""
        name = name or inst.name
        allowed = self.inst_names
        if name not in allowed:
            raise ValueError(
                f"Instrument {name} not allowed, choose between {allowed}."
            )
        setattr(self, name, inst)
        log.info("Added instrument %s.", name)

    def all_instruments(self, func_name: str, *args, **kwargs):
        """Apply function to all instruments (skipping the ones not set)."""
        for name in self.inst_names:
            inst = getattr(self, name, None)
            if inst is not None:
                getattr(inst, func_name)(*args, **kwargs)

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
            inst = getattr(self, inst_name, None)
            if inst is not None:
                self.append_data_group(inst_name, parent_name="config", **inst.defaults)


class MonitorExperiment(BaseExperiment):
    """Base monitoring experiment class."""

    sleep: float = 5

    def watch(self, event: Event):
        """Run the experiment continuously until event is set."""
        self.all_instruments("connect")
        log.info("Running monitor %s", self.name)
        while not event.wait(self.sleep):
            self.main()
        log.info("Trigger event set, %s shutting down.", self.name)


class Experiment(BaseExperiment):
    """Experiment with monitoring functions.

    Monitors can be declared in the class attribute ``monitors`` or added with
    :meth:`add_monitor`. While they run, :meth:`main` should periodically check
    :meth:`monitor_failed` and stop when it returns True: a failed monitor is then
    raised by :meth:`run` as :class:`MonitorError`.
    """

    monitors: List[MonitorExperiment] = []

    def __init__(
        self, name: str, data_file: Optional[str] = None, data_dir: Optional[str] = None
    ):
        """Initialize."""
        self.event = Event()
        self._monitor_error: Optional[BaseException] = None
        self._failure_handled = False
        # Copy, so that add_monitor does not change the class attribute
        self.monitors = list(type(self).monitors)
        super().__init__(name, data_file=data_file, data_dir=data_dir)

    def add_monitor(self, monitor: MonitorExperiment):
        """Add monitoring experiment."""
        self.monitors.append(monitor)

    def run(self):
        """Run the experiment with parallel monitoring functions."""
        self.event.clear()
        self._monitor_error = None
        self._failure_handled = False
        if len(self.monitors) == 0:
            super().run()
            return
        log.info("Starting experiment %s and monitors.", self.name)
        executor = ThreadPoolExecutor(1 + len(self.monitors))
        pending = {executor.submit(m.watch, self.event) for m in self.monitors}
        main = executor.submit(self.main)
        pending.add(main)
        try:
            while main in pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    if future is not main and future.exception() is not None:
                        self._record_failure(future.exception())
            exc = main.exception()
        except KeyboardInterrupt:
            log.warning("Interrupt signal received, exiting")
            # main runs in a thread that cannot be killed: it stops (and the
            # process can exit) only when it checks monitor_failed
            self._record_failure(MonitorError("Interrupted"))
            self._failure_handled = True
            executor.shutdown(wait=False, cancel_futures=True)
            self.reset_instruments()
            raise
        finally:
            self.event.set()  # stops the monitors
        executor.shutdown()
        for future in pending:
            if future.exception() is not None:
                self._record_failure(future.exception())
        if exc is not None:
            log.error("Exception occurred: %s", exc)
            if not self._failure_handled:
                self.reset_instruments()
            raise exc
        if self._monitor_error is not None:
            if not self._failure_handled:
                self.reset_instruments()
            raise MonitorError(
                f"Monitor failed: {self._monitor_error}"
            ) from self._monitor_error
        log.info("Experiment run successfully.")

    def _record_failure(self, error: BaseException):
        """Log a monitor failure, store the first one and stop the other monitors."""
        log.warning("Monitor failed with: %s.", error)
        if self._monitor_error is None:
            self._monitor_error = error
        self.event.set()

    def monitor_failed(self) -> bool:
        """Check if a monitor failed; the first time, restore safe values."""
        if self._monitor_error is None:
            return False
        if not self._failure_handled:
            log.warning("Monitor failure, resetting the instruments.")
            self._failure_handled = True
            self.reset_instruments()
        return True
