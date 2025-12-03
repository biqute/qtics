Proteox controller
==================

High-level controller for the Proteox cryostat system by Oxford Instruments, interfacing via WAMP.


To configure the connection, you must include a .env file in the same folder as the Proteox module. This file must contain the following entries:

.. code-block:: bash

  WAMP_USER="**********"
  WAMP_USER_SECRET="*************"
  WAMP_REALM="ucss"
  WAMP_ROUTER_URL="ws://************:8080/ws"
  BIND_SERVER_TO_INTERFACE="localhost"
  SERVER_PORT="33576"

.. warning::

  All API methods (including sensor accessors) are asynchronous and must be used with ``await`` inside an async function.

Example of operations
"""""""""""""""""""""

.. code-block:: python

  from asyncio import run
  from qtics import Proteox

  async def myfun():
      instrument = Proteox()
      await instrument.connect()

      for _ in range(1):
          mix = await instrument.get_MC_T()
          pt1 = await instrument.get_PT1_T1()
          pt2 = await instrument.get_PT2_T1()
          sti = await instrument.get_STILL_T()
          col = await instrument.get_CP_T()
          print("\nTEMPS:")
          print(f"MIX: {mix*1000:.2f} mK")
          print(f"STILL: {sti*1000:.2f} mK")
          print(f"COLD: {col*1000:.2f} mK")
          print(f"PT1: {pt1:.2f} K")
          print(f"PT2: {pt2:.2f} K")

      await instrument.close()

  run(myfun())


Commands
--------

* **connect()**

  Connect to the Proteox cryostat via WAMP.

* **close()**

  Cleanly disconnect from the cryostat session.

* **get_<sensor>()**

  Dynamic getter for supported sensors (see below).
  If the key is not recognized, raises an ``AttributeError``.

* **set_<attribute>(<value>)**

  Dynamic setter for supported control parameters (see below).
  If the key is not recognized, raises an ``AttributeError``.


Dynamic getters
---------------

The following sensors are available via dynamic getter methods:

Temperatures
^^^^^^^^^^^^

* get\_SAMPLE\_T() – Sample thermometer
* get\_MC\_T() – Mixing chamber temperature
* get\_MC\_T\_SP() – Mixing chamber temperature setpoint
* get\_STILL\_T() – Still temperature
* get\_CP\_T() – Cold plate temperature
* get\_SRB\_T() – Sorb temperature
* get\_DR2\_T(), get\_DR1\_T() – DR stage temperatures
* get\_PT2\_T1(), get\_PT1\_T1() – Pulse tube stage temperatures
* get\_MAG\_T() – Magnet system temperature

Heaters and Powers
^^^^^^^^^^^^^^^^^^

* get\_MC\_H() – Mixing chamber heater power
* get\_STILL\_H() – Still heater power

Pressures
^^^^^^^^^

* get\_OVC\_P() – Outer vacuum chamber pressure
* get\_P1\_P() to get\_P6\_P() – Various pressure gauges

Flows
^^^^^

* get\_3He\_F() – ^3He flowmeter

Magnetic Field Control
^^^^^^^^^^^^^^^^^^^^^^

* get\_MAG\_VEC() – Magnetic field vector
* get\_MAG\_STATE(), get\_SWZ\_STATE() – Magnet controller and sweep state
* get\_MAG\_TARGET() – Field target
* get\_MAG\_X\_STATE(), get\_MAG\_Y\_STATE(), get\_MAG\_Z\_STATE() – Axis state
* get\_MAG\_CURR\_VEC(), get\_CURR\_TARGET() – Magnet current vector and targets

State
^^^^^

* get\_state() – Cryostat state (returns descriptive label e.g., “CONDENSING”)

Available state labels:

* IDLE
* PUMPING
* CONDENSING
* CIRCULATING
* WARM UP
* CLEAN COLD TRAP
* SAMPLE EXCHANGE


Dynamic setters
---------------

The following control parameters are available via dynamic setter methods.
Each setter corresponds to a WAMP procedure call and must be awaited:

Example
"""""""

.. code-block:: python

  # Change the mixing chamber setpoint and heater power
  await instrument.set_MC_T(0.1)     # set MC temperature setpoint to 100 mK

.. note::
   The temperature is here in kelvin!

Temperature and Heater Control
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* set\_MC\_T(value) – Set mixing chamber temperature setpoint
* set\_MC\_H(value) – Set mixing chamber heater power
* set\_MC\_H\_OFF(value=0) – Turn off mixing chamber heater
* set\_STILL\_H(value) – Set still heater power
* set\_STILL\_H\_OFF(value=0) – Turn off still heater

Magnet Control
^^^^^^^^^^^^^^

* set\_MAG\_TARGET(value) – Set magnetic field target (vector or scalar depending on mode)
* set\_MAG\_STATE(value) – Set magnet controller state
* set\_MAG\_X\_STATE(value), set\_MAG\_Y\_STATE(value), set\_MAG\_Z\_STATE(value) – Set state for each magnet axis

.. note::

   Setter operations must always be awaited.
   Example: ``await instrument.set_MAG_STATE("SWEEP")``
