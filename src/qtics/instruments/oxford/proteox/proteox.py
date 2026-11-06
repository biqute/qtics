"""Define proteox instrument object."""

import asyncio
import concurrent.futures
import threading
from os import getenv
from typing import Any, Callable, Optional

from autobahn.asyncio.wamp import ApplicationRunner
from dotenv import load_dotenv

from qtics import log
from qtics.instruments.base import Instrument
from qtics.instruments.oxford.proteox.session import (
    InstrumentSession,
    wamp_call_handler_get,
    wamp_call_handler_set,
)
from qtics.instruments.oxford.proteox.states import RecognizedStateManager
from qtics.instruments.oxford.proteox.uris import (
    getter_indices,
    getters,
    setters,
    state_labels,
)


class AsyncProteox:
    """Asynchronous high-level API for interacting with Proteox over WAMP.

    Missing connection parameters are read from the environment (after loading a
    ``.env`` file, if any): ``WAMP_ROUTER_URL``, ``WAMP_REALM``, ``WAMP_USER`` and
    ``WAMP_USER_SECRET``.
    """

    def __init__(self, url=None, realm=None, user=None, secret=None):
        """Initialize properties."""
        if None in (url, realm, user, secret):
            load_dotenv()
        self.url = url if url is not None else getenv("WAMP_ROUTER_URL")
        self.realm = realm if realm is not None else getenv("WAMP_REALM")
        self.user = user if user is not None else getenv("WAMP_USER")
        self.secret = secret if secret is not None else getenv("WAMP_USER_SECRET")
        self.session = None
        self._runner = None
        self.disconnect_event = None
        self.recognized_states = RecognizedStateManager(self)

    async def connect(self, timeout: float = 10):
        """Connect to the WAMP router and establish session."""
        self.disconnect_event = asyncio.Event()

        def make_session(config):
            return InstrumentSession(config, self)

        self._runner = ApplicationRunner(self.url, self.realm)
        loop = asyncio.get_running_loop()
        runner = loop.create_task(self._runner.run(make_session, start_loop=False))

        # Wait until connection is ready (onJoin sets `session`)
        elapsed = 0.0
        while self.session is None:
            if runner.done() and runner.exception() is not None:
                raise ConnectionError(
                    f"Could not open a WAMP session with {self.url}."
                ) from runner.exception()
            if self.disconnect_event.is_set() or elapsed >= timeout:
                runner.cancel()
                raise ConnectionError(f"Could not open a WAMP session with {self.url}.")
            await asyncio.sleep(0.1)
            elapsed += 0.1

    async def close(self):
        """Close the WAMP session."""
        if self.session is None:
            return
        if self.session._session_id:
            self.session.leave()
        if self.disconnect_event:
            await self.disconnect_event.wait()
        self.session = None

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
        raise AttributeError(f"'AsyncProteox' object has no attribute '{name}'")

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


class Proteox(Instrument):
    """Synchronous Proteox driver.

    Wraps :class:`AsyncProteox`, which runs on an event loop in a daemon thread.
    The dynamic ``get_<KEY>()`` and ``set_<KEY>(value)`` methods of
    :class:`AsyncProteox` are available as blocking calls. Exceptions raised in the
    coroutines propagate to the caller.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        realm: Optional[str] = None,
        user: Optional[str] = None,
        secret: Optional[str] = None,
        name: str = "Proteox",
        timeout: float = 10,
    ):
        """Initialize, see :class:`AsyncProteox` for the credentials."""
        super().__init__(name)
        self.timeout = timeout
        self._async = AsyncProteox(url, realm, user, secret)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def is_connected(self) -> bool:
        """Whether the event loop thread is running and the session is open."""
        return self._thread is not None and self._async.session is not None

    def connect(self):
        """Start the event loop thread and open the WAMP session."""
        if self.is_connected:
            log.info(f"Instrument {self.name} already connected.")
            return
        # The router may have dropped the session: restart from a clean loop
        self._stop_loop()
        loop = asyncio.new_event_loop()
        thread = threading.Thread(
            target=loop.run_forever, name=f"{self.name}-loop", daemon=True
        )
        thread.start()
        self._loop, self._thread = loop, thread
        try:
            self._run(self._async.connect(self.timeout), self.timeout + 5)
        except BaseException:
            self._stop_loop()
            raise
        log.info(f"Instrument {self.name} connected successfully.")

    def disconnect(self):
        """Close the WAMP session and stop the event loop thread."""
        if self._thread is None:
            log.info(f"No connection to close for instrument {self.name}.")
            return
        try:
            self._run(self._async.close(), self.timeout)
        finally:
            self._stop_loop()
        log.info(f"Instrument {self.name} disconnected.")

    def _stop_loop(self):
        """Stop the loop, join its thread and release them."""
        loop, thread = self._loop, self._thread
        self._loop, self._thread = None, None
        if loop is None or thread is None:
            return
        loop.call_soon_threadsafe(loop.stop)
        thread.join()
        loop.close()

    def _run(self, coroutine, timeout: Optional[float] = None) -> Any:
        """Run a coroutine on the loop thread and wait for its result."""
        if self._loop is None:
            coroutine.close()
            raise ConnectionError(f"Instrument {self.name} is not connected.")
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            return future.result(self.timeout if timeout is None else timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise

    def _sync_call(self, name: str) -> Callable:
        """Blocking version of the coroutine method ``name`` of the async driver."""

        def call(*args, **kwargs):
            return self._run(getattr(self._async, name)(*args, **kwargs))

        call.__name__ = name
        return call

    def __getattr__(self, name):
        """Blocking ``get_<KEY>`` and ``set_<KEY>`` from the async driver."""
        # Only called when normal lookup fails: look up internals through __dict__
        # to avoid recursion before __init__ has finished.
        if name.startswith(("get_", "set_")) and "_async" in self.__dict__:
            table = getters if name.startswith("get_") else setters
            if name[4:] in table:
                return self._sync_call(name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def is_in_remote(self) -> bool:
        """Check if Proteox is in remote mode, i.e. it can be controlled."""
        return self._sync_call("is_in_remote")()

    def is_in_recognized_state(self) -> bool:
        """Return True if the cryostat is in a recognized state."""
        return self._sync_call("is_in_recognized_state")()

    def get_recognized_states(self):
        """Return all matched recognized states."""
        return self._sync_call("get_recognized_states")()

    def how_to_go_to_recognized_state(self, target_state=None) -> str:
        """Return instructions to reach a recognized state, see :class:`AsyncProteox`."""
        return self._sync_call("how_to_go_to_recognized_state")(target_state)
