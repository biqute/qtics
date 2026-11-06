NI PXIe-5170R Oscilloscope
==========================

PXIe-5170R reconfigurable oscilloscope by National Instruments (4 or 8 channels,
14 bit, up to 250 MS/s). The driver uses the NI-SCOPE Python API: install the
``niscope`` extra (``pip install "qtics[niscope]"``) and the NI-SCOPE driver from NI.
Documentation of the API is available at
`nimi-python <https://nimi-python.readthedocs.io/en/master/niscope.html>`_.

Base class: :class:`qtics.instruments.base.Instrument`.

The address is the NI resource name of the module (e.g. ``"PXI1Slot2"``, see NI MAX).
The driver keeps no open session: ``connect()`` and ``disconnect()`` do nothing, and
each :meth:`~qtics.instruments.ni.pxie5170r.Pxie5170R.acquire` opens a session,
configures it with the current settings, reads and closes it.

Example of operations
"""""""""""""""""""""

.. code-block:: python

   from qtics import Pxie5170R
   from qtics.instruments.ni.pxie5170r import EdgeTrigger

   scope = Pxie5170R("PXI1Slot2")
   print(scope.available)          # True if a session can be opened

   scope.voltage_range = 1         # V, peak-to-peak
   scope.coupling = "DC"           # "AC" or "DC"
   scope.sample_rate = 250e6       # S/s
   scope.trigger = EdgeTrigger("0", level=0.2)  # None: immediate trigger

   waveforms = scope.acquire("0,1", duration=10e-6, ref_position=50)
   for wfm in waveforms:
       print(wfm.channel, len(wfm.samples), wfm.x_increment)

``acquire(channels, duration, ref_position=50, options=None)`` returns the list of
``niscope.WaveformInfo`` of the channels (a channel string as accepted by NI-SCOPE,
e.g. ``"0"``, ``"0,1"`` or ``"0-3"``); each has the samples in V in ``samples``.
``ref_position`` is the trigger position in percent of the record, ``options`` is
passed to ``niscope.Session`` (e.g. ``{"simulate": True, "driver_setup": {"Model":
"5170R (4CH)"}}`` to run without hardware).

Triggers
""""""""

The triggers are dataclasses in :mod:`qtics.instruments.ni.pxie5170r`, assigned to
``scope.trigger``:

- ``SoftwareTrigger(holdoff=0.0, delay=0.0)``
- ``DigitalTrigger(source, slope=POSITIVE, holdoff=0.0, delay=0.0)``
- ``EdgeTrigger(source, slope=POSITIVE, holdoff=0.0, delay=0.0, level=1.0,
  trigger_coupling=DC)``

Slopes and couplings are ``niscope.TriggerSlope`` and ``niscope.TriggerCoupling``,
times are in s and the level in V.

Commands
""""""""

Properties
----------

- voltage_range
- coupling
- sample_rate
- trigger
- available (read only)

Functions
---------

- acquire(channels, duration, ref_position=50, options=None)
