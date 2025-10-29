R&S®FSV3030 Spectrum Analyzer
=============================

Spectrum analyzer drivers for the FSV3030 series by Rohde & Schwarz.
This driver has been tested with the `FSV3030` spectrum analyzer. Documentation is available at `RS website <https://www.rohde-schwarz.com/it/prodotti/misura-e-collaudo/analizzatori-da-banco/rs-fsv3000-signal-and-spectrum-analyzer_63493-601503.html>`_.

Base class: :class:`qtics.instruments.network_inst.NetworkInst`.

Commands
""""""""
Other than featuring all the methods of :class:`qtics.instruments.network_inst.NetworkInst`, the base :class:`qtics.instruments.network.RSFsv3030.FSV3030` class contains the following methods and properties:

Functions
---------

- clear(): Clear error queue and status registers.
- wait(): Wait until all commands are processed.
- single_sweep(): Trigger a single sweep and wait until completion.
- continuous(state: bool = True): Enable or disable continuous sweep mode.
- autoscale(): Autoscale the display (reference level and range).
- read_trace_data(trace: int = 1) -> np.ndarray: Read the trace data in dBm.
- read_freqs() -> np.ndarray: Return frequency axis for current span.
- snapshot(trace: int = 1) -> tuple[np.ndarray, np.ndarray]: Perform single sweep and return (freqs, trace).
- marker_to_peak(marker: int = 1): Move marker to maximum peak.
- marker_freq(marker: int = 1) -> float: Query marker frequency in Hz.
- marker_power(marker: int = 1) -> float: Query marker power in dBm.
- set_max_hold(trace: int = 1): Set a trace to max-hold mode.
- clear_max_hold(trace: int = 1): Clear the max-hold trace (reset).
- read_max_hold(trace: int = 1) -> np.ndarray: Acquire current max-hold trace data.

Properties
----------

- f_center: Center frequency in Hz.
- f_span: Frequency span in Hz.
- f_start: Start frequency in Hz.
- f_stop: Stop frequency in Hz.
- rbw: Resolution bandwidth in Hz.
- vbw: Video bandwidth in Hz.
- detector: Detector type (`POS`, `NEG`, `AVER`, `SAMP`, `RMS`, etc.).
- sweep_points: Number of sweep points.
- sweep_time: Sweep time in seconds.
- ref_level: Reference level in dBm.
- is_completed: Boolean indicating if the last operation is complete.
