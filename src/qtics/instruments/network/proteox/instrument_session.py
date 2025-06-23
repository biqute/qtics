import os

from autobahn.asyncio.wamp import ApplicationSession
from autobahn.wamp import auth
from dotenv import load_dotenv

load_dotenv()
USER = os.getenv("WAMP_USER")
USER_SECRET = os.getenv("WAMP_USER_SECRET")
URL = os.getenv("WAMP_ROUTER_URL")
REALM = os.getenv("WAMP_REALM")


def wamp_call_handler():
    def decorator(func):
        async def wrapper(self, uri):
            try:
                result = await func(self, uri)
                return result.results[4]
            except Exception as e:
                print(f"Failed to query: {e}")
                return None

        return wrapper

    return decorator


class InstrumentSession(ApplicationSession):
    """
    Internal session class to be used by Instrument. Handles WAMP session lifecycle.
    """

    def __init__(self, config, instrument):
        super().__init__(config)
        self.instrument = instrument

    def onConnect(self):
        self.join(self.config.realm, ["wampcra"], USER)

    def onChallenge(self, challenge):
        key = (
            auth.derive_key(
                USER_SECRET,
                challenge.extra["salt"],
                challenge.extra["iterations"],
                challenge.extra["keylen"],
            )
            if "salt" in challenge.extra
            else USER_SECRET
        )
        return auth.compute_wcs(key, challenge.extra["challenge"])

    async def onJoin(self, details):

        # identity = await self.call("oi.decs.sessionmanager.my_identity")
        # print(identity)

        try:
            mode = await self.call("oi.decs.sessionmanager.system_control_mode")
            if mode == 0:
                print("[Instrument] System is in LOCAL mode. Aborting session.")
                self.leave()
            elif mode == 1:
                print("[Instrument] System is in REMOTE mode. Proceeding.")
                try:
                    controller = await self.call(
                        "oi.decs.sessionmanager.system_controller"
                    )
                    if controller.results[0] == 0:
                        print("[Instrument] No controller detected, claiming control")
                        await self.call("oi.decs.sessionmanager.claim_system_control")
                    else:
                        print(
                            "[Instrument] A controller has been detected, disconnecting"
                        )
                        self.leave()
                except Exception as e:
                    print("ERROR ", e)

        except Exception as e:
            print(f"[Instrument] Failed to query control mode: {e}")
            self.leave()
        self.instrument.session = self

    async def onDisconnect(self):
        if self.instrument.disconnect_event:
            self.instrument.disconnect_event.set()
