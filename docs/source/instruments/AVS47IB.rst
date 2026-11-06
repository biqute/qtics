Resistance bridge Picowatt AVS-47B (AVS47-IB interface)
=======================================================

AC resistance bridge AVS-47B produced by Picowatt, controlled through its AVS47-IB
GPIB interface. The bridge also forwards commands to the optional TS-530A
temperature controller, when the two units are connected.

Base class: :class:`qtics.instruments.base.SCPIInstrument` (GPIB transport, see
:class:`qtics.transport.gpib.GPIBTransport`; the GPIB driver must be installed, see
:ref:`installation`).

The address is the GPIB primary address, 20 by default (factory setting). On
connection the status registers are cleared and the bridge is put in remote mode;
on disconnection it goes back to local mode.

Temperatures need a ``thermometer``: any object with the
``resistance_to_temperature(resistance)`` and ``temperature_to_resistance(temperature)``
methods (resistance in Ohm, temperature in K).

Example of operations
"""""""""""""""""""""

.. code-block:: python

  from qtics import AVS47IB

  bridge = AVS47IB(20, thermometer=my_thermometer)
  bridge.connect()


To execute commands:

.. code-block:: python

   bridge.set_channel(3, range_idx=5, excitation_idx=3)  # grounds the input while switching
   print(bridge.measure())  # resistance in Ohm, raises on overload
   print(bridge.average(10))  # mean, min, max, std over 10 conversions
   print(bridge.read_temperature())  # temperature in K, needs the thermometer

   # TS-530A temperature controller: set all its parameters first
   bridge.configure_controller(set_point=10000, proportional_gain=5, heater_range=3)
   bridge.set_temperature(0.05)  # K, on the current bridge range
   print(bridge.read_heater_power())  # W

   bridge.disconnect()  # back to local mode

Range and excitation are indexes, the values are listed in
``qtics.instruments.picowatt.avs47ib.RANGES`` and ``EXCITATIONS``.

Commands
""""""""

Functions
---------

- get_id()
- self_test()
- reset()
- clear()
- set_reference(value)
- zero_difference()
- trigger_adc()
- read_adc()
- read_resistance()
- measure()
- average(n)
- read_temperature()
- set_temperature(temperature)
- set_channel(channel, range_idx, excitation_idx, settle)
- configure_controller(set_point, proportional_gain, integrator_tc, derivator_tc, power_bias, heater_range)
- force_error_zero()
- read_set_point_voltage()
- read_heater_voltage()
- read_heater_current()
- read_heater_power()

Properties
----------

- remote
- input
- channel
- range
- excitation
- display
- autorange
- stabilization_delay
- reference_source
- magnifier
- overload
- set_point
- proportional_gain
- integrator_tc
- derivator_tc
- power_bias
- heater_range
