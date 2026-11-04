"""Driver of the Kratos 3494-64 attenuator, controlled by an Arduino."""

from qtics.instruments.base import SCPIInstrument
from qtics.transport import SerialTransport, Transport


class Kratos3494Attenuator(SCPIInstrument):
    """Control for the latching RF attenuator."""

    default_transport = SerialTransport
    transport_defaults = {
        "baudrate": 9600,
        "terminator": "\n",
        "delay": 0.1,
        "timeout": 5,
    }

    def __init__(
        self,
        transport: Transport | str,
        name: str = "Attenuator349464",
        **transport_kwargs,
    ):
        """Initialize."""
        super().__init__(transport, name, **transport_kwargs)
        self._attenuation: float = 0.0

    @property
    def attenuation(self) -> float:
        """The attenuation in dB."""
        # The firmware answers "<value>\tdB"
        return float(self.query("ATT?").split()[0])

    @attenuation.setter
    def attenuation(self, value: float):
        self._attenuation = round(value, 2)
        self.write(f"ATT {value}")

    def get_pins_state(self):
        """Get status of digital arduino pins."""
        return self.query("DIG:PIN?")
