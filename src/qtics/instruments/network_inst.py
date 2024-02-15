"""
Base class for instruments communicating via network connection.

.. module:: network_inst.py
.. moduleauthor:: Pietro Campana <campana.pietro@campus.unimib.it>

The code was partially taken from https://github.com/morgan-at-keysight/socketscpi
"""

import ipaddress
import socket
import time
from typing import Optional

from qtics import log
from qtics.instruments import Instrument


class NetworkInst(Instrument):
    """Base class for instruments communicating via network connection."""

    def __init__(
        self,
        name: str,
        address: str,
        port: int = 5025,  # Keysight instruments standard port
        timeout: int = 10,
        sleep: float = 0.1,
        no_delay: bool = True,
    ):
        """Initialize.

        :param name: instrument identifier
        :param address: ip address of the instrument
        :param port: port for instrument connection
        :param timeout: timeout for connection
        :param sleep: default sleep value
        :param no_delay: socket no_delay
        """
        super().__init__(name, address)

        # Validate IP
        _ = ipaddress.ip_address(address)
        self.port = port
        self.sleep = sleep
        self.timeout = timeout
        self.no_delay = no_delay
        self.__is_connected = False
        self.socket: Optional[socket.socket] = None

    def __del__(self):
        """Delete the object."""
        self.disconnect()

    def connect(self):
        """Connect to the device."""
        if not self.__is_connected:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_NODELAY, int(self.no_delay)
            )
            self.socket.connect((self.address, self.port))
            self.__is_connected = True
            log.info(f"Instrument {self.name} connected successfully.")
        else:
            log.info(f"Instrument {self.name} already connected.")

    def disconnect(self):
        """Disconnect from the device."""
        if self.__is_connected and self.socket is not None:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.__is_connected = False
            log.info(f"Instrument {self.name} disconnected.")
        else:
            log.info(f"No connection to close for instrument {self.name}.")

    def read(self) -> str:
        """Read the output buffer of the instrument.

        :return: output in string form (UTF-8)
        """
        response = b""
        if self.socket is None:
            log.warning("Socket not initialized.")
            return ""
        try:
            while response[-1:] != b"\n":
                response += self.socket.recv(1024)
        except TimeoutError as exc:
            raise exc
        res = response.decode("utf-8").strip("\n")
        log.debug(f"READ: {res}")
        return res

    def write(self, cmd: str, sleep: bool = False):
        """Write a message to the serial port.

        :param cmd: command in string form
        :param sleep: if true, sleeps after writing
        """
        if self.socket is None:
            log.warning("Socket not initialized.")
            return
        log.debug(f"WRITE: {cmd}")
        self.socket.sendall((cmd + "\n").encode())
        if sleep:
            time.sleep(self.sleep)

    def query(self, cmd: str) -> str:
        """Send a message, then read from the serial port.

        :param cmd: command in string form (must have question mark)
        :return: output in string form (UTF-8)
        """
        if "?" not in cmd:
            raise ValueError('Query must include "?"')
        self.write(cmd, True)
        return self.read()
