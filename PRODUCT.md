# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Members of the BiQuTe cryogenic lab (University of Milano-Bicocca): students and
researchers who control lab instruments from Python. They come to the docs to look
up a driver's properties and units, or to write an experiment script, often while
working next to the measurement setup.

## Product Purpose
qtics (Quantum Technologies Instrumentation ControlS) is a Python library of drivers
for the lab's instruments (VNAs, spectrum analyzers, RF sources, power supplies,
cryostats, Arduino-based switches/attenuators) plus an `Experiment` framework with
monitors. Success: a lab member finds the right driver and a working snippet fast.

## Positioning
Drivers for exactly the instruments in the BiQuTe lab, with one consistent API per
instrument type (SI units, bool states, properties for settings, methods for actions)
and fake transports for testing without hardware.

## Operating Context
- Docs built with Sphinx (Furo theme, autodoc API reference) and deployed to GitHub
  Pages (biqute.github.io/qtics) by GitHub Actions.
- Readers switch between the docs and their scripts/notebooks.

## Capabilities and Constraints
- Stack stays Sphinx + Furo; no new docs dependencies without asking (poetry.lock
  changes need approval).
- Readers must be able to switch the visible docs version: latest by default, plus
  the previous two releases.
- Released versions so far: v0.0.1 to v0.0.6; 0.1.0 is in development.

## Brand Commitments
- BiQuTe logo (`docs/source/_static/biqute_logo.png`) stays.

## Evidence on Hand
- Driver pages in `docs/source/instruments/`, guides (installation, migration,
  experiments, arduino), examples in `examples/`.
- No user testimonials, benchmarks, or adoption numbers exist; do not invent them.
