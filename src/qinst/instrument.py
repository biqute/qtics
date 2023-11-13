class Instrument:
    def __init__(self, name, address, is_connected):
        self.name: str = name
        self.address: str = address
        self.is_connected: bool = False

    def connect():
        raise NotImplementedError

    def disconnect():
        raise NotImplementedError
