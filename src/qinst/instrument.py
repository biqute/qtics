"""Base Instrument."""

from abc import ABC, abstractmethod


class Instrument(ABC):
    """Base instrument class."""

    def __init__(self, name: str, address: str):
        """Initialize."""
        self.name = name
        self.address = address

    @abstractmethod
    def connect(self):
        """Connect to the instrument."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self):
        """Disonnect from the instrument."""
        raise NotImplementedError

    @abstractmethod
    def write(self):
        """Send a command to the instrument."""
        raise NotImplementedError

    @abstractmethod
    def read(self):
        """Read from the instrument."""
        raise NotImplementedError

    @abstractmethod
    def query(self, _=None):
        """Send a command and read from the instrument."""
        raise NotImplementedError

    def get_id(self):
        """Return name of the device from SCPI standard query."""
        return self.query("*IDN?")

    def reset(self):
        """Reset device with SCPI standard command."""
        return self.query("*RST")

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
