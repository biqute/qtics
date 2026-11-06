"""Test Proteox drivers and recognized states against MAN-NS-0002 rev E."""

import asyncio

import pytest

from qtics.instruments.oxford.proteox import AsyncProteox, Proteox
from qtics.instruments.oxford.proteox.states import (
    ALL_CONDITIONS,
    build_conditions,
)
from qtics.instruments.oxford.proteox.uris import getters

CONDITIONS = build_conditions()


def evaluate(key, signals):
    """Evaluate a single condition on the given signals."""
    return CONDITIONS[key].evaluator(signals)


@pytest.fixture
def proteox(mocker):
    """AsyncProteox with a mocked WAMP session."""
    inst = AsyncProteox(url="ws://localhost", realm="test", user="u", secret="s")
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
    asyncio.run(AsyncProteox("ws://localhost", "test", "u", "s").close())


def test_connect_timeout(mocker):
    """Connect must fail instead of waiting forever."""
    runner = mocker.patch("qtics.instruments.oxford.proteox.proteox.ApplicationRunner")
    runner.return_value.run = mocker.AsyncMock()
    inst = AsyncProteox("ws://localhost", "test", "u", "s")
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
    """Error message must name the AsyncProteox class."""
    with pytest.raises(AttributeError, match="'AsyncProteox'"):
        proteox.get_NOT_A_SENSOR  # pylint: disable=pointless-statement


def test_mc_control_loop_on(proteox, mocker):
    """Control loop state is actual_mode of the setpoint record (Appendix D)."""
    proteox.session.call.return_value = mocker.Mock(results=[1050, 0, 0, 0, 2.5, 1, 1])
    assert asyncio.run(proteox.get_MC_CTRL_ON()) == 1
    proteox.session.call.assert_awaited_once_with(
        "oi.decs.temperature_control.DRI_MIX_CL.setpoint"
    )


# --- credentials -------------------------------------------------------------

ENV = {
    "WAMP_ROUTER_URL": "ws://env-host/ws",
    "WAMP_REALM": "env-realm",
    "WAMP_USER": "env-user",
    "WAMP_USER_SECRET": "env-secret",
}


@pytest.fixture
def no_dotenv(mocker):
    """Never read a real .env file."""
    return mocker.patch("qtics.instruments.oxford.proteox.proteox.load_dotenv")


def test_credentials_from_env(monkeypatch, no_dotenv):
    """Missing arguments are read from the environment."""
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    inst = AsyncProteox()
    assert (inst.url, inst.realm, inst.user, inst.secret) == (
        "ws://env-host/ws",
        "env-realm",
        "env-user",
        "env-secret",
    )
    no_dotenv.assert_called_once()


def test_credentials_from_args(monkeypatch, no_dotenv):
    """Arguments win over the environment, and no .env is loaded."""
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    inst = AsyncProteox("ws://a", "r", "u", "s")
    assert (inst.url, inst.realm, inst.user, inst.secret) == ("ws://a", "r", "u", "s")
    no_dotenv.assert_not_called()


def test_session_uses_instance_credentials(mocker):
    """The WAMP session takes user and secret from the instrument."""
    from qtics.instruments.oxford.proteox.session import InstrumentSession

    inst = AsyncProteox("ws://a", "r", "alice", "pw")
    session = InstrumentSession(mocker.Mock(realm="r"), inst)
    session.join = mocker.Mock()
    session.onConnect()
    session.join.assert_called_once_with("r", ["wampcra"], "alice")
    challenge = mocker.Mock(extra={"challenge": '{"nonce": 1}'})
    assert isinstance(session.onChallenge(challenge), (str, bytes))


# --- synchronous wrapper -----------------------------------------------------


@pytest.fixture
def sync_proteox(mocker, no_dotenv):
    """Sync Proteox whose connect sets a mocked session instead of using WAMP."""

    async def fake_connect(self, timeout=10):
        self.session = mocker.Mock()
        self.session.call = mocker.AsyncMock(return_value=1)
        self.session._session_id = 0

    mocker.patch.object(AsyncProteox, "connect", fake_connect)
    inst = Proteox("ws://a", "r", "u", "s")
    yield inst
    inst.disconnect()


def test_sync_connect_disconnect_thread(sync_proteox):
    """Connect starts the loop thread, disconnect stops it; both idempotent."""
    assert not sync_proteox.is_connected
    sync_proteox.connect()
    thread = sync_proteox._thread
    assert thread.is_alive() and thread.daemon
    assert sync_proteox.is_connected
    sync_proteox.connect()
    assert sync_proteox._thread is thread
    sync_proteox.disconnect()
    assert not thread.is_alive()
    assert not sync_proteox.is_connected
    sync_proteox.disconnect()


def test_sync_context_manager(sync_proteox):
    """The wrapper works as a context manager."""
    with sync_proteox:
        assert sync_proteox.is_connected
    assert sync_proteox._thread is None


def test_sync_getter_setter(sync_proteox, mocker):
    """Sync getters and setters call through to the session."""
    sync_proteox.connect()
    call = sync_proteox._async.session.call
    call.return_value = mocker.Mock(results=[0, 0, 0, 0, 0.012])
    assert sync_proteox.get_MC_T() == 0.012
    sync_proteox.set_MC_T(0.1)
    call.assert_awaited_with("oi.decs.temperature_control.DRI_MIX_CL.setpoint", 0.1, 1)
    sync_proteox.set_MC_H_OFF()
    call.assert_awaited_with(
        "oi.decs.temperature_control.DRI_MIX_CL.DRI_MIX_H.power", 0.0, False
    )


def test_sync_is_in_remote(sync_proteox):
    """Remote mode check goes through the loop."""
    sync_proteox.connect()
    assert sync_proteox.is_in_remote() is True


def test_sync_recognized_states(sync_proteox, mocker):
    """Recognized-state helpers are mirrored."""
    sync_proteox.connect()
    manager = sync_proteox._async.recognized_states
    mocker.patch.object(
        manager, "is_in_recognized_state", mocker.AsyncMock(return_value=True)
    )
    mocker.patch.object(
        manager, "get_recognized_states", mocker.AsyncMock(return_value=["A"])
    )
    howto = mocker.patch.object(
        manager, "how_to_go_to_recognized_state", mocker.AsyncMock(return_value="x")
    )
    assert sync_proteox.is_in_recognized_state() is True
    assert sync_proteox.get_recognized_states() == ["A"]
    assert sync_proteox.how_to_go_to_recognized_state("B") == "x"
    howto.assert_awaited_once_with("B")


def test_sync_exceptions_propagate(sync_proteox):
    """Errors in the coroutines reach the caller."""
    sync_proteox.connect()
    sync_proteox._async.session.call.side_effect = RuntimeError("wamp error")
    with pytest.raises(RuntimeError, match="wamp error"):
        sync_proteox.get_MC_T()
    with pytest.raises(RuntimeError, match="wamp error"):
        sync_proteox.set_MC_T(0.1)


def test_sync_not_connected(sync_proteox):
    """Calls before connect raise ConnectionError."""
    with pytest.raises(ConnectionError):
        sync_proteox.get_MC_T()


def test_sync_unknown_attribute(sync_proteox):
    """Unknown dynamic names raise AttributeError naming the class."""
    with pytest.raises(AttributeError, match="'Proteox'"):
        sync_proteox.get_NOT_A_SENSOR  # pylint: disable=pointless-statement
    with pytest.raises(AttributeError):
        sync_proteox.set_NOT_A_SETTER  # pylint: disable=pointless-statement


def test_sync_getattr_before_init():
    """No recursion when attributes are looked up before __init__ finished."""
    inst = Proteox.__new__(Proteox)
    with pytest.raises(AttributeError):
        inst.get_MC_T  # pylint: disable=pointless-statement


def test_sync_connect_failure_stops_thread(mocker, no_dotenv):
    """A failed connection leaves no running thread."""
    runner = mocker.patch("qtics.instruments.oxford.proteox.proteox.ApplicationRunner")
    runner.return_value.run = mocker.AsyncMock()
    inst = Proteox("ws://a", "r", "u", "s", timeout=0.2)
    with pytest.raises(ConnectionError):
        inst.connect()
    assert inst._thread is None


def test_sync_get_set_exact_names(sync_proteox):
    """Instrument.get/set keep working next to the dynamic getters."""
    assert callable(sync_proteox.get) and callable(sync_proteox.set)


def test_connect_surfaces_runner_error(mocker):
    """A failing WAMP runner is reported at once, with its cause."""
    runner = mocker.patch("qtics.instruments.oxford.proteox.proteox.ApplicationRunner")
    runner.return_value.run = mocker.AsyncMock(side_effect=OSError("unreachable"))
    inst = AsyncProteox("ws://localhost", "test", "u", "s")
    with pytest.raises(ConnectionError) as exc:
        asyncio.run(inst.connect(timeout=5))
    assert isinstance(exc.value.__cause__, OSError)


def test_session_disconnect_clears_session(mocker):
    """After a disconnection the instrument has no session anymore."""
    from qtics.instruments.oxford.proteox.session import InstrumentSession

    inst = AsyncProteox("ws://a", "r", "u", "s")
    session = InstrumentSession(mocker.Mock(realm="r"), inst)
    inst.session = session
    inst.disconnect_event = asyncio.Event()
    asyncio.run(session.onDisconnect())
    assert inst.session is None
    assert inst.disconnect_event.is_set()


def test_sync_reconnect_after_drop(sync_proteox):
    """If the router drops the session, connect() opens a new one."""
    sync_proteox.connect()
    first_thread = sync_proteox._thread
    sync_proteox._async.session = None  # what onDisconnect does
    assert not sync_proteox.is_connected
    sync_proteox.connect()
    assert sync_proteox.is_connected
    assert sync_proteox._thread is not first_thread
    assert not first_thread.is_alive()
