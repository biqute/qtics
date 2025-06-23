import asyncio
import os

from autobahn.asyncio.wamp import ApplicationRunner
from dotenv import load_dotenv

from qtics.instruments.network.proteox.instrument_session import (
    InstrumentSession,
    wamp_call_handler,
)
from qtics.instruments.network.proteox.uris import getters, state_labels

load_dotenv()
USER = os.getenv("WAMP_USER")
USER_SECRET = os.getenv("WAMP_USER_SECRET")
URL = os.getenv("WAMP_ROUTER_URL")
REALM = os.getenv("WAMP_REALM")


async def main():
    instrument = Proteox()
    await instrument.connect()

    for _ in range(5):
        # temp = await instrument.get_MC_T()
        # print(f"{temp * 1000} mK")
        status = await instrument.get_state()
        print(status)
        await asyncio.sleep(1)

    await instrument.close()


class Proteox:
    """
    High-level API for interacting with lab instruments over WAMP.
    """

    def __init__(self, url=URL, realm=REALM):
        self.url = url
        self.realm = realm
        self.session = None
        self._runner = None
        self.disconnect_event = None

    async def connect(self):
        """
        Connect to the WAMP router and establish session.
        """
        self.disconnect_event = asyncio.Event()

        def make_session(config):
            return InstrumentSession(config, self)

        self._runner = ApplicationRunner(self.url, self.realm)
        loop = asyncio.get_event_loop()
        loop.create_task(self._runner.run(make_session, start_loop=False))

        # Wait until connection is ready (onJoin sets `session`)
        while self.session is None:
            await asyncio.sleep(0.1)

    async def close(self):
        """
        Cleanly close the WAMP session.
        """
        if self.session:
            self.session.leave()
        if self.disconnect_event:
            await self.disconnect_event.wait()
            print("Instrument disconnected.")

    @wamp_call_handler()
    async def get_sensor(self, uri):
        return await self.session.call(uri)

    def __getattr__(self, name):
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


if __name__ == "__main__":
    asyncio.run(main())
