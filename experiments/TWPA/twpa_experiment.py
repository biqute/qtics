"""Base class for TWPA characterization experiments."""
from time import sleep

import numpy as np
from triton_monitor import TritonMonitor

from qtics import SIM928, SMA100B, VNAN9916A
from qtics.experiment import Experiment


class TWPAExperiment(Experiment):
    """Base class for TWPA characterization experiments."""

    vna = VNAN9916A("vna", "192.168.40.10")
    pump = SMA100B("pump", "192.168.40.15")
    bias = SIM928("bias", "COM34")
    delay_between_acquisitions = 1
    resistance = 1997

    def __init__(self, name, data_file: str = "", data_dir="data"):
        """Initialize."""
        super().__init__(name, data_file=data_file, data_dir=data_dir)
        self.add_monitor(TritonMonitor("tempcheck"))

    def config_instruments(self):
        """Configure instruments defaults."""
        self.all_instruments("connect")
        self.vna.set_defaults(
            f_min=1e9, f_max=10e9, power=-45, sweep_point=5000, IFBW=1000, average=1
        )
        self.pump.set_defaults(f_fixed=7.95e9, p_fixed=-2.5)
        self.bias.set_defaults(voltage=2.4)

    def attribute_sweep(
        self,
        inst_name: str,
        attr_name: str,
        values: np.ndarray,
        blink_bias=True,
        parent_name="",
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
                str(value),
                parent_name="",
                datasets={"frequencies": f, "values": z},
                **group_attributes
            )
            if self.monitor_failed():
                self.all_instruments("safe_reset")
                return
            sleep(self.delay_between_acquisitions)

    def run(self):
        """Run experiment."""
        super().run()
        self.save_config()
