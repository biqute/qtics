Triton controller
=================

Controller of the Triton Cryostat by Oxford Instruments.

Base class: :class:`qtics.instruments.network_inst.NetworkInst`.

Example of opertations
""""""""""""""""""""""

.. code-block:: python

   from qtics import Triton

   controller = Triton("name", "address")
   controller.connect()

   print(f"Mixing chamber temp: {controller.get_mixing_chamber_temp()} mK")

   print(f"Set temperature: {controller.mixing_chamber_tset} mK")
   controller.mixing_chamber_tset = 60  # mK

Commands
""""""""

Functions
---------

* `get_mixing_chamber_temp()`
  Return the mixing chamber temperature in mK.

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
  Heater current range (readable; writable if `ENABLE_SETTERS=True`). Units: mA.

* `mixing_chamber_tset`
  Mixing chamber temperature setpoint in mK (readable; writable if `ENABLE_SETTERS=True`).
