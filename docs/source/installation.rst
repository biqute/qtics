.. _installation:

Installation
============

Qtics can be installed from PyPI

.. code-block:: bash

   pip install qtics

Some drivers need optional packages, installed with the corresponding extra:

- ``proteox``: ``Proteox``/``AsyncProteox`` (autobahn, python-dotenv).
- ``niscope``: ``Pxie5170R`` (NI-SCOPE Python API; the NI driver must be installed
  separately).
- ``all``: all of the above.

.. code-block:: bash

   pip install "qtics[proteox]"
   pip install "qtics[all]"

GPIB instruments (``GPIBTransport``) need the GPIB driver, no Python package:
linux-gpib on Linux or NI-488.2 on Windows.

For development, clone the repository and install it with Poetry, including the
extras and the dependency groups for experiments, analysis (tests, linters) and docs:

.. code-block:: bash

   poetry install --all-extras --with experiments,analysis,docs
   pre-commit install
