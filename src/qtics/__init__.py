"""Qtics module."""

import importlib.metadata as im

__version__ = im.version(__package__)

from qtics.logger import qtics_log as log  # isort: skip

from qtics.experiment import BaseExperiment, Experiment, MonitorExperiment
from qtics.instruments.network.NA_N9916A import SAN9916A, VNAN9916A
from qtics.instruments.network.RS_SMA100B import SMA100B
from qtics.instruments.network.triton_ctrl import Triton
from qtics.instruments.serial.keithley2231a import Keithley2231A
from qtics.instruments.serial.keithley6514 import Keithley6514
from qtics.instruments.serial.rf_attenuator_3494_64.rf_attenuator_3494_64 import (
    Attenuator_3494_64,
)
from qtics.instruments.serial.rf_switch_R591722600.rf_switch_R591722600 import (
    Switch_R591,
)
from qtics.instruments.serial.synth_FSL0010 import FSL0010
from qtics.instruments.serial.voltage_source_SIM928 import SIM928

Radiall_R591722600 = Switch_R591
Kratos_349464 = Attenuator_3494_64
SRS_SIM928 = SIM928
Keithley_6514 = Keithley6514
Keithley_2231A = Keithley2231A
