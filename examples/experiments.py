"""Examples of experiments written with qtics."""

from qtics import VNAN9916A, Experiment, MonitorExperiment, Triton, log


class TemperatureNotInRangeError(RuntimeError):
    """Custom exception for temperatures outside an allowed range."""

    def __init__(self, min: float, max: float, temp: float):
        """Generate error message from current temperature and limits."""
        message = f"Temperature is {temp} mK. Allowed is ({min}, {max})"
        super().__init__(message)


class VNASnapshot(Experiment):
    """Simple snapshot with vna."""

    vna = VNAN9916A("192.168.0.10", name="vna")

    def main(self):
        """Acquire VNA snapshot."""
        self.vna.connect()
        f, z = self.vna.snapshot()
        self.append_data_group("snapshot", datasets={"frequencies": f, "values": z})
        self.save_config()


class TritonMonitor(MonitorExperiment):
    """Monitor temperature of Triton cryostat."""

    cryo = Triton("192.168.0.20", name="cryo")
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
        temperature = self.cryo.get_mixing_chamber_temp() * 1e3  # K to mK
        log.info("Cryostat temperature %s mK", temperature)
        if not self.min_temp <= temperature <= self.max_temp:
            raise TemperatureNotInRangeError(self.min_temp, self.max_temp, temperature)


class MultiVNASnapshot(Experiment):
    """Multiple vna snapshots with temperature checks."""

    vna = VNAN9916A("192.168.0.10", name="vna")
    n_snapshots = 20

    def __init__(self, name: str):
        """Initialize and add the temperature monitor."""
        super().__init__(name)
        self.add_monitor(TritonMonitor("tempcheck"))

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
