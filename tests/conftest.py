"""Options of the hardware tests, which are skipped unless ``--hw-config`` is given."""

from pathlib import Path

import pytest

HARDWARE_DIR = Path(__file__).parent / "hardware"


def pytest_addoption(parser):
    """Add the hardware test options."""
    group = parser.getgroup("hardware", "tests on real instruments (tests/hardware)")
    group.addoption(
        "--hw-config",
        default=None,
        help="TOML file with the instruments to test, see tests/hardware/lab.example.toml",
    )
    group.addoption(
        "--no-manual",
        action="store_true",
        help="skip the checks that ask the operator for a confirmation",
    )
    group.addoption(
        "--allow-output",
        action="store_true",
        help="run the tests that switch on outputs (RF, voltage, heaters)",
    )


def pytest_configure(config):
    """Register the markers."""
    config.addinivalue_line("markers", "hardware: needs a real instrument")
    config.addinivalue_line(
        "markers", "output: switches on an instrument output, needs --allow-output"
    )


def pytest_collection_modifyitems(config, items):
    """Mark and skip the hardware tests according to the options."""
    no_config = pytest.mark.skip(reason="hardware test, pass --hw-config to run it")
    no_output = pytest.mark.skip(reason="switches on an output, pass --allow-output")
    for item in items:
        if HARDWARE_DIR not in Path(item.fspath).parents:
            continue
        item.add_marker(pytest.mark.hardware)
        if not config.getoption("hw_config"):
            item.add_marker(no_config)
        elif "output" in item.keywords and not config.getoption("allow_output"):
            item.add_marker(no_output)
