"""Base Instrument."""


class Instrument:
    """Base instrument class."""

    def __init__(self, name: str, address: str):
        """Initialize."""
        self.name = name
        self.address = address

    def connect(self):
        """Connect to the instrument."""
        raise NotImplementedError

    def disconnect(self):
        """Disonnect from the instrument."""
        raise NotImplementedError

    def write(self):
        """Send a command to the instrument."""
        raise NotImplementedError

    def read(self):
        """Read from the instrument."""
        raise NotImplementedError

    def query(self, _=None):
        """Send a command and read from the instrument."""
        raise NotImplementedError

    def get_id(self):
        """Return name of the device from SCPI standard query."""
        return self.query("*IDN?")
