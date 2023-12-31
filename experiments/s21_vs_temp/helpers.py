"""HDF5 file helper for the S21 experiment."""

from datetime import datetime

import h5py
import matplotlib.pyplot as plt
import numpy as np

DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


class HDF5File:
    """HDF5 helper."""

    def __init__(self, path: str):
        """Read file, save indexes and temperatures."""
        self.f = h5py.File(path, "r")
        self.names = list(self.f)
        self.temps = [self.f[name].attrs["temperature"] for name in self.names]
        self.dates = [
            datetime.strptime(self.f[name].attrs["date"], DATE_FORMAT)
            for name in self.names
        ]

    def get_dataset(self, idx=None, temp=None):
        """Get a specific dataset/acqusition."""
        if idx and temp:
            raise RuntimeError("Specify only temp or idx.")
        if temp:
            idx = self.temps.index(temp)
        assert idx is not None
        return self.f[self.names[idx]]

    def plot_temp(self, temp: float, db=True):
        """Plot S21 Vs frequencies at a specific temperature."""
        dataset = self.get_dataset(temp=temp)
        x = np.array(dataset["frequencies"])
        y = np.array(dataset["values"])

        if db:
            plt.plot(x, 20 * np.log10(abs(y)))
            plt.ylabel("Magnitude S21 [dB]")
        else:
            plt.plot(x, abs(y))
            plt.ylabel("Magnitude S21 [au]")
        plt.xlabel("Frequencies [Hz]")

    def plot_s21_vs_temp(
        self, min_freq: float = 0.0, max_freq: float = 1.0e10, db: bool = True
    ):
        """Plot S21 Vs temperature. Data averaged in a range."""
        x = np.array(self.temps)
        y = []
        for idx in range(len(self.names)):
            vals = np.array(self.get_dataset(idx=idx)["values"])
            freqs = np.array(self.get_dataset(idx=idx)["values"])

            # this is not particularly nice
            vals = vals[min_freq > freqs]
            freqs = freqs[min_freq > freqs]
            vals = vals[max_freq < freqs]

            y.append(np.mean(np.abs(vals)))

        y = np.array(y)

        if db:
            plt.plot(x, 20 * np.log10(abs(y)))
            plt.ylabel("Magnitude S21 [dB]")
        else:
            plt.plot(x, abs(y))
            plt.ylabel("Magnitude S21 [au]")
        plt.xlabel("Frequencies [Hz]")
