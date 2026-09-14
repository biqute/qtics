"""
Ruthenium oxide (RuOx) thermometer calibration.

Loads a two-column Lake Shore .dat calibration file (Temperature / Resistance)
and provides resistance-to-temperature conversion via monotonic cubic
interpolation.
"""

from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator


class RuOx:
    """Resistance-to-temperature conversion for a RuOx thermometer.

    Reads a Lake Shore calibration file with two columns (Temperature in K,
    Resistance in Ohms), skipping the 3-line header.  Since resistance
    decreases monotonically with temperature, the interpolator is built on
    the reversed arrays so that it operates on an increasing sequence.

    Parameters
    ----------
    cal_file:
        Path to the ``.dat`` calibration file supplied by Lake Shore.
    name:
        Optional label (e.g. serial number).  Defaults to the file stem.

    Raises
    ------
    FileNotFoundError
        If *cal_file* does not exist.
    ValueError
        If the file cannot be parsed or contains fewer than 2 data points.

    Examples
    --------
    >>> thermometer = RuOx("calibration/U08585.dat")
    >>> thermometer.resistance_to_temperature(2134.06)   # → ~1.2 K
    """

    def __init__(self, cal_file: str | Path, name: str | None = None):
        cal_file = Path(cal_file)
        if not cal_file.exists():
            raise FileNotFoundError(f"Calibration file not found: {cal_file}")

        self.cal_file = cal_file
        self.name = name or cal_file.stem

        # Load: skip the 3-line header (2 label lines + 1 blank line)
        data = np.loadtxt(cal_file, skiprows=3)
        if data.ndim != 2 or data.shape[1] < 2 or len(data) < 2:
            raise ValueError(f"Could not parse calibration data from {cal_file}")

        # Columns: temperature (K), resistance (Ω)
        # Resistance decreases with temperature, so reverse for a monotonically
        # increasing sequence required by the interpolator.
        temperature = data[:, 0]
        resistance = data[:, 1]

        self._r_min = float(resistance.min())
        self._r_max = float(resistance.max())
        self._t_min = float(temperature.min())
        self._t_max = float(temperature.max())

        # R → T interpolator (reversed so R is increasing)
        self._interp_r2t = PchipInterpolator(resistance[::-1], temperature[::-1])
        # T → R interpolator (temperature is already increasing)
        self._interp_t2r = PchipInterpolator(temperature, resistance)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def temperature_range(self) -> tuple[float, float]:
        """Calibrated temperature range (T_min, T_max) in Kelvin."""
        return self._t_min, self._t_max

    @property
    def resistance_range(self) -> tuple[float, float]:
        """Calibrated resistance range (R_min, R_max) in Ohms."""
        return self._r_min, self._r_max

    def resistance_to_temperature(self, resistance: float) -> float:
        """Convert a measured resistance to temperature in Kelvin.

        Parameters
        ----------
        resistance:
            Measured resistance in Ohms.

        Returns
        -------
        float
            Temperature in Kelvin.

        Raises
        ------
        ValueError
            If *resistance* is outside the calibrated range.
        """
        if not (self._r_min <= resistance <= self._r_max):
            raise ValueError(
                f"Resistance {resistance:.1f} Ω is outside the calibrated "
                f"range [{self._r_min:.1f}, {self._r_max:.1f}] Ω "
                f"({self.name})."
            )
        return float(self._interp_r2t(resistance))

    def temperature_to_resistance(self, temperature: float) -> float:
        """Convert a target temperature to the expected resistance in Ohms.

        Parameters
        ----------
        temperature:
            Target temperature in Kelvin.

        Returns
        -------
        float
            Expected resistance in Ohms.

        Raises
        ------
        ValueError
            If *temperature* is outside the calibrated range.
        """
        if not (self._t_min <= temperature <= self._t_max):
            raise ValueError(
                f"Temperature {temperature:.4f} K is outside the calibrated "
                f"range [{self._t_min:.4f}, {self._t_max:.1f}] K "
                f"({self.name})."
            )
        return float(self._interp_t2r(temperature))

    def __repr__(self) -> str:
        return (
            f"RuOx({self.name!r}, "
            f"T=[{self._t_min:.3f}, {self._t_max:.1f}] K, "
            f"R=[{self._r_min:.0f}, {self._r_max:.0f}] Ω)"
        )
