"""Test Proteox driver and recognized states against MAN-NS-0002 rev E."""

import asyncio

import pytest

from qtics import Proteox
from qtics.instruments.network.proteox.recognized_states import (
    ALL_CONDITIONS,
    build_conditions,
)
from qtics.instruments.network.proteox.uris import getters

CONDITIONS = build_conditions()


def evaluate(key, signals):
    """Evaluate a single condition on the given signals."""
    return CONDITIONS[key].evaluator(signals)


@pytest.fixture
def proteox(mocker):
    """Proteox with a mocked WAMP session."""
    inst = Proteox(url="ws://localhost", realm="test")
    inst.session = mocker.Mock()
    inst.session.call = mocker.AsyncMock()
    return inst


def test_all_conditions_defined():
    """Every condition used by the truth table must be defined."""
    assert set(ALL_CONDITIONS) <= set(CONDITIONS)


@pytest.mark.parametrize(
    "v9, v10, v4, expected",
    [(1, 1, 0, True), (0, 1, 0, False), (1, 0, 0, False), (1, 1, 1, False)],
)
def test_trap_bypassed(v9, v10, v4, expected):
    """Trap is bypassed with V9, V10 open and V4 closed (Table 59)."""
    signals = {"V9_OPEN": v9, "V10_OPEN": v10, "V4_OPEN": v4}
    assert evaluate("TRAP_BYPASSED", signals) is expected


@pytest.mark.parametrize(
    "key, signal",
    [("PRECOOL_ENABLED", "AV_15_OPEN"), ("EMPTYING_PRECOOL", "AV_17_OPEN")],
)
def test_precool_valves(key, signal):
    """Precool conditions follow 3CL-AV-15 and 3CL-AV-17 (Table 59)."""
    assert evaluate(key, {signal: 1}) is True
    assert evaluate(key, {signal: 0}) is False


def test_ovc_valve_open():
    """OVC valve state is 1 when open (OiValveStateRecord)."""
    assert getters["OVC_AV_01_OPEN"] == "oi.decs.proteox.OVC_AV_01.state"
    assert evaluate("OVC_VALVE_OPEN", {"OVC_AV_01_OPEN": 1}) is True
    assert evaluate("OVC_VALVE_OPEN", {"OVC_AV_01_OPEN": 0}) is False


def test_set_setpoint_closed_loop(proteox):
    """Setpoint is sent as [setpoint_K, demanded_mode=closed]."""
    asyncio.run(proteox.set_MC_T(0.1))
    proteox.session.call.assert_awaited_once_with(
        "oi.decs.temperature_control.DRI_MIX_CL.setpoint", 0.1, 1
    )


def test_set_heater_power(proteox):
    """Heater power is sent as [power_W, output_enabled]."""
    asyncio.run(proteox.set_STILL_H(0.01))
    proteox.session.call.assert_awaited_once_with(
        "oi.decs.temperature_control.DRI_STL_H.power", 0.01, True
    )


def test_set_heater_off(proteox):
    """Heater OFF sends zero power with the output disabled."""
    asyncio.run(proteox.set_MC_H_OFF())
    proteox.session.call.assert_awaited_once_with(
        "oi.decs.temperature_control.DRI_MIX_CL.DRI_MIX_H.power", 0.0, False
    )


def test_set_magnet_state(proteox):
    """Magnet setters must reach the instrument."""
    asyncio.run(proteox.set_MAG_STATE(30))
    proteox.session.call.assert_awaited_once_with(
        "oi.decs.magnetic_field_control.VRM_01.set_state", 30
    )


def test_set_magnet_target_params(proteox):
    """Multi-parameter setters are unpacked into the WAMP call."""
    params = (0, 0.0, 0.0, 1.0, 0, 0.1, False)
    asyncio.run(proteox.set_MAG_TARGET(params))
    proteox.session.call.assert_awaited_once_with(
        "oi.decs.magnetic_field_control.VRM_01.set_field_target", *params
    )


def test_close_without_session():
    """Closing a never connected Proteox must not raise."""
    asyncio.run(Proteox(url="ws://localhost", realm="test").close())


def test_connect_timeout(mocker):
    """Connect must fail instead of waiting forever."""
    runner = mocker.patch("qtics.instruments.network.proteox.proteox.ApplicationRunner")
    runner.return_value.run = mocker.AsyncMock()
    inst = Proteox(url="ws://localhost", realm="test")
    with pytest.raises(ConnectionError):
        asyncio.run(inst.connect(timeout=0.2))


@pytest.mark.parametrize(
    "old, new", [("V4_CLOSED", "V4_OPEN"), ("AV_08_CLOSED", "AV_08_OPEN")]
)
def test_valve_getters_named_open(old, new):
    """Valve state is 1 when open, getter names must say so."""
    assert old not in getters
    assert new in getters


def test_emptying_trap():
    """Emptying trap when 3CL-AV-08 is open (Table 59)."""
    assert evaluate("EMPTYING_TRAP", {"AV_08_OPEN": 1}) is True
    assert evaluate("EMPTYING_TRAP", {"AV_08_OPEN": 0}) is False


def test_getter_raises_on_error(proteox):
    """Failed WAMP calls must reach the caller."""
    proteox.session.call.side_effect = RuntimeError("wamp error")
    with pytest.raises(RuntimeError):
        asyncio.run(proteox.get_MC_T())


def test_setter_raises_on_error(proteox):
    """Failed WAMP calls must reach the caller."""
    proteox.session.call.side_effect = RuntimeError("error.not_authorized")
    with pytest.raises(RuntimeError):
        asyncio.run(proteox.set_MC_T(0.1))


@pytest.mark.parametrize("mode, expected", [(1, True), (0, False)])
def test_is_in_remote(proteox, mode, expected):
    """Remote mode is read from the session manager (Appendix D)."""
    proteox.session.call.return_value = mode
    assert asyncio.run(proteox.is_in_remote()) is expected
    proteox.session.call.assert_awaited_once_with(
        "oi.decs.sessionmanager.system_control_mode"
    )


def test_unknown_attribute_message(proteox):
    """Error message must name the Proteox class."""
    with pytest.raises(AttributeError, match="'Proteox'"):
        proteox.get_NOT_A_SENSOR  # pylint: disable=pointless-statement


def test_mc_control_loop_on(proteox, mocker):
    """Control loop state is actual_mode of the setpoint record (Appendix D)."""
    proteox.session.call.return_value = mocker.Mock(results=[1050, 0, 0, 0, 2.5, 1, 1])
    assert asyncio.run(proteox.get_MC_CTRL_ON()) == 1
    proteox.session.call.assert_awaited_once_with(
        "oi.decs.temperature_control.DRI_MIX_CL.setpoint"
    )
