"""Base Instrument."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Union

from qtics import log


class Instrument(ABC):
    """Base instrument class."""

    def __init__(self, name: str, address: str):
        """Initialize."""
        self.name = name
        self.address = address
        self._defaults: Dict[str, Any] = {}

    @abstractmethod
    def connect(self):
        """Connect to the instrument."""

    @abstractmethod
    def disconnect(self):
        """Disconnect from the instrument."""

    @abstractmethod
    def write(self, cmd, sleep=False):
        """Send a command to the instrument."""

    @abstractmethod
    def read(self):
        """Read from the instrument."""

    @abstractmethod
    def query(self, cmd) -> str:
        """Send a command and read from the instrument."""

    def get_id(self):
        """Return name of the device from SCPI standard query."""
        return self.query("*IDN?")

    def reset(self, defaults=True):
        """Reset device with SCPI standard command."""
        self.write("*RST")
        if defaults:
            self.set_defaults()

    def set(self, **kwargs):
        """Set multiple attributes and/or properties."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise RuntimeError(f"The instrument does not have the {key} parameter.")

    def get(self, *args) -> dict:
        """Get multiple attributes and/or properties."""
        values = {}
        for key in args:
            if hasattr(self, key):
                values[key] = getattr(self, key)
            else:
                raise RuntimeError(f"The instrument does not have the {key} parameter.")
        return values

    @staticmethod
    def validate_opt(opt: Union[str, int], allowed: tuple):
        """Check if provided option is between allowed ones."""
        if opt not in allowed:
            raise RuntimeError(f"Invalid option provided, choose between {allowed}")

    @staticmethod
    def validate_range(n, n_min, n_max):
        """Check if provided number is in allowed range."""
        if not n_min <= n <= n_max:
            valid = max(n_min, min(n_max, n))
            log.warning(
                f"Provided value {n} not in range ({n_min}, {n_max}), will be set to {valid}."
            )
            return valid
        return n

    @property
    def defaults(self) -> dict:
        """Default values for the instrument attributes."""
        return self._defaults

    def update_defaults(self, **kwargs):
        """Validate and update the defaults dictionary."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                self._defaults[key] = value
            else:
                raise RuntimeError(f"The instrument does not have the {key} parameter.")

    def clear_defaults(self):
        """Clear the defaults dictionary."""
        self._defaults = {}

    def set_defaults(self, **kwargs):
        """Set the specified default values."""
        if kwargs:
            self.update_defaults(**kwargs)
        if self.defaults:
            self.set(**self.defaults)
