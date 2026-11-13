Triton controller
=================

Controller of the Triton Cryostat by Oxford Instruments.

Base class: :class:`qtics.instruments.network_inst.NetworkInst`.

Example of opertations
""""""""""""""""""""""

.. code-block:: python

   from qtics import Triton

   controller = Triton("name", "address")

   print(f"Mixing chamber temp: {controller.get_mixing_chamber_temp()} mK")

   print(f"Set temperature: {controller.mixing_chamber_tset} mK")
   controller.mixing_chamber_tset = 60  # mK

Commands
""""""""

Functions
---------

- get_mixing_chamber_temp()

Properties
----------

- mixing_chamber_ch
- heater_range
- mixing_chamber_tset
