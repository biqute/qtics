"""Fixtures of the hardware tests.

Run them with ``pytest tests/hardware --hw-config lab.toml``. Instruments missing
from the config are skipped. See ``lab.example.toml`` for the config format.
"""

import sys
from numbers import Number

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    tomllib = pytest.importorskip("tomli", reason="Python < 3.11 needs tomli")


@pytest.fixture(scope="session")
def hw_config(pytestconfig) -> dict:
    """Content of the ``--hw-config`` file."""
    with open(pytestconfig.getoption("hw_config"), "rb") as file:
        return tomllib.load(file)


@pytest.fixture(scope="module")
def open_instrument(hw_config):
    """Return a function connecting an instrument described in the config.

    ``open_instrument(cls, section=None, **kwargs)`` builds ``cls`` with the
    ``address`` and the other options of the ``[section]`` table (default: the class
    name) plus ``kwargs``, and connects it. The test is skipped if the section is
    missing. Instruments are disconnected at the end of the module.
    """
    opened = []

    def _open(cls, section=None, **kwargs):
        section = section or cls.__name__
        if section not in hw_config:
            pytest.skip(f"[{section}] not in the hardware config")
        options = {**hw_config[section], **kwargs}
        args = [options.pop("address")] if "address" in options else []
        inst = cls(*args, **options)
        inst.connect()
        opened.append(inst)
        return inst

    yield _open
    for inst in reversed(opened):
        inst.disconnect()


def check_roundtrip(inst, prop, values, rel=1e-6, abs_tol=0):
    """Set each value of ``prop``, read it back and compare, then restore it."""
    original = getattr(inst, prop)
    try:
        for value in values:
            setattr(inst, prop, value)
            read = getattr(inst, prop)
            if isinstance(value, Number) and not isinstance(value, bool):
                assert read == pytest.approx(value, rel=rel, abs=abs_tol), prop
            else:
                assert read == value, prop
    finally:
        setattr(inst, prop, original)


@pytest.fixture
def roundtrip():
    """Return :func:`check_roundtrip`."""
    return check_roundtrip


@pytest.fixture
def confirm(request):
    """Return a function asking the operator to confirm a check (y/N).

    The test fails if the answer is not yes, it is skipped with ``--no-manual``.
    """

    def _confirm(question: str):
        if request.config.getoption("no_manual"):
            pytest.skip("manual check, --no-manual given")
        capture = request.config.pluginmanager.getplugin("capturemanager")
        with capture.global_and_fixture_disabled():
            answer = input(f"\n[{request.node.name}] {question} [y/N] ")
        assert answer.strip().lower() in ("y", "yes"), f"Not confirmed: {question}"

    return _confirm
