"""TCP socket transport, e.g. for raw SCPI over LAN.

The code was partially taken from https://github.com/morgan-at-keysight/socketscpi
"""

import socket
from typing import Optional

from qtics import log
from qtics.transport.base import Transport


class SocketTransport(Transport):
    """Raw TCP socket transport."""

    def __init__(
        self,
        address: str,
        port: int = 5025,  # Keysight instruments standard port
        timeout: float = 10,
        terminator: str = "\n",
        delay: float = 0.1,
        no_delay: bool = True,
    ):
        """Initialize, ``address`` is an IP or a hostname."""
        super().__init__(address, timeout, terminator, delay)
        self.port = port
        self.no_delay = no_delay
        self.socket: Optional[socket.socket] = None

    @property
    def is_connected(self) -> bool:
        """Whether the socket is open."""
        return self.socket is not None

    def connect(self):
        """Open the socket."""
        if self.socket is not None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, int(self.no_delay))
        sock.connect((self.address, self.port))
        self.socket = sock

    def close(self):
        """Close the socket."""
        if self.socket is None:
            return
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError as exc:
            log.debug(f"Socket shutdown failed: {exc}")
        self.socket.close()
        self.socket = None

    def _write_bytes(self, data: bytes):
        assert self.socket is not None
        self.socket.sendall(data)

    def read(self) -> str:
        """Read until the terminator."""
        if self.socket is None:
            raise ConnectionError(f"Transport to {self.address} is not connected.")
        end = self.terminator.encode()
        response = b""
        while not response.endswith(end):
            chunk = self.socket.recv(1024)
            if not chunk:
                raise ConnectionError(f"Connection to {self.address} closed.")
            response += chunk
        res = response[: -len(end)].decode("utf-8")
        log.debug(f"READ: {res}")
        return res

    def read_raw(self, n_bytes: int) -> bytes:
        """Read exactly ``n_bytes`` bytes."""
        if self.socket is None:
            raise ConnectionError(f"Transport to {self.address} is not connected.")
        data = bytearray(n_bytes)
        view = memoryview(data)
        while n_bytes:
            received = self.socket.recv_into(view, n_bytes)
            if not received:
                raise ConnectionError(f"Connection to {self.address} closed.")
            view = view[received:]
            n_bytes -= received
        return bytes(data)
