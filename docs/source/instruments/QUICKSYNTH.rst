
Microwave synthesizers by QuickSynth
====================================

In these category, qtics supports the FSW and FSL series by Microwave Synthesizer by National Instruments
The manual of this instrument and similar products can be found `here <http://ni-microwavecomponents.com/quicksyn-lite#documentation>`_. The SCPI commands and functions can be found in the `communications specifications <http://ni-microwavecomponents.com/manuals/5580522-01.pdf>`_.

Base class: :class:`qtics.instruments.serial_inst.SerialInst`.

Example of operation
""""""""""""""""""""

.. code-block:: python

  from qtics import FSL0010 # also FSL0020, FSW0010, FSW0020

  synth = FSL0010(name = "mySynth", address = "/dev/ttyUSB0")
  synth.freq = 5.3e9
  synth.output_on = True

Commands
""""""""
Other than featuring all the methods of :class:`qtics.instruments.serial_inst.SerialInst`, this class contains the following properties.

Properties
----------
- freq
- output_on
- ext_ref_source
- temperature
