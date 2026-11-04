"""Base instrument classes.

- :class:`Instrument`: name, defaults, set/get and validation helpers.
- :class:`MessageInstrument`: exchanges text messages through a
  :class:`~qtics.transport.Transport`.
- :class:`SCPIInstrument`: message instrument with the SCPI common commands.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Type, Union

from qtics import log
from qtics.transport import SocketTransport, Transport


class Instrument(ABC):
    """Base instrument class."""

    def __init__(self, name: str):
        """Initialize."""
        self.name = name
        self._defaults: Dict[str, Any] = {}

    @abstractmethod
    def connect(self):
        """Connect to the instrument."""

    @abstractmethod
    def disconnect(self):
        """Disconnect from the instrument."""

    def __enter__(self):
        """Connect when entering a ``with`` block."""
        self.connect()
        return self

    def __exit__(self, *exc):
        """Disconnect when leaving a ``with`` block."""
        self.disconnect()

    def reset(self, defaults: bool = True):
        """Restore the default values.

        Instruments supporting a hardware reset extend this method.
        """
        if defaults:
            self.set_defaults()

    def set(self, **kwargs):
        """Set multiple attributes and/or properties, in the given order."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise RuntimeError(f"The instrument does not have the {key} parameter.")

    def get(self, *args) -> dict:
        """Get multiple attributes and/or properties."""
        values = {}
        for key in args:
            if hasattr(self, key):
                values[key] = getattr(self, key)
            else:
                raise RuntimeError(f"The instrument does not have the {key} parameter.")
        return values

    @staticmethod
    def validate_opt(opt: Union[str, int], allowed: tuple):
        """Check that ``opt`` is one of the allowed options and return it."""
        if opt not in allowed:
            raise RuntimeError(f"Invalid option provided, choose between {allowed}")
        return opt

    @staticmethod
    def validate_range(n, n_min, n_max):
        """Clip ``n`` to the allowed range, warning if it was outside."""
        if not n_min <= n <= n_max:
            valid = max(n_min, min(n_max, n))
            log.warning(
                f"Provided value {n} not in range ({n_min}, {n_max}), will be set to {valid}."
            )
            return valid
        return n

    @property
    def defaults(self) -> dict:
        """Default values for the instrument attributes."""
        return self._defaults

    def update_defaults(self, **kwargs):
        """Validate and update the defaults dictionary."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                self._defaults[key] = value
            else:
                raise RuntimeError(f"The instrument does not have the {key} parameter.")

    def clear_defaults(self):
        """Clear the defaults dictionary."""
        self._defaults = {}

    def set_defaults(self, **kwargs):
        """Set the specified default values."""
        if kwargs:
            self.update_defaults(**kwargs)
        if self.defaults:
            self.set(**self.defaults)


class MessageInstrument(Instrument):
    """Instrument exchanging text messages through a transport.

    The transport can be given directly, or as an address string: in that case
    ``default_transport`` is built with ``transport_defaults`` updated by the extra
    keyword arguments. Nothing is opened before :meth:`connect`.
    """

    default_transport: ClassVar[Type[Transport]] = SocketTransport
    transport_defaults: ClassVar[Dict[str, Any]] = {}

    def __init__(
        self, transport: Union[Transport, str], name: str = "", **transport_kwargs
    ):
        """Initialize."""
        super().__init__(name or type(self).__name__)
        if isinstance(transport, str):
            options = {**self.transport_defaults, **transport_kwargs}
            transport = self.default_transport(transport, **options)
        elif transport_kwargs:
            raise TypeError("Transport options are only allowed with an address.")
        self.transport: Transport = transport

    @property
    def address(self) -> str:
        """Address of the instrument."""
        return self.transport.address

    @property
    def is_connected(self) -> bool:
        """Whether the transport is open."""
        return self.transport.is_connected

    def connect(self):
        """Open the transport and run the instrument setup."""
        if self.transport.is_connected:
            log.info(f"Instrument {self.name} already connected.")
            return
        self.transport.connect()
        self._after_connect()
        log.info(f"Instrument {self.name} connected successfully.")

    def disconnect(self):
        """Run the instrument teardown and close the transport."""
        if not self.transport.is_connected:
            log.info(f"No connection to close for instrument {self.name}.")
            return
        try:
            self._before_disconnect()
        finally:
            self.transport.close()
        log.info(f"Instrument {self.name} disconnected.")

    def _after_connect(self):
        """Commands sent right after opening the transport."""

    def _before_disconnect(self):
        """Commands sent right before closing the transport."""

    def write(self, cmd: str, sleep: bool = False):
        """Send a command, optionally waiting the transport delay afterwards."""
        self.transport.write(cmd)
        if sleep:
            time.sleep(self.transport.delay)

    def read(self) -> Any:
        """Read an answer."""
        return self.transport.read()

    def read_raw(self, n_bytes: int) -> bytes:
        """Read exactly ``n_bytes`` bytes."""
        return self.transport.read_raw(n_bytes)

    def query(self, cmd: str) -> Any:
        """Send a command and read the answer."""
        with self.transport.lock:
            self.write(cmd, sleep=True)
            return self.read()


class SCPIInstrument(MessageInstrument):
    """Message instrument supporting the SCPI common commands."""

    def query(self, cmd: str) -> str:
        """Send a query, which must contain "?", and read the answer."""
        if "?" not in cmd:
            raise ValueError('Query must include "?"')
        return super().query(cmd)

    def get_id(self) -> str:
        """Identification string."""
        return self.query("*IDN?")

    def reset(self, defaults: bool = True):
        """Reset the instrument, then restore the default values."""
        self.write("*RST")
        super().reset(defaults)

    def clear(self):
        """Clear status registers and error queue."""
        self.write("*CLS")

    def wait(self):
        """Execute the following commands only after the pending ones complete."""
        self.write("*WAI")

    @property
    def is_completed(self) -> bool:
        """Whether all pending operations are completed."""
        return self.query("*OPC?") == "1"
