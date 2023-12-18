"""Base class for TWPA characterization experiments."""
from time import sleep

import numpy as np
from triton_monitor import TritonMonitor

from qinst import SIM928, SMA100B, VNAN9916A
from qinst.experiment import Experiment


class TWPAExperiment(Experiment):
    """Base class for TWPA characterization experiments."""

    vna = VNAN9916A("vna", "192.168.40.10")
    pump = SMA100B("pump", "192.168.40.10")
    bias = SIM928("bias", "/dev/ttyUSB0")
    delay_between_acquisitions = 1
    resistance = 1997
    f_start = 1e9
    f_stop = 10e9
    vna_power = -45
    sweep_points = 5000
    IFBW = 1000
    vna_average = 1
    pump_freq = 7.95e9
    pump_power = -2.5
    bias_voltage = 2.4

    def __init__(self, name, data_file: str = ""):
        """Initialize."""
        super().__init__(name, data_file=data_file)
        self.vna.set(
            f_min=self.f_start,
            f_max=self.f_stop,
            power=self.vna_power,
            sweep_points=self.sweep_points,
            IFBW=self.IFBW,
            average=self.vna_average,
        )
        self.pump.connect()
        self.pump.set(
            f_mode="CW",
            f_fixed=self.pump_freq,
            p_mode="CW",
            p_unit="DBM",
            p_fixed=self.pump_power,
        )
        self.bias.connect()
        self.bias.voltage = self.bias_voltage
        self.add_monitor(TritonMonitor("tempcheck"))

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
        config_attr = {
            key: value
            for key, value in self.__dict__.items()
            if key not in self.inst_names and not key.startswith("_")
        }
        self.append_data_group("config", **config_attr)
