"""Define proteox instrument object."""

from asyncio import Event, get_event_loop, sleep
from os import getenv

from autobahn.asyncio.wamp import ApplicationRunner
from dotenv import load_dotenv

from qtics.instruments.network.proteox.instrument_session import (
    InstrumentSession,
    wamp_call_handler,
)
from qtics.instruments.network.proteox.uris import getters, state_labels

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

    async def connect(self):
        """Connect to the WAMP router and establish session."""
        self.disconnect_event = Event()

        def make_session(config):
            return InstrumentSession(config, self)

        self._runner = ApplicationRunner(self.url, self.realm)
        loop = get_event_loop()
        loop.create_task(self._runner.run(make_session, start_loop=False))

        # Wait until connection is ready (onJoin sets `session`)
        while self.session is None:
            await sleep(0.1)

    async def close(self):
        """Close the WAMP session."""
        if self.session:
            self.session.leave()
        if self.disconnect_event:
            await self.disconnect_event.wait()
            print("Instrument disconnected.")

    @wamp_call_handler()
    async def get_sensor(self, uri):
        """Get sensor value from URI."""
        return await self.session.call(uri)

    def __getattr__(self, name):
        """General get function from sensor name."""
        if name.startswith("get_"):
            key = name[len("get_") :]
            if key in getters:

                async def dynamic_getter():
                    value = await self.get_sensor(getters[key])
                    if key == "state":
                        return state_labels.get(value, f"Unknown ({value})")
                    return value

                return dynamic_getter
        raise AttributeError(f"'Instrument' object has no attribute '{name}'")
