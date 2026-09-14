"""
Base class for instruments communicating via GPIB (IEEE-488).

Uses pyvisa as the backend. Requires a VISA runtime (e.g. NI-VISA or
linux-gpib) and the ``pyvisa`` package to be installed.
"""

import time

import pyvisa

from qtics import log
from qtics.instruments.instrument import Instrument


class GpibInst(Instrument):
    """Base class for GPIB instruments accessed through pyvisa.

    Parameters
    ----------
    name:
        Human-readable label for the instrument.
    address:
        GPIB primary address (integer, 1-30).
    board:
        GPIB board / interface index (default 0).
    timeout:
        Visa timeout in milliseconds (default 10 000 ms).
    sleep:
        Pause inserted after every write, in seconds (default 0.1 s).
    """

    def __init__(
        self,
        name: str,
        address: int,
        board: int = 0,
        timeout: int = 10_000,
        sleep: float = 0.1,
    ):
        # Store address as string for the Instrument base class, but keep
        # the integer version for building the VISA resource string.
        super().__init__(name, str(address))
        self._gpib_address = int(address)
        self._board = board
        self.timeout = timeout
        self.sleep = sleep
        self._rm: pyvisa.ResourceManager | None = None
        self._inst: pyvisa.resources.GPIBInstrument | None = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    @property
    def resource_string(self) -> str:
        """VISA resource string for this instrument."""
        return f"GPIB{self._board}::{self._gpib_address}::INSTR"

    def connect(self):
        """Open a VISA session to the instrument."""
        if self._inst is not None:
            log.info(f"Instrument {self.name} already connected.")
            return
        self._rm = pyvisa.ResourceManager()
        self._inst = self._rm.open_resource(self.resource_string)
        self._inst.timeout = self.timeout
        log.info(f"Instrument {self.name} connected ({self.resource_string}).")

    def disconnect(self):
        """Close the VISA session."""
        if self._inst is not None:
            self._inst.close()
            self._inst = None
        if self._rm is not None:
            self._rm.close()
            self._rm = None
        log.info(f"Instrument {self.name} disconnected.")

    def __del__(self):
        """Ensure the session is closed on garbage collection."""
        self.disconnect()

    # ------------------------------------------------------------------
    # Low-level I/O
    # ------------------------------------------------------------------

    def write(self, cmd: str, sleep: bool = False):
        """Send a command string to the instrument."""
        if self._inst is None:
            raise RuntimeError(f"Instrument {self.name} is not connected.")
        log.debug(f"WRITE: {cmd}")
        self._inst.write(cmd)
        if sleep:
            time.sleep(self.sleep)

    def read(self) -> str:
        """Read a response string from the instrument."""
        if self._inst is None:
            raise RuntimeError(f"Instrument {self.name} is not connected.")
        response = self._inst.read().strip()
        log.debug(f"READ:  {response}")
        return response

    def query(self, cmd: str) -> str:
        """Send a command and immediately read the response."""
        if "?" not in cmd:
            raise ValueError('Query command must contain "?".')
        self.write(cmd, sleep=True)
        return self.read()
