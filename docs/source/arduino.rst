.. _arduino_firmware:

Compile Arduino Firmwares
=========================

Some of the instruments include an Arduino firmware that requires to be compiled and uploaded on the Arduino controller.

To compile the firmware, one should download the `Arduino <https://www.arduino.cc/en/software>`_ package.

Then, two options are available: the Arduino IDE, the Arduino command line interface.

Installation through Arduino IDE
""""""""""""""""""""""""""""""""

First install the additional required library `Vrekrer_scpi_parser` (version 0.5.0).
To do so, go to Tools -> Manage Libraries. Search `Vrekrer_scpi_parser`, select the right version and install.

Then, upload the firmware using the dedicated upload button.

Installation through Command Line
"""""""""""""""""""""""""""""""""

First, download the arduino CLI tool from `the official website <https://arduino.github.io/arduino-cli/0.23/installation/>`_.

Then download the additional required library `Vrekrer_scpi_parser` (version 0.5.0):

.. code-block:: bash

    arduino-cli lib vrekrer_scpi_parser@0.5.0

Then compile and upload the firmware:

.. code-block:: bash

    arduino --upload [sketch.ino]
