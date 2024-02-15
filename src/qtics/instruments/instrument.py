"""Base Instrument."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Union

from qtics import log


class Instrument(ABC):
    """Base instrument class."""

    def __init__(self, name: str, address: str):
        """Initialize.

        :param name: identifier of the instrument
        :param address: ip address of the instrument
        """
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

    def reset(self, defaults: bool = True):
        """Reset device with SCPI standard command.

        :param defaults: if true set default values after reset
        """
        self.write("*RST")
        if defaults:
            self.set_defaults()

    def set(self, **kwargs):
        """Set multiple attributes and/or properties.

        :param kwargs: parameters and values to set
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise RuntimeError(f"The instrument does not have the {key} parameter.")

    def get(self, *args) -> dict:
        """Get multiple attributes and/or properties.

        :param args: parameters to get
        """
        values = {}
        for key in args:
            if hasattr(self, key):
                values[key] = getattr(self, key)
            else:
                raise RuntimeError(f"The instrument does not have the {key} parameter.")
        return values

    @staticmethod
    def validate_opt(opt: Union[str, int], allowed: tuple):
        """Check if provided option is between allowed ones.

        :param opt: chosen option
        :param allowed: tuple of the allowed options
        """
        if opt not in allowed:
            raise RuntimeError(f"Invalid option provided, choose between {allowed}")

    @staticmethod
    def validate_range(n, n_min, n_max):
        """Check if provided number is in allowed range.

        :param n: provided number
        :param n_min: minimum value allowed
        :param n_max: maximum value allowed

        :return: n if is valid, otherwise n_max/n_min
        """
        if not n_min <= n <= n_max:
            valid = max(n_min, min(n_max, n))
            log.warning(
                f"Provided value {n} not in range ({n_min}, {n_max}), will be set to {valid}."
            )
            return valid
        return n

    @property
    def defaults(self) -> dict:
        """Return default values for the instrument attributes."""
        return self._defaults

    def update_defaults(self, **kwargs):
        """Validate and update the defaults dictionary.

        :param kwargs: dictionary of default parameters and values
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                self._defaults[key] = value
            else:
                raise RuntimeError(f"The instrument does not have the {key} parameter.")

    def clear_defaults(self):
        """Clear the defaults dictionary."""
        self._defaults = {}

    def set_defaults(self, **kwargs):
        """Set the specified default values.

        :param kwargs: dictionary of default parameters and values
        """
        if kwargs:
            self.update_defaults(**kwargs)
        if self.defaults:
            self.set(**self.defaults)
