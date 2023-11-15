class Instrument:
    def __init__(self, name: str, address: str, is_connected: bool = False):
        self.name = name
        self.address = address
        self.is_connected = is_connected

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def write(self):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError

    def query(self):
        raise NotImplementedError

    def get_id(self):
        """Return name of the device from SCPI standard query."""
        return self.query("*IDN?")
