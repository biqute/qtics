Frequency Synthesizer module Valon Model 5019
=============================================

The manuals of this instrument and similar models are available at `Valon <https://www.valonrf.com/5019-frequency-synthesizer-20ghz-542911.html>`_.

Base class: :class:`qtics.instruments.serial_inst.SerialInst`.

Example of operations
"""""""""""""""""""""
.. code-block:: python

  from qtics import VALON5019

  fs = VALON5019(name = "myvalon", address = "/dev/ttyUSB0")
  fs.connect()

Commands
""""""""

Functions
---------

- reset()
- write(cmd, sleep=False)
- read()
- get_id()
- increment_freq()
- decrement_freq()
- sweep_run()
- sweep_halt()
- sweep_trigger()

Properties
----------

- mode
- freq
- freq_offset
- freq_step
- sweep_start
- sweep_stop
- sweep_step
- sweep_rate
- sweep_rtime
- sweep_tmode
- list_entry (setter only; getter raises `NotImplementedError`)
- power
- power_oen
- power_pdn
- am_modulation
- am_frequency
- ref_freq
- ref_source
