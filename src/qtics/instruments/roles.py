"""Protocols defining the methods and properties the instrument drivers must satisfy
to be usable by experiments interchangeably.

A driver conforms by implementing the members below; no inheritance is
required, so these are compatible with any transport base class
(``NetworkInst``, ``SerialInst``, ``GpibInst``).

Check conformance with::

    conforms(RSZNB, VNA)              # class-level, safe on live drivers
    missing_members(RSZNB, VNA)       # names still to implement
    def f(vna: VNA): ...              # static, signatures too

Prefer :func:`conforms` over ``isinstance``: ``isinstance`` calls ``hasattr``
on the *instance*, which executes property getters and therefore talks to the
hardware (and raises if the instrument is not connected).  The helpers below
inspect the class instead.
"""

import inspect
import re
from functools import lru_cache
from typing import Any, Dict, List, Protocol, Tuple, runtime_checkable

import numpy as np

__all__ = [
    "InstrumentLike",
    "VNA",
    "TimeDomainVNA",
    "Pump",
    "Bias",
    "SpectrumAnalyzer",
    "ResistanceBridge",
    "protocol_members",
    "missing_members",
    "conforms",
    "check_role",
]


@runtime_checkable
class InstrumentLike(Protocol):
    """Members every driver must expose, whatever its role."""

    name: str
    address: str

    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def write(self, cmd: str, sleep: bool = False) -> None: ...

    def read(self) -> str: ...

    def query(self, cmd: str) -> str: ...

    def get_id(self) -> str: ...

    def reset(self, defaults: bool = True) -> None: ...

    def set(self, **kwargs: Any) -> None: ...

    def get(self, *args: str) -> Dict[str, Any]: ...

    def set_defaults(self, **kwargs: Any) -> None: ...

    def update_defaults(self, **kwargs: Any) -> None: ...


@runtime_checkable
class VNA(InstrumentLike, Protocol):
    """Vector network analyzer (``self.vna``).

    Implemented by ``RSZNB`` and ``VNAN9916A``.
    """

    s_par: str
    f_min: float
    f_max: float
    f_center: float
    f_span: float
    sweep_points: int
    average: int
    IFBW: float
    power: float
    yformat: str

    def setup(self, s_par: str = "S21") -> None:
        """Put the instrument in a known measurement state."""

    def sweep(self) -> None:
        """Run a frequency sweep honouring averaging and trigger mode."""

    def read_freqs(self) -> np.ndarray:
        """Frequency axis of the current sweep."""

    def read_trace_data(self, yformat: Any = None) -> np.ndarray:
        """Complex S-parameter data, or formatted data if ``yformat`` given."""

    def snapshot(self, **kwargs: Any) -> Tuple[np.ndarray, np.ndarray]:
        """Single sweep returning ``(frequencies, values)``."""

    def clear_average(self) -> None: ...

    def autoscale(self) -> None: ...


@runtime_checkable
class TimeDomainVNA(VNA, Protocol):
    """VNA with the time-domain option, required by TDR experiments."""

    time_domain: str
    t_min: float
    t_max: float
    time_domain_window: str
    harmonic_grid: str
    low_pass_extrapolation: float
    low_pass_stimulus: str

    def read_times(self) -> np.ndarray:
        """Time axis of the current time-domain trace."""


@runtime_checkable
class Pump(InstrumentLike, Protocol):
    """RF signal generator driving a pump tone (``self.pump``, ``self.pump_iso``).

    Implemented by ``SMA100B`` and ``VALON5019``.
    """

    f_fixed: float
    p_fixed: float
    rf_status: str


@runtime_checkable
class Bias(InstrumentLike, Protocol):
    """DC source biasing the device (``self.bias``).

    Implemented by ``SIM928`` and ``Keithley2231A``.
    """

    voltage: float

    def output_on(self) -> None: ...

    def output_off(self) -> None: ...


@runtime_checkable
class SpectrumAnalyzer(InstrumentLike, Protocol):
    """Spectrum analyzer (``self.spectrum``).

    Implemented by ``FSV3030``.
    """

    f_center: float
    f_span: float
    f_start: float
    f_stop: float
    rbw: float
    vbw: float
    detector: str
    sweep_points: int
    sweep_time: float
    average: int
    ref_level: float

    def setup(self) -> None:
        """Put the instrument in single-sweep mode with a clean trace."""

    def single_sweep(self) -> None:
        """Trigger one sweep and block until it completes."""

    def read_freqs(self) -> np.ndarray: ...

    def read_trace_data(self, trace: int = 1) -> np.ndarray: ...

    def snapshot(self, **kwargs: Any) -> Tuple[np.ndarray, np.ndarray]:
        """Single sweep returning ``(frequencies, values)``."""


@runtime_checkable
class ResistanceBridge(InstrumentLike, Protocol):
    """Resistance bridge with temperature control (``self.bridge``).

    Implemented by ``AVS47IB``.
    """

    channel: int
    range: int
    excitation: int
    heater_range: int
    set_point: int

    def measure(self) -> float:
        """Trigger a conversion and return resistance in Ohms."""

    def read_temperature(self) -> float:
        """Resistance converted to Kelvin via the thermometer calibration."""

    def set_temperature(self, temperature: float) -> None:
        """Command the controller to a target temperature in Kelvin."""


# ----------------------------------------------------------------------
# Conformance helpers
# ----------------------------------------------------------------------


def protocol_members(protocol: type) -> List[str]:
    """Public members a driver must provide to satisfy *protocol*."""
    members = set()
    for base in protocol.__mro__:
        if base is object or getattr(base, "__module__", "") == "typing":
            continue
        members.update(getattr(base, "__annotations__", {}))
        members.update(k for k in vars(base) if not k.startswith("_"))
    return sorted(members)


def missing_members(driver: Any, protocol: type) -> List[str]:
    """Members of *protocol* that *driver* (class or instance) lacks.

    Members are looked up on the class, then in the instance ``__dict__`` for
    attributes assigned in ``__init__``.  Neither lookup invokes a descriptor,
    so property getters never reach the hardware.
    """
    is_class = isinstance(driver, type)
    cls = driver if is_class else type(driver)
    known = set(getattr(driver, "__dict__", {})) if not is_class else set()
    known |= _init_attributes(cls)
    return [
        m for m in protocol_members(protocol) if not hasattr(cls, m) and m not in known
    ]


@lru_cache(maxsize=None)
def _init_attributes(cls: type) -> frozenset:
    """Names assigned as ``self.<name> = ...`` in any ``__init__`` of *cls*.

    Lets a class be checked before instantiation even though members such as
    ``name`` and ``address`` only exist on instances.  Best effort: returns an
    empty set when the source is unavailable.
    """
    names: set = set()
    for base in cls.__mro__:
        init = vars(base).get("__init__")
        if init is None:
            continue
        try:
            source = inspect.getsource(init)
        except (OSError, TypeError):
            continue
        names.update(re.findall(r"self\.(\w+)\s*(?::[^=]+)?=", source))
    return frozenset(names)


def conforms(driver: Any, protocol: type) -> bool:
    """True if *driver* implements every member of *protocol*."""
    return not missing_members(driver, protocol)


def check_role(driver: Any, protocol: type, role: str = "") -> None:
    """Raise ``TypeError`` listing what *driver* is missing for *protocol*."""
    missing = missing_members(driver, protocol)
    if missing:
        cls = driver if isinstance(driver, type) else type(driver)
        where = f" as '{role}'" if role else ""
        raise TypeError(
            f"{cls.__name__} cannot be used{where}: it does not satisfy "
            f"{protocol.__name__}. Missing members: {', '.join(missing)}."
        )
