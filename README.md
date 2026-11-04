# Qtics - Quantum Technologies Instrumentation ControlS

![docs](https://github.com/biqute/qtics/actions/workflows/deploy_docs.yml/badge.svg)
![Lint-Pytest-Mypy](https://github.com/biqute/qtics/actions/workflows/analysis.yml/badge.svg)

## Overview

Qtics is a collection of tools designed to facilitate the instrumentation of the
[BiQuTe Cryogenic Laboratory](https://biqute.unimib.it/research/cryogenic-lab).

In the examples folder, some experiments are provided as examples.

## Documentation

You can find the latest documentation [here](https://biqute.github.io/qtics).

## Installation instructions

### Stable version:

To install the latest released version, you can use the standard pip command:

```bash
pip install qtics
```

Drivers needing extra packages have pip extras: `qtics[proteox]` (Oxford
Proteox), `qtics[niscope]` (NI PXIe-5170R) or `qtics[all]`.

### Latest version:

To install the latest version, unreleased, you can first clone the repository
with:

```bash
git clone https://github.com/biqute/qtics.git
```

then to install it in normal mode:

```bash
pip install .
```

Use poetry to install the latest version in developer mode, remember to also
install the pre-commits!

```bash
poetry install --all-extras --with docs,analysis,experiments
pre-commit install
```

## Usage

Drivers are imported from `qtics` and take the instrument address (or a
transport from `qtics.transport`):

```python
from qtics import SMA100B, ZNB

with ZNB("192.168.0.4") as vna, SMA100B("192.168.0.5") as source:
    source.frequency = 5e9  # Hz
    source.power = -10  # dBm
    source.output = True
    vna.set(f_start=4e9, f_stop=6e9, points=1001)
    freqs, s21 = vna.snapshot()
```

Coming from qtics 0.0.x? See the migration guide in the documentation.

## License

Qtics is licensed under the [Apache License 2.0](LICENSE). See the
[LICENSE](LICENSE) file for details.
