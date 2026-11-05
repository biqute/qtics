"""Test the examples in the examples folder."""

import importlib.util
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parent.parent / "examples" / "experiments.py"


@pytest.fixture
def examples():
    """Import the experiments examples module."""
    spec = importlib.util.spec_from_file_location("experiments", EXAMPLES)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("temp_k, fails", [(0.05, False), (0.2, True)])
def test_triton_monitor_range(examples, mocker, temp_k, fails):
    """Monitor raises only outside the allowed range in mK."""
    monitor = examples.TritonMonitor("tempcheck", min_temp=0, max_temp=80)
    mocker.patch.object(monitor.cryo, "get_mixing_chamber_temp", return_value=temp_k)
    if fails:
        with pytest.raises(examples.TemperatureNotInRangeError):
            monitor.main()
    else:
        monitor.main()
