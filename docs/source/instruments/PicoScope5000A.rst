PicoScope 5000 Series oscilloscopes
===================================

Driver for the PicoScope 5000 Series (A API: 5000A, 5000B and 5000D), tested on the
4-channel USB oscilloscope PicoScope 5444D with flexible resolution (8 to 16 bit).
The programmer's guide ("PicoScope 5000 Series (A API) Programmer's Guide") and the
other manuals are available at `Pico Technology <https://www.picotech.com/downloads>`_.

The driver calls the ``ps5000a`` C library of the PicoSDK through ``ctypes``: install
the `PicoSDK <https://www.picotech.com/downloads>`_ (``libps5000a.so`` on Linux,
``ps5000a.dll`` on Windows), no Python package is needed. The library is searched in
the usual places (including ``/opt/picoscope/lib``), or its path can be given with the
``library`` argument.

Base class: :class:`qtics.instruments.base.Instrument`. Errors of the PicoSDK raise
``RuntimeError`` (``PicoError``) with the name of the status code, e.g.
``PICO_NOT_FOUND``. If the AC adaptor of a 4-channel unit is not connected, the unit
runs on USB power with channels A and B only.

Example of operation
""""""""""""""""""""

Capture 1000 samples every 1 us on channel A (range +-1 V), triggering on a rising
edge at 0.2 V, or after 100 ms anyway.

.. code-block:: python

  from qtics import PicoScope5000A

  scope = PicoScope5000A()  # or PicoScope5000A(serial="...", resolution=12)
  scope.connect()
  scope.set_channel("A", range_v=1.0, coupling="DC")
  scope.set_channel("B", enabled=False)
  scope.set_timebase(1e-6, 1000)
  scope.set_trigger("A", 0.2, direction="RISING", auto_trigger_ms=100)

  time, data = scope.acquire(pre_trigger=100e-6)  # time [s], data["A"] [V]
  time, data = scope.acquire(averages=16)  # software average of 16 captures

  # 5 triggered waveforms in a row (rapid block mode), data["A"].shape == (5, 1000)
  time, data = scope.acquire_segments(5)

  scope.disconnect()

Notes
-----
- The input range is the smallest of +-10 mV, 20 mV, 50 mV, 100 mV, 200 mV, 500 mV,
  1 V, 2 V, 5 V, 10 V and 20 V that contains the requested ``range_v``.
- The API cannot read back the channel settings: the driver keeps them in
  ``channels`` and applies them again on connect and when the resolution changes.
- At 15 bit only two channels can be enabled, at 16 bit only one. The fastest
  sampling intervals also need few enabled channels, so set the channels before
  ``set_timebase``. If the fastest timebases are not valid for the enabled channels,
  the next valid one is used.
- The trigger level is the voltage at the input: it is converted to ADC counts with
  the range and the offset of the trigger channel.
- Voltages are ``counts / max_adc * range - offset``, with the maximum ADC count of
  the current resolution.
- ``acquire`` waits at most ``timeout`` seconds for the trigger, then stops the capture
  and raises ``TimeoutError``: without auto trigger a signal is needed.
- The built-in signal generator, streaming mode, ETS and the digital ports of the MSO
  models are not supported.

Commands
""""""""

Functions
---------
- connect()
- disconnect()
- set_channel(channel, enabled, range_v, coupling, offset)
- set_timebase(sample_interval, n_samples)
- set_trigger(source, level_v, direction, delay, auto_trigger_ms, enabled)
- acquire(channels, timeout, pre_trigger, averages)
- acquire_segments(n_captures, channels, timeout, pre_trigger)

Properties
----------
- is_connected
- resolution
- channels
- timebase
- sample_interval
- n_samples
- trigger
