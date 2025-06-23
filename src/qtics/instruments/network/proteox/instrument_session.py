"""Manager for WAMP session."""

import os

from autobahn.asyncio.wamp import ApplicationSession
from autobahn.wamp import auth
from dotenv import load_dotenv

# Load environment variables from a `.env` file
load_dotenv()
USER = os.getenv("WAMP_USER")  # WAMP username
USER_SECRET = os.getenv("WAMP_USER_SECRET")  # WAMP user password/secret
URL = os.getenv("WAMP_ROUTER_URL")  # WAMP router URL
REALM = os.getenv("WAMP_REALM")  # WAMP realm name


def wamp_call_handler():
    """Create the decorator for wrapping WAMP RPC calls.

    Handles exceptions and extracts the 5th result item from the call response.

    Returns:
        Callable: The wrapped function.
    """

    def decorator(func):
        async def wrapper(self, uri):
            try:
                result = await func(self, uri)
                return result.results[4]  # Return only the 5th item from result
            except Exception as e:
                print(f"Failed to query: {e}")
                return None

        return wrapper

    return decorator


class InstrumentSession(ApplicationSession):
    """WAMP session class.

    Manages the connection to the router and ensures the
    instrument has control of the system if in remote mode.

    Attributes:
        instrument (Any): Reference to the parent instrument instance.
    """

    def __init__(self, config, instrument):
        """Initialize the InstrumentSession.

        Args:
            config (ComponentConfig): WAMP session configuration.
            instrument (Any): An object that holds session and disconnect event.
        """
        super().__init__(config)
        self.instrument = instrument

    def onConnect(self):
        """Join the realm using WAMP-CRA authentication."""
        self.join(self.config.realm, ["wampcra"], USER)

    def onChallenge(self, challenge):
        """Authenticate.

        Args:
            challenge (Challenge): The challenge object containing auth parameters.

        Returns:
            str: Signature computed for the challenge.
        """
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
        """Check the control mode of the system and claims control if no controller exists."""
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

        # Link the session to the instrument object
        self.instrument.session = self

    async def onDisconnect(self):
        """Signal the instrument's disconnect_event if set."""
        if self.instrument.disconnect_event:
            self.instrument.disconnect_event.set()
