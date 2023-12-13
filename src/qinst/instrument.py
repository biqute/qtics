"""Base Instrument."""

from abc import ABC, abstractmethod
from typing import Union

from qinst import log


class Instrument(ABC):
    """Base instrument class."""

    def __init__(self, name: str, address: str):
        """Initialize."""
        self.name = name
        self.address = address
        self.__safe_options: dict = {}

    @abstractmethod
    def connect(self):
        """Connect to the instrument."""

    @abstractmethod
    def disconnect(self):
        """Disonnect from the instrument."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Get connection status."""

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

    def reset(self):
        """Reset device with SCPI standard command."""
        return self.write("*RST")

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

    def set_safe_options(self, **kwargs):
        """Set multiple fallback attributes/properties."""
        self.__safe_options = {}
        for key, value in kwargs.items():
            if hasattr(self, key):
                self.__safe_options[key] = value
            else:
                raise RuntimeError(f"The instrument does not have the {key} parameter.")

    def get_safe_options(self) -> dict:
        """Get fallback attributes/properties."""
        return self.__safe_options

    def safe_reset(self):
        """Reset to standard or specified safe options."""
        log.debug(f"Setting safe parameters for instrument {self.name}.")
        if not self.__safe_options:
            self.reset()
        else:
            self.set(**self.__safe_options)

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
