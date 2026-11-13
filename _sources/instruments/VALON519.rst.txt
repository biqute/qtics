Frequency Synthesizer module Valon Model 5019
=============================================

The manuals of this instrument and similar models are available at `Valon <https://www.valonrf.com/5019-frequency-synthesizer-20ghz-542911.html>`_.

Base classes: :class:`qtics.instruments.types.RFSource` and :class:`qtics.instruments.base.MessageInstrument` (serial transport, terminator ``\r``, delay 0.3 s).

Example of operations
"""""""""""""""""""""
.. code-block:: python

  from qtics import Valon5019

  fs = Valon5019("/dev/ttyUSB0")
  fs.connect()
  fs.frequency = 5e9
  fs.power = -10
  fs.output = True

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
- frequency
- f_offset
- f_step_cw
- f_start
- f_stop
- f_step
- sweep_rate
- sweep_rtime
- sweep_tmode
- list_entry (setter only; getter raises `NotImplementedError`)
- power
- output
- power_pdn
- am_modulation
- am_frequency
- ref_freq
- ref_source
