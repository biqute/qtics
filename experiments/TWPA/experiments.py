"""Collection of experiments for characterization of a TWPA."""
from time import sleep

import numpy as np
from twpa_experiment import TWPAExperiment


class S21vsBias(TWPAExperiment):
    """Response as a function of bias voltage."""

    delay_between_acquisitions = 5
    min_bias = 0
    max_bias = 2.4
    step_bias = 0.02
    vna_power = -20

    def main(self):
        """Acquire for different bias voltage values."""
        self.pump.rf_status = "OFF"
        bias_sweep = np.arange(self.min_bias, self.max_bias, self.step_bias)
        self.attribute_sweep("bias", "voltage", bias_sweep)


class GainVsFreq(TWPAExperiment):
    """Long snapshot for ripples."""

    f_start = 1e9
    f_stop = 7e9
    f_window = 3e9
    vna_average = 1
    vna_sweep_points = 1000

    def main(self):
        """Acquire with and without pump."""
        self.pump.rf_status = "ON"
        self.bias.output_on()
        sleep(0.1)
        f, z = self.vna.survey(self.f_start, self.f_stop, self.f_window)
        self.append_data_group("pump_on", datasets={"frequencies": f, "values": z})
        self.pump.rf_status = "OFF"
        self.bias.output_off()
        sleep(self.delay_between_acquisitions)
        self.bias.output_on()
        f, z = self.vna.survey(self.f_start, self.f_stop, self.f_window)
        self.append_data_group("pump_off", datasets={"frequencies": f, "values": z})
        self.bias.output_off()


class GainVsPump(TWPAExperiment):
    """Gain as a function of pump frequency."""

    min_f_pump = 7.8e9
    max_f_pump = 8.3e9
    f_pump_step = 1e7

    min_p_pump = -4
    max_p_pump = -2
    p_pump_step = 0.1

    def main(self):
        """Acquire for different pump frequency values."""
        self.bias.output_on()
        self.pump.rf_status = "OFF"
        f, z = self.vna.snapshot()
        self.append_data_group("pump_off", datasets={"frequencies": f, "values": z})
        self.bias.output_off()
        self.pump.rf_status = "ON"

        for pump_pow in np.arange(self.min_p_pump, self.max_p_pump, self.p_pump_step):
            self.pump.rf_status = "ON"
            group_name = f"pow_{pump_pow}"
            self.append_data_group(group_name, power=pump_pow)
            freq_sweep = np.arange(self.min_f_pump, self.max_f_pump, self.f_pump_step)
            self.attribute_sweep(
                "pump", "frequency", freq_sweep, parent_name=group_name
            )
            self.pump.rf_status = "OFF"
        self.bias.output_off()


class CompressionPoint(TWPAExperiment):
    """Gain as a function of signal power."""

    f_stop = 7e9
    min_vna_pow = -35
    max_vna_pow = -5
    vna_pow_step = 0.5

    def main(self):
        """Acquire for different vna power values."""
        self.pump.rf_status = "ON"
        power_sweep = np.arange(self.min_vna_pow, self.max_vna_pow, self.vna_pow_step)
        self.attribute_sweep("vna", "power", power_sweep, parent_name="pump_on")
        self.pump.rf_status = "OFF"
        self.attribute_sweep("vna", "power", power_sweep, parent_name="pump_off")
