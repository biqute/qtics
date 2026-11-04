"""Define proteox instrument object."""

from asyncio import Event, get_event_loop, sleep
from os import getenv

from autobahn.asyncio.wamp import ApplicationRunner
from dotenv import load_dotenv

from qtics.instruments.network.proteox.instrument_session import (
    InstrumentSession,
    wamp_call_handler_get,
    wamp_call_handler_set,
)
from qtics.instruments.network.proteox.recognized_states import RecognizedStateManager
from qtics.instruments.network.proteox.uris import (
    getter_indices,
    getters,
    setters,
    state_labels,
)

load_dotenv()
USER = getenv("WAMP_USER")
USER_SECRET = getenv("WAMP_USER_SECRET")
URL = getenv("WAMP_ROUTER_URL")
REALM = getenv("WAMP_REALM")


class Proteox:
    """High-level API for interacting with lab instruments over WAMP."""

    def __init__(self, url=URL, realm=REALM):
        """Initialize properties."""
        self.url = url
        self.realm = realm
        self.session = None
        self._runner = None
        self.disconnect_event = None
        self.recognized_states = RecognizedStateManager(self)

    async def connect(self, timeout: float = 10):
        """Connect to the WAMP router and establish session."""
        self.disconnect_event = Event()

        def make_session(config):
            return InstrumentSession(config, self)

        self._runner = ApplicationRunner(self.url, self.realm)
        loop = get_event_loop()
        loop.create_task(self._runner.run(make_session, start_loop=False))

        # Wait until connection is ready (onJoin sets `session`)
        elapsed = 0.0
        while self.session is None:
            if self.disconnect_event.is_set() or elapsed >= timeout:
                raise ConnectionError(f"Could not open a WAMP session with {self.url}.")
            await sleep(0.1)
            elapsed += 0.1

    async def close(self):
        """Close the WAMP session."""
        if self.session is None:
            return
        if self.session._session_id:
            self.session.leave()
        if self.disconnect_event:
            await self.disconnect_event.wait()

    async def is_in_remote(self) -> bool:
        """Check if Proteox is in remote mode, i.e. it can be controlled."""
        mode = await self.session.call("oi.decs.sessionmanager.system_control_mode")
        return mode == 1

    @wamp_call_handler_get()
    async def get_sensor(self, uri):
        """Get sensor value from URI."""
        return await self.session.call(uri)

    @wamp_call_handler_set()
    async def set_sensor(self, uri, value):
        """Set value of the given URI, parameters as in MAN-NS-0002 Appendix D."""
        if isinstance(value, (list, tuple)):
            await self.session.call(uri, *value)
        elif uri.endswith(".setpoint"):
            # the 1 is for closed control loop
            await self.session.call(uri, value, 1)
        elif uri.endswith(".power"):
            # the True enables the heater output
            await self.session.call(uri, value, True)
        else:
            await self.session.call(uri, value)

    def __getattr__(self, name):
        """General get function from sensor name."""
        if name.startswith("get_"):
            key = name[len("get_") :]
            if key in getters:

                async def dynamic_getter():
                    value = await self.get_sensor(
                        getters[key], getter_indices.get(key, 4)
                    )
                    if key == "state":
                        return state_labels.get(value, f"Unknown ({value})")
                    return value

                return dynamic_getter

        elif name.startswith("set_"):
            key = name[len("set_") :]
            if key in setters:

                async def dynamic_setter(value=None):
                    if key.endswith("_OFF"):
                        value = (0.0, False)
                    await self.set_sensor(setters[key], value)

                return dynamic_setter
        raise AttributeError(f"'Proteox' object has no attribute '{name}'")

    async def is_in_recognized_state(self) -> bool:
        """Return True if the cryostat is in a recognized state."""
        return await self.recognized_states.is_in_recognized_state()

    async def get_recognized_states(self):
        """Return all matched recognized states."""
        return await self.recognized_states.get_recognized_states()

    async def how_to_go_to_recognized_state(self, target_state=None) -> str:
        """
        Return instructions to reach a state.

        In particular:
        - the closest recognized state, if target_state is None
        - or a specific recognized state
        """
        return await self.recognized_states.how_to_go_to_recognized_state(target_state)
