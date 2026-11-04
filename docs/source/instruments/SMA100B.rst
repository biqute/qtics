R&S®SMA100B RF and microwave signal generator
=============================================

R&S®SMA100B RF and microwave signal generator by Rohde & Schwarz
The manuals of this instrument and similar models are available at `Rohde & Schwarz <https://www.rohde-schwarz.com/products/test-and-measurement/analog-signal-generators/rs-sma100b-rf-and-microwave-signal-generator_63493-427776.html>`_.
The SCPI commands and functions can be found in the `programming guide <https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/pdm/cl_manuals/user_manual/1178_3834_01/SMA100B_UserManual_en_10.pdf>`_.

Base classes: :class:`qtics.instruments.types.RFSource` and :class:`qtics.instruments.base.SCPIInstrument`.

The power unit is set to dBm after connecting (``power`` is in dBm, see ``p_unit``).

Example of operations
---------------------
.. code-block:: python

  from qtics import SMA100B

  sg = SMA100B("192.168.40.15")
  sg.connect()

Set the frequency and the RF level applied to the DUT at 1 GHz and -10 dBm respectively.

.. code-block:: python

  sg.output = False
  sg.f_mode = "CW"
  sg.frequency = 1e9
  sg.p_mode = "CW"
  sg.power = -10
  sg.output = True

Perform a one-off RF frequency sweep in a range of 1 GHz to 10 GHz with a frequency step of 100 kHz and a dwell time of 1 second.

.. code-block:: python

  sg.f_sweep_mode = "SING"
  sg.f_mode = "SWEEP"
  sg.f_start = 1e9
  sg.f_stop = 10e9
  sg.f_dwell = 1
  sg.f_step = 100e3
  sg.sweep()

Commands
""""""""

Functions
------------
- reset()
- clear()
- wait()
- cal(opt)
- diag(opt)
- screen_saver_mode(state)
- set_phase_ref()
- sweep()

Properties
------------
- is_completed
- screen_saver_time
- output
- f_mode
- frequency
- f_mult
- f_offset
- f_sweep_mode
- is_f_sweep_completed
- f_start
- f_stop
- f_center
- f_span
- f_step
- f_dwell
- phase
- p_unit
- p_mode
- power
- p_sweep_mode
- is_p_sweep_completed
- p_start
- p_stop
- p_dwell
- p_step
