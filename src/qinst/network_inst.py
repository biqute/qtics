"""
Base class for instruments communicating via network connection.

.. module:: network_inst.py
.. moduleauthor:: Pietro Campana <campana.pietro@campus.unimib.it>
The code was partially taken from https://github.com/morgan-at-keysight/socketscpi
"""
import ipaddress
import socket
import time

from qinst import log
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
        no_delay=True,
    ):
        """Initialize."""
        super().__init__(name, address)

        # Validate IP
        _ = ipaddress.ip_address(address)
        self.port = port
        self.sleep = sleep
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.timeout = timeout
        self.no_delay = no_delay
        self.__is_connected = False

    def __del__(self):
        """Delete the object."""
        self.disconnect()

    def connect(self):
        """Connect to the device."""
        self.socket.connect((self.address, self.port))
        self.__is_connected = True

    def disconnect(self):
        """Disconnect from the device."""
        if self.__is_connected:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.__is_connected = False

    def read(self) -> str:
        """Read the output buffer of the instrument."""
        response = b""
        try:
            while response[-1:] != b"\n":
                response += self.socket.recv(1024)
        except socket.timeout:
            raise TimeoutError("Reached timeout limit.")
        return response.decode("utf-8").strip("\n")

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

    @property
    def no_delay(self):
        """If True, send data immediately without concatenating multiple packets together."""
        return bool(self.socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY))

    @no_delay.setter
    def no_delay(self, opt: bool):
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, int(opt))

    @property
    def timeout(self):
        """Maximum waiting time for connection and communication."""
        return self.socket.timeout

    @timeout.setter
    def timeout(self, nsec: float):
        self.socket.settimeout(nsec)

    def validate_opt(self, opt: str, allowed: tuple):
        """Check if provided option is between allowed ones."""
        if opt not in allowed:
            raise RuntimeError(f"Invalid option provided, choose between {allowed}")

    def validate_range(self, n, n_min, n_max):
        """Check if provided number is in allowed range."""
        if not n_min < n < n_max:
            valid = max(n_min, min(n_max, n))
            log.warning(
                f"Provided value {n} not in range ({n_min}, {n_max}), will be set to {valid}."
            )
            return valid
        return n
