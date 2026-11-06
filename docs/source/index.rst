Drive the lab's instruments from Python
=======================================

Qtics collects the drivers of the `BiQuTe cryogenic lab
<https://biqute.unimib.it/research/cryogenic-lab>`_: one driver per instrument,
one interface per instrument type. Units are SI, on/off states are booleans,
settings are properties and actions are methods.

.. code-block:: python

   from qtics import SMA100B, ZNB

   with ZNB("192.168.0.4") as vna, SMA100B("192.168.0.5") as source:
       source.frequency = 5e9  # Hz
       source.output = True
       vna.set(f_start=4e9, f_stop=6e9, points=1001)
       freqs, s21 = vna.snapshot()

Install it with ``pip install qtics`` (see :ref:`installation` for the optional
extras), then write your measurement as an :ref:`experiment <experiments>`.

Instruments
-----------

.. include:: instruments/catalogue.inc

Every driver also accepts a :class:`~qtics.transport.fake.FakeTransport`, so scripts can
be tested without hardware. Coming from qtics 0.0.x? Read :doc:`migration`.

.. toctree::
   :hidden:
   :caption: Getting started

   installation
   migration

.. toctree::
   :hidden:
   :caption: Instruments

   instruments/modules
   arduino

.. toctree::
   :hidden:
   :caption: Experiments

   experiments

.. toctree::
   :hidden:
   :caption: API reference

   api-reference/modules
   genindex
