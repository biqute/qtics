# Qinst - Instrumentation Tools for BiQuTe Lab

![docs](https://github.com/biqute/qinst/actions/workflows/deploy_docs.yml/badge.svg)
![Pylint](https://github.com/biqute/qinst/actions/workflows/pylint.yml/badge.svg)
![Tests](https://github.com/biqute/qinst/actions/workflows/tests.yml/badge.svg)

## Overview

Qinst is a collection of tools designed to facilitate the instrumentation of the
[BiQuTe Cryogenic Laboratory](https://biqute.unimib.it/research/cryogenic-lab).

In the experiments folder, some experiments are provided as examples, along with
various helpers.

## Documentation

You can find the latest documentation [here](https://biqute.github.io/qinst).

## Installation instructions

### Stable version:

To install the latest released version, you can use the standard pip command:

```bash
pip install qinst
```

### Latest version:

To install the latest version, unreleased, you can first clone the repository
with:

```bash
git clone https://github.com/biqute/qinst.git
```

then to install it in normal mode:

```bash
pip install .
```

otherwise use poetry:

```bash
poetry install --with docs,analysis,tests,experiments
pre-commit install
```

Remember to also install the pre-commits!

## License

Qinst is licensed under the [Apache License 2.0](LICENSE). See the
[LICENSE](LICENSE) file for details.
