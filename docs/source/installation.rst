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

Tests
-----

``poetry run pytest`` runs the tests that need no instrument (this is what CI runs).

The tests in ``tests/hardware`` check the drivers on real instruments, and are skipped
unless a config file is given. Copy ``tests/hardware/lab.example.toml`` to
``tests/hardware/lab.toml`` (ignored by git), keep the tables of the instruments on the
bench with their addresses, then run:

.. code-block:: bash

   poetry run pytest tests/hardware --hw-config tests/hardware/lab.toml

Instruments missing from the config are skipped. Each test sets values, reads them back
and restores the original ones; a few checks ask the operator to confirm what the
instrument shows (``--no-manual`` skips them). Tests that switch on an output (RF,
voltage, RF switches and attenuators) only run with ``--allow-output``. The cryostat
tests (Triton, Proteox) only read.
