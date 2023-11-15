class Instrument:
    def __init__(self, name: str, address: str):
        self.name = name
        self.address = address

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def get_id(self):
        raise NotImplementedError
