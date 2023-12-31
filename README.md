# Qtics - Quantum Technologies Instrumentation ControlS

![docs](https://github.com/biqute/qtics/actions/workflows/deploy_docs.yml/badge.svg)
![Lint-Pytest-Mypy](https://github.com/biqute/qtics/actions/workflows/analysis.yml/badge.svg)

## Overview

Qtics is a collection of tools designed to facilitate the instrumentation of the
[BiQuTe Cryogenic Laboratory](https://biqute.unimib.it/research/cryogenic-lab).

In the experiments folder, some experiments are provided as examples, along with
various helpers.

## Documentation

You can find the latest documentation [here](https://biqute.github.io/qtics).

## Installation instructions

### Stable version:

To install the latest released version, you can use the standard pip command:

```bash
pip install qtics
```

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
poetry install --with docs,analysis,experiments
pre-commit install
```

## License

Qtics is licensed under the [Apache License 2.0](LICENSE). See the
[LICENSE](LICENSE) file for details.
