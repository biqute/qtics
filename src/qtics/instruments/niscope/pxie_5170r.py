"""PXiE 5170R NI driver."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import niscope as ni

from qtics import log
from qtics.instruments import Instrument


@dataclass
class Trigger(ABC):
    """Abstract trigger object."""

    source: Optional[str]
    """Source of the trigger."""

    @abstractmethod
    def configure(self, session: ni.Session):
        """Configure session."""
        raise NotImplementedError


@dataclass
class DigitalTrigger(Trigger):
    """Digital trigger class."""

    slope: ni.TriggerSlope = ni.TriggerSlope.POSITIVE
    """Activation slope of the trigger."""
    holdoff: float = 0.0
    """Waiting time before trigger [s]."""
    delay: float = 0.0
    """Delay between trigger and acquisition."""

    def configure(self, session: ni.Session):
        """Configure a session."""
        session.configure_trigger_digital(
            trigger_source=self.source,
            slope=self.slope,
            holdoff=self.holdoff,
            delay=self.delay,
        )


@dataclass
class EdgeTrigger(Trigger):
    """Edge trigger class."""

    slope: ni.TriggerSlope = ni.TriggerSlope.POSITIVE
    """Activation slope of the trigger."""
    holdoff: float = 0.0
    """Waiting time before trigger [s]."""
    delay: float = 0.0
    """Delay between trigger and acquisition."""
    level: float = 1.0
    """Voltage threshold."""
    trigger_coupling: ni.TriggerCoupling = ni.TriggerCoupling.DC

    def configure(self, session: ni.Session):
        """Configure a session."""
        session.configure_trigger_edge(
            trigger_source=self.source,
            trigger_coupling=self.trigger_coupling,
            slope=self.slope,
            holdoff=self.holdoff,
            delay=self.delay,
            level=self.level,
        )


@dataclass
class SoftwareTrigger(Trigger):
    """Software trigger class."""

    holdoff: float = 0.0
    """Waiting time before trigger [s]."""
    delay: float = 0.0
    """Delay between trigger and acquisition."""
    source = None
    """Overwrite source property."""

    def configure(self, session: ni.Session):
        """Configure a session."""
        session.configure_trigger_software(
            holdoff=self.holdoff,
            delay=self.delay,
        )


class Pxie570R(Instrument):
    """Instrument class."""

    def __init__(self, name: str, address: str):
        """Initialize."""
        super().__init__(name, address)
        self.voltage_range = 1
        self.coupling = "DC"
        self.sample_rate = int(250e9)  # Samples per second
        self.trigger = DigitalTrigger("ch1")  # TODO check this is reasonable

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

    @property
    def trigger(self):
        """The trigger property."""
        return self._trigger

    @trigger.setter
    def trigger(self, value: Trigger):
        self._trigger = value

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
            if self.trigger:
                self.trigger.configure(session)
            return session.channels[channels].read(num_samples=num_samples)
