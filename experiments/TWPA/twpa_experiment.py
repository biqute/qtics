"""Base class for TWPA characterization experiments."""
from time import sleep

import numpy as np

from qinst import SIM928, SMA100B, VNAN9916A
from qinst.experiment import Experiment


class TWPAExperiment(Experiment):
    """Base class for TWPA characterization experiments."""

    vna = VNAN9916A("vna", "192.168.40.10")
    pump = SMA100B("pump", "192.168.40.10")
    bias = SIM928("bias", "/dev/ttyUSB0")
    delay_between_acquisitions = 1
    f_start = 1e9
    f_stop = 10e9

    def __init__(self, name, data_file: str = ""):
        """Initialize."""
        super().__init__(name, data_file=data_file)
        self.vna.set(f_min=self.f_start, f_max=self.f_stop)

    def attribute_sweep(
        self,
        inst_name: str,
        attr_name: str,
        values: np.ndarray,
        blink_bias=True,
        **group_attributes
    ):
        """Acquire with the VNA for different values of some instrument's parameter."""
        inst = getattr(self, inst_name)
        for value in values:
            setattr(inst, attr_name, value)
            self.bias.output_on()
            sleep(0.1)
            f, z = self.vna.snapshot()
            if blink_bias:
                self.bias.output_off()
            self.append_data_group(
                str(value), {"frequencies": f, "values": z}, **group_attributes
            )
            sleep(self.delay_between_acquisitions)
