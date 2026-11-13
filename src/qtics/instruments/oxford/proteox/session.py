"""Manager for WAMP session."""

from autobahn.asyncio.wamp import ApplicationSession
from autobahn.wamp import auth
from autobahn.wamp.types import CloseDetails

from qtics import log


def wamp_call_handler_get():
    """Create the decorator for wrapping getters WAMP RPC calls.

    Handles exceptions and extracts the item at `index` (default the 5th, the
    value of most records) from the call response.

    Returns:
        Callable: The wrapped function.
    """

    def decorator(func):
        async def wrapper(self, uri, index=4):
            try:
                result = await func(self, uri)
                if isinstance(result, int):
                    return result
                return result.results[index]
            except Exception as e:
                log.error(f"Failed to query {uri}: {e}")
                raise

        return wrapper

    return decorator


def wamp_call_handler_set():
    """Create the decorator for wrapping setters WAMP RPC calls.

    Returns:
        Callable: The wrapped function.
    """

    def decorator(func):
        async def wrapper(self, uri, value=None):
            try:
                await func(self, uri, value)
            except Exception as e:
                log.error(f"Failed to query {uri}: {e}")
                raise

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
            instrument (Any): An object that holds the session, the disconnect event
                and the credentials (``user`` and ``secret``).
        """
        super().__init__(config)
        self.instrument = instrument

    def onConnect(self):
        """Join the realm using WAMP-CRA authentication."""
        self.join(self.config.realm, ["wampcra"], self.instrument.user)

    def onLeave(self, details: CloseDetails):
        """Override standard onLeave to avoid not necessary warning."""
        details.reason = CloseDetails.REASON_DEFAULT
        return super().onLeave(details)

    def onChallenge(self, challenge):
        """Authenticate.

        Args:
            challenge (Challenge): The challenge object containing auth parameters.

        Returns:
            str: Signature computed for the challenge.
        """
        secret = self.instrument.secret
        key = (
            auth.derive_key(
                secret,
                challenge.extra["salt"],
                challenge.extra["iterations"],
                challenge.extra["keylen"],
            )
            if "salt" in challenge.extra
            else secret
        )
        return auth.compute_wcs(key, challenge.extra["challenge"])

    async def onJoin(self, details):
        """Check the control mode of the system and claims control if no controller exists."""
        try:
            mode = await self.call("oi.decs.sessionmanager.system_control_mode")

            if mode == 0:
                log.warning("[Instrument] System is in LOCAL mode. Aborting session.")
                self.leave()
                return

            elif mode == 1:
                try:
                    controller = await self.call(
                        "oi.decs.sessionmanager.system_controller"
                    )
                    if controller.results[0] == 0:
                        await self.call("oi.decs.sessionmanager.claim_system_control")
                    else:
                        log.warning(
                            "[Instrument] A controller has been detected, disconnecting"
                        )
                        self.leave()
                        return

                except Exception as e:
                    log.error(f"ERROR: {e}")

        except Exception as e:
            log.error(f"[Instrument] Failed to query control mode: {e}")
            self.leave()
            return

        # Link the session to the instrument object
        self.instrument.session = self

    async def onDisconnect(self):
        """Forget the session and signal the instrument's disconnect_event if set."""
        self.instrument.session = None
        if self.instrument.disconnect_event:
            self.instrument.disconnect_event.set()
