"""List of supported instruments."""

from qinst.instruments.network.NA_N9916A import SAN9916A, VNAN9916A
from qinst.instruments.network.RS_SMA100B import SMA100B
from qinst.instruments.network.triton_ctrl import Triton
from qinst.instruments.serial.keithley6514 import Keithley6514
from qinst.instruments.serial.rf_attenuator_3494_64.rf_attenuator_3494_64 import (
    Attenuator_3494_64,
)
from qinst.instruments.serial.rf_switch_R591722600.rf_switch_R591722600 import (
    Switch_R591,
)
from qinst.instruments.serial.voltage_source_SIM928 import SIM928
from qinst.log import log

Radiall_R591722600 = Switch_R591
Kratos_349464 = Attenuator_3494_64
SRS_SIM928 = SIM928
Keithley_6514 = Keithley6514
