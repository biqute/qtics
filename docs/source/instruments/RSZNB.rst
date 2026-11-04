R&S®ZNB vector network analyzer
===============================

Vector network analyzer drivers for ZNB series by Rohde&Shwarz.
This driver has been tested for the `ZNB20` and `ZNB26` VNAs of which documentation can be found at `RS website <https://www.rohde-schwarz.com/us/products/test-and-measurement/network-analyzers/rs-znb-vector-network-analyzer_63493-11648.html>`_.

The SCPI commands and functions can be found in the `programming guide <https://www.rohde-schwarz.com/webhelp/ZNB_ZNBT_HTML_UserManual_en/Content/welcome.htm>`_.

Base class: :class:`qtics.instruments.base.SCPIInstrument` (socket transport, port 5025). It implements the :class:`qtics.instruments.types.VNA` interface.

Example of operation
---------------------

.. code-block:: python

  from qtics import ZNB

  vna = ZNB("192.168.40.11", channel=1)
  vna.connect()

  vna.s_parameter = "S21"
  vna.averages = 5
  vna.power = -30  # dBm
  f, z = vna.snapshot(f_start=4e9, f_stop=8e9)  # sweep once, return (freqs, complex data)

Commands
""""""""
Other than featuring all the methods of :class:`qtics.instruments.base.SCPIInstrument`, the :class:`qtics.instruments.rohde_schwarz.znb.ZNB` class contains the following methods and properties:

Functions
------------
- setup()
- write_and_hold()
- hold()
- clear()
- activate_trace()
- sweep(): single sweep waiting for completion, considering averaging
- clear_average()
- autoscale()
- read_freqs()
- read_trace_data()
- snapshot()
- survey()
- start_calibration()
- measure_standard()
- apply_calibration()
- create_trace()
- select_trace()
- delete_trace()
- list_traces()
- read_times()

Properties
------------
- f_start
- f_stop
- f_center
- f_span
- points
- sweep_time
- sweep_meas_time
- averages
- continuous
- data_format
- s_parameter
- yformat
- smoothing
- ifbw
- power
- time_domain
- t_start
- t_stop
- time_domain_window
- harmonic_grid
- low_pass_extrapolation
- low_pass_stimulus
