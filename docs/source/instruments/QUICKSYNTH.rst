
Microwave synthesizers by QuickSynth
====================================

In these category, qtics supports the FSW and FSL series by Microwave Synthesizer by National Instruments
The manual of this instrument and similar products can be found `here <http://ni-microwavecomponents.com/quicksyn-lite#documentation>`_. The SCPI commands and functions can be found in the `communications specifications <http://ni-microwavecomponents.com/manuals/5580522-01.pdf>`_.

Base classes: :class:`qtics.instruments.types.RFSource` and :class:`qtics.instruments.base.SCPIInstrument` (serial transport, 115200 baud).

Example of operation
""""""""""""""""""""

.. code-block:: python

  from qtics import FSL0010 # also FSL0020, FSW0010, FSW0020

  synth = FSL0010("/dev/ttyUSB0")
  synth.connect()
  synth.frequency = 5.3e9
  synth.output = True

Commands
""""""""
Other than the common SCPI methods of :class:`qtics.instruments.base.SCPIInstrument`, this class contains the following properties.

Properties
----------
- frequency
- output
- ext_ref_source
- temperature
