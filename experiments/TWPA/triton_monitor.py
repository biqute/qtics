"""Monitor experiment class for temperature check."""
from time import sleep

from qtics import Triton, log
from qtics.experiment import MonitorExperiment


class TritonMonitor(MonitorExperiment):
    """Monitor temperature of Triton cryostat."""

    cryo: Triton

    def __init__(
        self,
        name: str,
        min_temp: float = 0,  # minimum mixing chamber temperature in mK
        max_temp: float = 80,  # max mixing chamber temperature in mK
        sleep: int = 5,
        **triton_kwargs,
    ):
        """Initialize."""
        super().__init__(name)
        if min_temp >= max_temp:
            raise ValueError("Minimum allowed temperature must be lower than maximum.")
        self.min_temp = min_temp
        self.max_temp = max_temp
        log.info("Allowed temperature range %f-%f mK set.", min_temp, max_temp)
        self.sleep = sleep
        self.add_instrument(Triton("cryo", **triton_kwargs))

    def main(self):
        """Execute main part of the experiment."""
        temperature = self.cryo.get_mixing_chamber_temp()
        log.info("Cryostat temperature %s mK", temperature)
        if temperature < self.min_temp or temperature > self.max_temp:
            raise Exception("Temperature %s mK out of allowed range.", temperature)
        sleep(self.sleep)
