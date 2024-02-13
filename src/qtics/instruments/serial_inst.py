"""Base instrument for serial connections."""

import time
from typing import Literal

import serial

from qtics import log
from qtics.instruments import Instrument


class SerialInst(Instrument):
    """Base class for instrument controlled via serial connection."""

    def __init__(
        self,
        name: str,
        address: str,
        baudrate: int = 9600,
        bytesize: int = serial.EIGHTBITS,
        parity: Literal["N"] = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        timeout: int = 10,
        sleep: float = 0.1,
    ):
        """Initialize."""
        super().__init__(name, address)

        self.serial = serial.Serial()
        self.serial.port = address
        self.serial.baudrate = baudrate
        self.serial.bytesize = bytesize
        self.serial.parity = parity
        self.serial.stopbits = stopbits
        self.serial.timeout = timeout

        self.sleep = sleep

    def __del__(self):
        """Disconnect and delete."""
        self.disconnect()

    def connect(self):
        """Connect to the device."""
        if not self.serial.is_open:
            self.serial.open()
            log.info(f"Instrument {self.name} connected successfully.")
        else:
            log.info(f"Instrument {self.name} already connected.")

    def disconnect(self):
        """Disconnect from the device."""
        if self.serial.is_open:
            self.serial.close()
            log.info(f"Instrument {self.name} disconnected.")
        else:
            log.info(f"No connection to close for instrument {self.name}.")

    def write(self, cmd, sleep=False):
        """Write a message to the serial port."""
        if self.serial.is_open:
            log.debug(f"WRITE: {cmd}")
            self.serial.write((cmd + "\n").encode())
            if sleep:
                time.sleep(self.sleep)

    def read(self) -> str:
        """Read a message from the serial port."""
        if self.serial.is_open:
            raw = self.serial.read(self.serial.in_waiting)
            res = raw.decode("utf-8").strip("\n")
            log.debug(f"READ: {res}")
            return res
        return ""

    def query(self, cmd) -> str:
        """Send a message, then read from the serial port."""
        self.write(cmd, sleep=True)
        return self.read()
