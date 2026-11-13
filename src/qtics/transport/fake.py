"""Fake transport for tests: records commands and replies with scripted answers."""

from typing import Callable, Dict, List, Optional, Union

from qtics.transport.base import Transport

Answer = Union[str, bytes, Callable[[str], Union[str, bytes]]]


class FakeTransport(Transport):
    """In-memory transport.

    Every written command is appended to :attr:`written`. If the command is a key of
    ``answers`` its answer is queued for reading: strings are returned by
    :meth:`read`, bytes by :meth:`read_raw`, callables are called with the command.
    Queries (commands containing "?") without a scripted answer get ``default``
    (if not None); other commands get no answer.
    """

    def __init__(
        self,
        answers: Optional[Dict[str, Answer]] = None,
        default: Optional[Answer] = None,
        address: str = "fake",
        terminator: str = "\n",
    ):
        """Initialize."""
        super().__init__(address, timeout=0, terminator=terminator, delay=0)
        self.answers: Dict[str, Answer] = dict(answers or {})
        self.default = default
        self.written: List[str] = []
        self._pending: List[str] = []
        self._raw = b""
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Whether the fake channel is open."""
        return self._connected

    def connect(self):
        """Open the fake channel."""
        self._connected = True

    def close(self):
        """Close the fake channel."""
        self._connected = False

    def _write_bytes(self, data: bytes):
        cmd = data.decode()[: -len(self.terminator) or None]
        self.written.append(cmd)
        answer: Optional[Answer] = self.answers.get(
            cmd, self.default if "?" in cmd else None
        )
        if callable(answer):
            answer = answer(cmd)
        if isinstance(answer, bytes):
            self._raw += answer
        elif answer is not None:
            self._pending.append(answer)

    def read(self) -> str:
        """Return the oldest pending answer, empty string if none."""
        return self._pending.pop(0) if self._pending else ""

    def read_raw(self, n_bytes: int) -> bytes:
        """Return the next ``n_bytes`` of queued raw data."""
        data, self._raw = self._raw[:n_bytes], self._raw[n_bytes:]
        return data
