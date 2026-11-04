"""Swept analyzers: vector network analyzers and spectrum analyzers.

Frequencies are in Hz, powers in dBm. ``f_start``, ``f_stop``, ``f_center`` and
``f_span`` are coupled: setting one changes the others.
"""

from abc import abstractmethod
from typing import Tuple

import numpy as np

from qtics.instruments.base import Instrument


class SweptInstrument(Instrument):
    """Instrument acquiring a trace over a frequency sweep."""

    @property
    @abstractmethod
    def f_start(self) -> float:
        """Start frequency of the sweep [Hz]."""

    @property
    @abstractmethod
    def f_stop(self) -> float:
        """Stop frequency of the sweep [Hz]."""

    @property
    @abstractmethod
    def f_center(self) -> float:
        """Center frequency of the sweep [Hz]."""

    @property
    @abstractmethod
    def f_span(self) -> float:
        """Frequency span of the sweep [Hz]."""

    @property
    @abstractmethod
    def points(self) -> int:
        """Number of points of the sweep."""

    @property
    @abstractmethod
    def continuous(self) -> bool:
        """Whether the instrument sweeps continuously."""

    @abstractmethod
    def sweep(self):
        """Perform a single sweep and wait for its completion."""

    @abstractmethod
    def read_freqs(self) -> np.ndarray:
        """Read the frequencies of the trace points [Hz]."""

    @abstractmethod
    def read_trace_data(self) -> np.ndarray:
        """Read the data of the current trace."""

    def snapshot(self) -> Tuple[np.ndarray, np.ndarray]:
        """Perform a single sweep and return (frequencies, trace)."""
        self.sweep()
        return self.read_freqs(), self.read_trace_data()


class VNA(SweptInstrument):
    """Vector network analyzer."""

    @property
    @abstractmethod
    def power(self) -> float:
        """Output power [dBm]."""

    @property
    @abstractmethod
    def ifbw(self) -> float:
        """Intermediate frequency bandwidth [Hz]."""

    @property
    @abstractmethod
    def s_parameter(self) -> str:
        """Measured scattering parameter, e.g. "S21"."""

    @property
    @abstractmethod
    def averages(self) -> int:
        """Number of sweeps averaged."""


class SpectrumAnalyzer(SweptInstrument):
    """Spectrum analyzer."""

    @property
    @abstractmethod
    def rbw(self) -> float:
        """Resolution bandwidth [Hz]."""
