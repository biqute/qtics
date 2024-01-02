"""
Base class for instruments communicating via network connection.

.. module:: network_inst.py
.. moduleauthor:: Pietro Campana <campana.pietro@campus.unimib.it>

The code was partially taken from https://github.com/morgan-at-keysight/socketscpi
"""
import ipaddress
import socket
import time

from qtics import log
from qtics.instrument import Instrument


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
        log.info(f"Instrument {self.name} connected succesfully.")

    def disconnect(self):
        """Disconnect from the device."""
        if self.__is_connected:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.__is_connected = False
            log.info(f"Instrument {self.name} disconnected.")

    def read(self) -> str:
        """Read the output buffer of the instrument."""
        response = b""
        try:
            while response[-1:] != b"\n":
                response += self.socket.recv(1024)
        except TimeoutError as exc:
            raise exc
        res = response.decode("utf-8").strip("\n")
        log.debug(f"READ: {res}")
        return res

    def write(self, cmd: str, sleep=False):
        """Write a message to the serial port."""
        log.debug(f"WRITE: {cmd}")
        self.socket.sendall((cmd + "\n").encode())
        if sleep:
            time.sleep(self.sleep)

    def query(self, cmd: str) -> str:
        """Send a message, then read from the serial port."""
        if "?" not in cmd:
            raise ValueError('Query must include "?"')
        self.write(cmd, True)
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
