"""Tests of the AVS47IB driver."""

import pytest

from qtics import AVS47IB
from qtics.instruments.picowatt import avs47ib
from qtics.transport import FakeTransport, GPIBTransport


class LinearThermometer:
    """Thermometer with R = 1000 * T."""

    def resistance_to_temperature(self, resistance):
        """Temperature from resistance."""
        return resistance / 1000

    def temperature_to_resistance(self, temperature):
        """Resistance from temperature."""
        return temperature * 1000


@pytest.fixture(autouse=True)
def no_sleep(mocker):
    """Skip the waits of the driver."""
    mocker.patch.object(avs47ib.time, "sleep")


@pytest.fixture
def bridge():
    """Bridge on a fake transport, in remote mode, answers "<CMD> 0"."""
    transport = FakeTransport({"REM?": "REM 1"}, default=lambda cmd: cmd[:-1] + " 0")
    inst = AVS47IB(transport, thermometer=LinearThermometer())
    inst.transport.connect()
    return inst


def test_defaults():
    """GPIB transport on the factory address, integer addresses accepted."""
    inst = AVS47IB()
    assert isinstance(inst.transport, GPIBTransport)
    assert inst.address == "GPIB0::20::INSTR"
    assert AVS47IB(7, board=1).address == "GPIB1::7::INSTR"
    assert inst.name == "AVS47IB"


def test_connect_disconnect_hooks():
    """Clear and remote on connect, local before closing."""
    inst = AVS47IB(FakeTransport())
    inst.connect()
    inst.disconnect()
    assert inst.transport.written == ["*CLS", "REM 1", "REM 0"]


def test_settings(bridge):
    """Getters parse the last field, setters validate."""
    bridge.transport.answers["MUX?"] = "MUX 3"
    assert bridge.channel == 3
    bridge.channel = 9
    bridge.range = 5
    bridge.excitation = 2
    bridge.input = avs47ib.INP_MEASURE
    bridge.autorange = True
    assert bridge.transport.written[-5:] == [
        "MUX 7",
        "RAN 5",
        "EXC 2",
        "INP 1",
        "ARN 1",
    ]


def test_measure(bridge):
    """Measure triggers a conversion and reads the resistance."""
    bridge.transport.answers["RES?"] = "RES 1234.5"
    assert bridge.measure() == 1234.5
    assert bridge.transport.written[-2:] == ["ADC", "RES?"]
    assert bridge.read_temperature() == 1.2345


def test_measure_overload(bridge):
    """Overload raises."""
    bridge.transport.answers["RES?"] = "RES 2.0001E+6"
    with pytest.raises(RuntimeError, match="overload"):
        bridge.measure()


def test_average_restores_timeout(bridge):
    """Average raises the timeout during the acquisition and restores it."""
    timeouts = []
    bridge.transport.answers["AVE?"] = lambda cmd: (
        timeouts.append(bridge.transport.timeout) or "AVE 10.5"
    )
    result = bridge.average(10)
    assert result["mean"] == 10.5 and result["overload"] is False
    assert timeouts == [10 * 0.4 + 1 + 5]
    assert bridge.transport.timeout == 0
    assert "AVE 10" in bridge.transport.written


def test_set_temperature(bridge):
    """Temperature -> resistance -> set point on the current range."""
    bridge.transport.answers["RAN?"] = "RAN 4"  # 2 kOhm full scale
    bridge.set_temperature(1)  # 1 kOhm, half scale
    assert bridge.transport.written[-1] == "SPT 10000"


def test_ts530_needs_remote(bridge):
    """TS-530A setters refuse to run in local mode."""
    bridge.transport.answers["REM?"] = "REM 0"
    with pytest.raises(RuntimeError, match="remote"):
        bridge.heater_range = 3


def test_no_thermometer():
    """Temperature methods need a thermometer."""
    inst = AVS47IB(FakeTransport(default="RES 1"))
    inst.transport.connect()
    with pytest.raises(RuntimeError, match="thermometer"):
        inst.read_temperature()


def test_macro(bridge):
    """Heater power macro writes the command, then queries it."""
    bridge.transport.answers["HTP?"] = "HTP 1.5E-6"
    assert bridge.read_heater_power() == 1.5e-6
    assert bridge.transport.written[-2:] == ["HTP", "HTP?"]
