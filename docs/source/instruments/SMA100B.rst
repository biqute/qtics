R&S®SMA100B RF and microwave signal generator
===========================================

R&S®SMA100B RF and microwave signal generator by Rohde & Schwarz
The manuals of this instrument and similar models are available at `Rohde & Schwarz <https://www.rohde-schwarz.com/products/test-and-measurement/analog-signal-generators/rs-sma100b-rf-and-microwave-signal-generator_63493-427776.html>`_.
The SCPI commands and functions can be found in the `programming guide <https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/pdm/cl_manuals/user_manual/1178_3834_01/SMA100B_UserManual_en_10.pdf>`_.

Base class: :class:`qinst.instruments.network_inst.NetworkInst`.

Example of operations
---------------------
.. code-block:: python

  from qinst import SMA_100B

  sg = SMA_100B(name = "mySignalGenerator", address = "192.168.40.15")
  sg.connect()

Set the frequency and the RF level applied to the DUT at 1 GHz and 1 V respectively.

.. code-block:: python

  sg.f_mode = "CW"
  sg.f_fixed = 1e9
  sg.p_mode = "CW"
  sg.p_unit = "V"
  sg.p_fixed = 1

Perform a one-off RF frequency sweep in a range of 1 GHz to 10 GHz with a frequency step of 100 kHz and a dwell time of 1 second.

.. code-block:: python

  sg.f_sweep_mode = "SING"
  sg.f_mode = "SWEEP"
  sg.f_min = 1e9
  sg.f_max = 10e9
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
- screen_saver_time(time)
- screen_saver_mode(state)
- f_mode(mode)
- f_fixed(f)
- f_mult(n)
- f_offset(f)
- f_sweep_mode(mode)
- f_min(f)
- f_max(f)
- f_center(f)
- f_span(f)
- f_step(f)
- f_dwell(value)
- phase(deg)
- set_phase_ref()
- p_unit(unit)
- p_mode(mode)
- p_fixed(p)
- p_sweep_mode(mode)
- p_min(p)
- p_max(p)
- p_dwell(value)
- p_step(p)
- sweep()

Properties
------------
- is_completed
- screen_saver_time
- f_mode
- f_fixed
- f_mult
- f_offset
- f_sweep_mode
- is_f_sweep_completed
- f_min
- f_max
- f_center
- f_span
- f_step
- f_dwell
- phase
- p_unit
- p_mode
- p_fixed
- p_sweep_mode
- is_p_sweep_completed
- p_min
- p_max
- p_dwell
- p_step
