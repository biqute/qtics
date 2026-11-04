"""Sources: RF generators and power supplies.

Optional capabilities (e.g. ``power`` of an RF source, ``current`` of a power
supply) are documented here and implemented only by the drivers supporting them.
"""

from abc import abstractmethod

from qtics.instruments.base import Instrument


class RFSource(Instrument):
    """RF signal generator.

    Optional: ``power`` [dBm].
    """

    @property
    @abstractmethod
    def frequency(self) -> float:
        """Output frequency in continuous wave mode [Hz]."""

    @property
    @abstractmethod
    def output(self) -> bool:
        """Whether the RF output is on."""


class PowerSupply(Instrument):
    """DC power supply.

    Optional: ``current`` [A], ``voltage_limit`` [V], ``current_limit`` [A],
    ``channel``.
    """

    @property
    @abstractmethod
    def voltage(self) -> float:
        """Output voltage [V]."""

    @property
    @abstractmethod
    def output(self) -> bool:
        """Whether the output is on."""
