"""Examples of experiments written with qtics."""

from time import sleep

from qtics import VNAN9916A, Experiment, MonitorExperiment, Triton, log


class VNASnapshot(Experiment):
    """Simple snapshot with vna."""

    vna = VNAN9916A("vna", "address")

    def main(self):
        """Acquire VNA snapshot."""
        self.vna.connect()
        f, z = self.vna.snapshot()
        self.append_data_group("snapshot", datasets={"frequencies": f, "values": z})
        self.save_config()


class TritonMonitor(MonitorExperiment):
    """Monitor temperature of Triton cryostat."""

    cryo = Triton("name", "address")
    sleep = 5

    def __init__(
        self,
        name: str,
        min_temp: float = 0,  # minimum mixing chamber temperature in mK
        max_temp: float = 80,  # max mixing chamber temperature in mK
    ):
        """Initialize."""
        super().__init__(name)
        if min_temp >= max_temp:
            raise ValueError("Minimum allowed temperature must be lower than maximum.")
        self.min_temp = min_temp
        self.max_temp = max_temp
        log.info("Allowed temperature range %f-%f mK set.", min_temp, max_temp)

    def main(self):
        """Execute main part of the experiment."""
        temperature = self.cryo.get_mixing_chamber_temp()
        log.info("Cryostat temperature %s mK", temperature)
        if self.min_temp > temperature > self.max_temp:
            raise Exception("Temperature %s mK out of allowed range.", temperature)
        sleep(self.sleep)


class MultiVNASnapshot(Experiment):
    """Multiple vna snapshots with temperature checks."""

    vna = VNAN9916A("vna", "address")
    monitors = [TritonMonitor("tempcheck")]
    n_snapshots = 20

    def main(self):
        """Acquire VNA snapshot."""
        self.vna.connect()
        for i in range(self.n_snapshots):
            freqs, vals = self.vna.snapshot()
            self.append_data_group(
                f"snapshot_{i}", datasets={"frequencies": freqs, "values": vals}
            )
            if self.monitor_failed():
                return
        self.save_config()
