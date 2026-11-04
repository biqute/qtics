"""Base transport: the channel used to exchange messages with an instrument."""

import time
from abc import ABC, abstractmethod
from threading import RLock

from qtics import log


class Transport(ABC):
    """Message channel to an instrument.

    Opening the channel is deferred to :meth:`connect`, creating a transport never
    touches the hardware.
    """

    def __init__(
        self,
        address: str,
        timeout: float = 10,
        terminator: str = "\n",
        delay: float = 0.1,
    ):
        """Initialize.

        Args:
            address: address of the instrument (IP, hostname or serial port).
            timeout: read timeout in seconds.
            terminator: string appended to written commands and ending answers.
            delay: seconds to wait between a write and the following read in a query.
        """
        self.address = address
        self.timeout = timeout
        self.terminator = terminator
        self.delay = delay
        # A query is a write followed by a read: the lock makes it atomic when
        # the instrument is shared between threads (e.g. experiment monitors).
        self.lock = RLock()

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the channel is open."""

    @abstractmethod
    def connect(self):
        """Open the channel."""

    @abstractmethod
    def close(self):
        """Close the channel."""

    @abstractmethod
    def _write_bytes(self, data: bytes):
        """Send raw bytes."""

    @abstractmethod
    def read(self) -> str:
        """Read an answer, without the terminator."""

    @abstractmethod
    def read_raw(self, n_bytes: int) -> bytes:
        """Read exactly ``n_bytes`` bytes."""

    def write(self, cmd: str):
        """Send a command, appending the terminator."""
        if not self.is_connected:
            raise ConnectionError(f"Transport to {self.address} is not connected.")
        log.debug(f"WRITE: {cmd}")
        self._write_bytes((cmd + self.terminator).encode())

    def query(self, cmd: str) -> str:
        """Send a command, wait ``delay`` and read the answer."""
        with self.lock:
            self.write(cmd)
            time.sleep(self.delay)
            return self.read()

    def __del__(self):
        """Close the channel, without sending any instrument command."""
        try:
            self.close()
        except Exception:  # pylint: disable=broad-except
            pass
