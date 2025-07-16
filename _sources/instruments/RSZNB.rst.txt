R&S®ZNB vector network analyzer
===============================

Vector network analyzer drivers for ZNB series by Rohde&Shwarz.
This driver has been tested for the `ZNB20` and `ZNB26` VNAs of which documentation can be found at `RS website <https://www.rohde-schwarz.com/us/products/test-and-measurement/network-analyzers/rs-znb-vector-network-analyzer_63493-11648.html>`_.

The SCPI commands and functions can be found in the `programming guide <https://www.rohde-schwarz.com/webhelp/ZNB_ZNBT_HTML_UserManual_en/Content/welcome.htm>`_.

Base class: :class:`qtics.instruments.network_inst.NetworkInst`.

Commands
""""""""
Other than featuring all the methods of :class:`qtics.instruments.network_inst.NetworkInst`, the base :class:`qtics.instruments.network.RS_ZNB.RSZNB` class contains the following methods and properties:

Functions
------------
- setup()
- write_and_hold()
- hold()
- clear()
- activate_trace()
- single_sweep()
- query_data()
- clear_average()
- autoscale()
- read_freqs()
- read_trace_data()
- sweep()
- snapshot()
- survey()
- start_calibration()
- measure_standard()
- apply_calibration()
- create_trace()
- select_trace()
- delete_trace()
- list_trace()

Properties
------------
- f_min
- f_max
- f_center
- f_span
- sweep_points
- sweep_time
- sweep_meas_time
- average
- continuous
- data_format
- s_par
- yformat
- smoothing
- IFBW
- power
