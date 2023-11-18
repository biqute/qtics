import ipaddress
import socket
import time

from qinst.instrument import Instrument


class NetworkInst(Instrument):
    """Base class for instruments communicating via network connection."""

    def __init__(
        self,
        name: str,
        address: str,
        port: int = 5025,  # Keysight instruments standard port
        timeout: int = 10,
        sleep: float = 0.1,
        noDelay=True,
    ):
        super().__init__(name, address)

        # Validate IP
        ipaddress.ip_address(address)
        self.port = port
        self.timeout = timeout
        self.sleep = sleep

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if noDelay:
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.socket.setblocking(False)
        self.socket.settimeout(timeout)

    def __del__(self):
        self.disconnect()

    def connect(self):
        """Connect to the device."""
        self.socket.connect((self.address, self.port))

    def disconnect(self):
        """Disconnect from the device."""
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def read(self) -> str:
        """Read the output buffer of the instrument."""
        response = b""
        try:
            while response[-1:] != b"\n":
                response += self.socket.recv(1024)
        except socket.timeout:
            raise TimeoutError("Reached timeout limit.")
        return response.decode("utf-8").strip()

    def write(self, cmd: str):
        """Write a message to the serial port."""
        self.socket.sendall((cmd + "\n").encode())

    def query(self, cmd: str) -> str:
        """Send a message, then read from the serial port."""
        if "?" not in cmd:
            raise ValueError('Query must include "?"')
        self.write(cmd)
        time.sleep(self.sleep)
        return self.read()
