"""Collection of experiments for characterization of a TWPA."""
from datetime import datetime
from time import sleep

import numpy as np
from triton_monitor import TritonMonitor
from twpa_experiment import TWPAExperiment

from qinst import Triton, log


class S21vsTemp(TWPAExperiment):
    """Response as a function of cryostat's temperature."""

    cryo = Triton("triton")
    total_time = 60 * 10

    def main(self):
        """Save data for different temperatures."""
        self.cryo.connect()
        for _ in range(int(self.total_time / self.delay_between_acquisitions)):
            date = str(datetime.now())
            temperature = self.cryo.get_mixing_chamber_temp()
            log.info(f"Temperature: {round(temperature, 2)} mK.")
            f, z = self.vna.snapshot()
            self.append_data_group(
                date, {"frequencies": f, "values": z}, temperature=temperature
            )
            sleep(self.delay_between_acquisitions)


class S21vsBias(TWPAExperiment):
    """Response as a function of bias voltage."""

    min_bias = 0
    max_bias = 3
    bias_step = 0.05

    def __init__(self, name, data_file: str = ""):
        """Initialize."""
        super().__init__(name, data_file)
        self.add_monitor(TritonMonitor("tempcheck", max_temp=500))
        self.delay_between_acquisitions = 10

    def main(self):
        """Acquire for different bias voltage values."""
        self.all_instruments("connect")
        bias_sweep = np.arange(self.min_bias, self.max_bias, self.bias_step)
        self.attribute_sweep("bias", "voltage", bias_sweep)


class GainVsPumpFreq(TWPAExperiment):
    """Gain as a function of pump frequency."""

    min_f_pump = 7.9e9
    max_f_pump = 8.3e9
    f_pump_step = 2e7

    def __init__(self, name, data_file: str = ""):
        """Initialize."""
        super().__init__(name, data_file)
        self.add_monitor(TritonMonitor("tempcheck"))

    def main(self):
        """Acquire for different pump frequency values."""
        self.all_instruments("connect")
        freq_sweep = np.arange(self.min_f_pump, self.max_f_pump, self.f_pump_step)
        self.attribute_sweep("pump", "frequency", freq_sweep)


class CompressionPoint(TWPAExperiment):
    """Gain as a function of signal power."""

    min_vna_pow = -60
    max_vna_pow = -10
    vna_pow_step = 2

    def __init__(self, name, data_file: str = ""):
        """Initialize."""
        super().__init__(name, data_file)
        self.add_monitor(TritonMonitor("tempcheck"))

    def main(self):
        """Acquire for different vna power values."""
        self.all_instruments("connect")
        power_sweep = np.arange(self.min_vna_pow, self.max_vna_pow, self.vna_pow_step)
        self.attribute_sweep("vna", "power", power_sweep)
