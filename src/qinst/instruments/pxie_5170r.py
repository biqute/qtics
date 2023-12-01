"""PXiE 5170R NI driver."""

import niscope as ni

from qinst import log
from qinst.instrument import Instrument


class Pxie570R(Instrument):
    """Instrument class."""

    def __init__(self, name: str, address: str):
        """Initialize."""
        super().__init__(name, address)
        self.voltage_range = 1
        self.coupling = "DC"
        self.sample_rate = 250e9  # Samples per second

    def connect(self):
        """Empty method to comply with interface."""

    def disconnect(self):
        """Empty method to comply with interface."""

    def write(self):
        """Empty method to comply with interface."""

    def read(self):
        """Empty method to comply with interface."""

    def query(self):
        """Empty method to comply with interface."""

    @property
    def available(self):
        """Check if instrument is available."""
        try:
            with ni.Session(self.address) as _:
                return True
        except Exception as e:
            log.error(e)
            return False

    @property
    def voltage_range(self):
        """The voltage_range property."""
        return self._voltage_range

    @voltage_range.setter
    def voltage_range(self, value):
        self._voltage_range = value

    @property
    def coupling(self):
        """The coupling property."""
        return self._coupling

    @coupling.setter
    def coupling(self, value: str):
        # TODO: add validate
        mapping = {"AC": ni.VerticalCoupling.AC, "DC": ni.VerticalCoupling.DC}
        self._coupling = mapping[value]

    @property
    def sample_rate(self) -> int:
        """The sample_rate property."""
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value):
        self._sample_rate = int(value)

    def acquire(self, channels, duration, ref_position=50, options=None):
        """Perform an acquisition."""
        with ni.Session(self.address, options=options) as session:
            num_samples = int(duration * self.sample_rate)
            session.configure_vertical(range=self.voltage_range, coupling=self.coupling)
            session.configure_horizontal_timing(
                min_sample_rate=self.sample_rate,
                min_num_pts=num_samples,
                ref_position=ref_position,
                num_records=1,
                enforce_realtime=True,
            )
            return session.channels[channels].read(num_samples=num_samples)
