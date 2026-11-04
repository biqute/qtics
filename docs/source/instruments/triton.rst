Triton controller
=================

Controller of the Triton Cryostat by Oxford Instruments.

Base class: :class:`qtics.instruments.base.MessageInstrument` (TCP socket transport, default port 33576).
The address of the cryostat is required, there is no default. Transport options (``port``, ``timeout``,
``delay``, ``no_delay``) can be passed as keyword arguments, or a ready transport can be given instead of the address.

Example of opertations
""""""""""""""""""""""

.. code-block:: python

   from qtics import Triton

   controller = Triton("192.168.1.10")  # address of the cryostat
   controller.connect()

   print(f"Mixing chamber temp: {controller.get_mixing_chamber_temp() * 1000} mK")

   print(f"Set temperature: {controller.mixing_chamber_tset*1000} mK")
   controller.mixing_chamber_tset = 0.06  # setter must be enabled, see below
   controller.disconnect()

Commands
""""""""

Functions
---------

* `get_mixing_chamber_temp()`
  Return the mixing chamber temperature in K.

* `get_still_temp()`
  Return the still temperature in K.

* `get_cool_temp()`
  Return the cold plate (CP) temperature in K.

* `get_pt1_temp()`
  Return the 1st stage pulse tube temperature in K.

* `get_pt2_temp()`
  Return the 2nd stage pulse tube temperature in K.

* `get_sorb_temp()`
  Return the sorption pump temperature in K.

* `get_state()`
  Return the general state of the cryostat.

* `get_action()`
  Return the current operational action of the cryostat (e.g., "Precooling", "Condensing", "Circulating").

Properties
----------

* `heater_range`
  Mixing chamber heater range in A, one of `HEATER_RANGES` (readable; writable if
  `ENABLE_SETTERS=True`).

* `mixing_chamber_tset`
  Mixing chamber temperature setpoint in K (readable; writable if `ENABLE_SETTERS=True`,
  up to `MAX_TSET` = 0.2 K).
