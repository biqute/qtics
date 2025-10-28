"""Simple Spectrum snapshot for minimal driver testing."""

import matplotlib.pyplot as plt

from qtics import FSV3030

IP_ADDRESS = "169.254.101.32"
sa = FSV3030(name="FSV3030", address=IP_ADDRESS, port=5025, timeout=10000)

sa.connect()

sa.f_start = 0
sa.f_stop = 10e9

# Bandwidth 1 MHz
sa.rbw = 1e6
sa.vbw = 1e6

sa.sweep_points = 1001

sa.continuous(False)  # single sweep mode

freqs, trace = sa.snapshot()
plt.plot(freqs, trace)
plt.show()
