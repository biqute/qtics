R&S®FSV3030 Spectrum Analyzer
=============================

Spectrum analyzer drivers for the FSV3030 series by Rohde & Schwarz.
This driver has been tested with the `FSV3030` spectrum analyzer. Documentation is available at `RS website <https://www.rohde-schwarz.com/it/prodotti/misura-e-collaudo/analizzatori-da-banco/rs-fsv3000-signal-and-spectrum-analyzer_63493-601503.html>`_.

Base class: :class:`qtics.instruments.base.SCPIInstrument` (socket transport, port 5025). It implements the :class:`qtics.instruments.types.SpectrumAnalyzer` interface.

Example of operation
---------------------

.. code-block:: python

  from qtics import FSV3030

  sa = FSV3030("192.168.40.12")
  sa.connect()

  sa.f_start, sa.f_stop = 4e9, 8e9
  sa.rbw = 1e3
  f, trace = sa.snapshot()  # single sweep, return (freqs, trace in dBm)

  # max-hold: start, sweep repeatedly, then read without resetting
  sa.set_max_hold()
  for _ in range(10):
      sa.sweep()
  max_trace = sa.read_max_hold()

Commands
""""""""
Other than featuring all the methods of :class:`qtics.instruments.base.SCPIInstrument` (``clear()``, ``wait()``, ``is_completed``), the :class:`qtics.instruments.rohde_schwarz.fsv3030.FSV3030` class contains the following methods and properties:

Functions
---------

- sweep(): Trigger a single sweep (switching continuous mode off) and wait until completion.
- autoscale(): Autoscale the display (reference level and range).
- read_trace_data(trace: int = 1) -> np.ndarray: Read the trace data in dBm, without sweeping.
- read_freqs() -> np.ndarray: Return frequency axis for current span.
- snapshot(trace: int = 1) -> tuple[np.ndarray, np.ndarray]: Perform single sweep and return (freqs, trace).
- marker_to_peak(marker: int = 1): Move marker to maximum peak.
- marker_freq(marker: int = 1) -> float: Query marker frequency in Hz.
- marker_power(marker: int = 1) -> float: Query marker power in dBm.
- set_max_hold(trace: int = 1): Set a trace to max-hold mode and start a sweep.
- clear_max_hold(trace: int = 1): Clear the max-hold trace (reset).
- read_max_hold(trace: int = 1) -> np.ndarray: Read the max-hold trace accumulated so far, without resetting it.

Properties
----------

- f_center: Center frequency in Hz.
- f_span: Frequency span in Hz.
- f_start: Start frequency in Hz.
- f_stop: Stop frequency in Hz.
- rbw: Resolution bandwidth in Hz.
- vbw: Video bandwidth in Hz.
- detector: Detector type (`POS`, `NEG`, `AVER`, `SAMP`, `RMS`).
- points: Number of sweep points.
- sweep_time: Sweep time in seconds.
- continuous: Whether the instrument sweeps continuously (bool).
- ref_level: Reference level in dBm.
