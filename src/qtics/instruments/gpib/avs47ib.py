"""
Driver for the Picowatt AVS-47B resistance bridge with AVS47-IB GPIB interface.

Hardware:  AVS-47B AC resistance bridge (Picowatt)
Interface: AVS47-IB two-stage GPIB computer interface (firmware >= 3R4)
Bus:       IEEE-488 (GPIB), factory default device address 20

The AVS47-IB follows IEEE-488.2 with minor deviations.  All commands are
case-insensitive and strictly sequential: the previous operation is always
fully completed before the next command is processed.

References
----------
* AVS47-IB Instruction Manual, Picowatt, rev. 2015-02-17 (firmware 3R4)
* TS-530A Temperature Controller Instruction Manual, Picowatt, rev. 1999-07-28
"""

import time
from typing import TYPE_CHECKING

from qtics import log

if TYPE_CHECKING:
    from qtics.calibration.ruox import RuOx
from qtics.instruments.gpib_inst import GpibInst

# ---------------------------------------------------------------------------
# Enumeration-style constants for the bridge settings
# ---------------------------------------------------------------------------

# RAN [0..7]: range index -> full-scale resistance
RANGES = {
    0: None,  # no range connected (power-on default; do not use)
    1: 2,  # 2 Ω
    2: 20,  # 20 Ω
    3: 200,  # 200 Ω
    4: 2_000,  # 2 kΩ
    5: 20_000,  # 20 kΩ
    6: 200_000,  # 200 kΩ
    7: 2_000_000,  # 2 MΩ
}

# EXC [0..7]: excitation index -> nominal excitation voltage
EXCITATIONS = {
    0: 0,  # no excitation
    1: 3e-6,  # 3 µV
    2: 10e-6,  # 10 µV
    3: 30e-6,  # 30 µV
    4: 100e-6,  # 100 µV
    5: 300e-6,  # 300 µV
    6: 1e-3,  # 1 mV
    7: 3e-3,  # 3 mV
}

# INP [0..2]: input source
INP_ZERO = 0  # bridge input grounded (offset measurement)
INP_MEASURE = 1  # measurement (sensor selected by MUX)
INP_CAL = 2  # internal 100 Ω calibration reference

# ADC overload sentinel value (raw integer)
ADC_OVERLOAD = 20001
# RES overload sentinel value (Ohms)
RES_OVERLOAD = 2.0001e6


class AVS47IB(GpibInst):
    """Picowatt AVS-47B resistance bridge via AVS47-IB GPIB interface.

    The AVS47-IB wraps the analogue AVS-47B into a fully computer-controlled
    instrument.  It also forwards commands to the optional TS-530A temperature
    controller when the two units are connected with the 37-way ribbon cable.

    Parameters
    ----------
    name:
        Human-readable label (e.g. ``"avs47"``).
    address:
        GPIB primary address.  Factory default is **20**.
    board:
        GPIB board / interface index (default 0).
    timeout:
        VISA timeout in milliseconds (default 10 000 ms).
    sleep:
        Pause after every write in seconds (default 0.1 s).

    Notes
    -----
    ``*IDN?`` response format (IEEE-488.2)::

        *IDN PICOWATT,AVS47-IB,0,<firmware_version>

    This is the only AVS47-IB query that returns a string; all others are
    numeric.

    **Safe channel-change sequence** (manual recommendation)::

        bridge.input = INP_ZERO          # disconnect input
        bridge.channel = n               # select new MUX channel
        bridge.range = r                 # set range
        bridge.excitation = e            # set excitation
        time.sleep(2)
        bridge.input = INP_MEASURE       # re-enable input

    The :meth:`set_channel` helper performs this sequence automatically.
    """

    #: Factory-default GPIB address (stored in EEPROM, writable via IBA).
    DEFAULT_ADDRESS: int = 20

    def __init__(
        self,
        name: str = "avs47",
        address: int = DEFAULT_ADDRESS,
        board: int = 0,
        timeout: int = 10_000,
        sleep: float = 0.1,
        thermometer: "RuOx | None" = None,
    ):
        super().__init__(name, address, board, timeout, sleep)
        self.thermometer = thermometer

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self):
        """Open a VISA session, clear status registers, and take remote control."""
        super().connect()
        self.write("*CLS")
        self.remote = True
        log.info(f"{self.name}: ready (remote mode).")

    def disconnect(self):
        """Release front-panel controls to local mode, then close session."""
        if self._inst is not None:
            try:
                self.remote = False
            except Exception:
                pass
        super().disconnect()

    # ------------------------------------------------------------------
    # Identification / status
    # ------------------------------------------------------------------

    def get_id(self) -> str:
        """Return the IEEE-488.2 identification string.

        Returns
        -------
        str
            E.g. ``"*IDN PICOWATT,AVS47-IB,0,3.1"``
        """
        return self.query("*IDN?")

    def self_test(self) -> int:
        """Run the built-in self-test and return the error byte.

        A return value of 0 means all checks passed.  96 (bits 5+6) is the
        minimum expected value when no TS-530A is connected.

        .. warning::
            Do not run during an experiment.  Resets both AVS-47B and TS-530A.
        """
        return int(self.query("*TST?").split()[-1])

    def clear_status(self):
        """Clear all status registers (``*CLS``)."""
        self.write("*CLS")

    def reset(self, defaults: bool = True):
        """Reset both AVS-47B and TS-530A to their default states (``*RST``).

        After reset: range 2 MΩ, excitation 3 µV, input grounded.
        """
        self.write("*RST")
        if defaults:
            self.set_defaults()

    # ------------------------------------------------------------------
    # Remote / local mode
    # ------------------------------------------------------------------

    @property
    def remote(self) -> bool:
        """True when the bridge is in remote (computer-controlled) mode."""
        return bool(int(self.query("REM?").split()[-1]))

    @remote.setter
    def remote(self, state: bool):
        self.write(f"REM {int(state)}")

    # ------------------------------------------------------------------
    # AVS-47B bridge settings
    # ------------------------------------------------------------------

    @property
    def input(self) -> int:
        """Input source: 0 = zero (gnd), 1 = measure, 2 = calibrate."""
        return int(self.query("INP?").split()[-1])

    @input.setter
    def input(self, value: int):
        value = self.validate_range(value, 0, 2)
        self.write(f"INP {value}")

    @property
    def channel(self) -> int:
        """Multiplexer channel (0–7)."""
        return int(self.query("MUX?").split()[-1])

    @channel.setter
    def channel(self, value: int):
        value = self.validate_range(value, 0, 7)
        self.write(f"MUX {value}")

    @property
    def range(self) -> int:
        """Resistance range index (0–7).  See :data:`RANGES` for mapping."""
        return int(self.query("RAN?").split()[-1])

    @range.setter
    def range(self, value: int):
        value = self.validate_range(value, 0, 7)
        self.write(f"RAN {value}")

    @property
    def excitation(self) -> int:
        """Excitation index (0–7).  See :data:`EXCITATIONS` for mapping."""
        return int(self.query("EXC?").split()[-1])

    @excitation.setter
    def excitation(self, value: int):
        value = self.validate_range(value, 0, 7)
        self.write(f"EXC {value}")

    @property
    def display(self) -> int:
        """Display selector (0–7; 0 = R, 7 = TS-530 set point)."""
        return int(self.query("DIS?").split()[-1])

    @display.setter
    def display(self, value: int):
        value = self.validate_range(value, 0, 7)
        self.write(f"DIS {value}")

    @property
    def autorange(self) -> bool:
        """True when software autoranging is enabled."""
        return bool(int(self.query("ARN?").split()[-1]))

    @autorange.setter
    def autorange(self, state: bool):
        self.write(f"ARN {int(state)}")

    @property
    def stabilization_delay(self) -> int:
        """Autoranging stabilization delay in seconds (1–100)."""
        return int(self.query("SDY?").split()[-1])

    @stabilization_delay.setter
    def stabilization_delay(self, seconds: int):
        seconds = self.validate_range(seconds, 1, 100)
        self.write(f"SDY {seconds}")

    @property
    def reference_source(self) -> int:
        """Reference source: 0 = memory DAC, 1 = direct potentiometer."""
        return int(self.query("RFS?").split()[-1])

    @property
    def magnifier(self) -> int:
        """Difference magnifier: 0 = ΔR×1, 1 = ΔR×10."""
        return int(self.query("MAG?").split()[-1])

    def set_reference(self, value: int):
        """Set the difference reference DAC value (0–20000).

        The value is internally rounded to the nearest multiple of 5.
        There is no corresponding query; use ``DIS 3; DLY 1; ADC; ADC?``
        to read back the actual reference voltage.

        Parameters
        ----------
        value:
            Reference DAC value.  19999 corresponds to ≈ 2.0 V.
        """
        value = self.validate_range(value, 0, 20000)
        self.write(f"REF {value}")

    def zero_difference(self):
        """Take the current reading as the deviation reference (``ZDR`` macro)."""
        self.write("ZDR")

    # ------------------------------------------------------------------
    # Measurement
    # ------------------------------------------------------------------

    def trigger_adc(self):
        """Trigger a single A/D conversion (takes up to 400 ms)."""
        self.write("ADC")

    def read_adc(self) -> int:
        """Return the raw A/D result from the last :meth:`trigger_adc` call.

        Uses serial polling to wait until the result is in the output queue
        before reading, so this method is safe to call immediately after
        :meth:`trigger_adc` without any sleep.

        Returns
        -------
        int
            -19999 to 19999; :data:`ADC_OVERLOAD` (20001) on overload.
        """
        time.sleep(0.5)  # ADC takes up to 400 ms
        return int(self.query("ADC?").split()[-1])

    def read_resistance(self) -> float:
        """Return resistance in Ohms from the last :meth:`trigger_adc` call.

        Accounts for the current range and magnifier setting automatically.
        Uses serial polling to wait for the result.

        Returns
        -------
        float
            Resistance in Ω; :data:`RES_OVERLOAD` (2.0001e6) on overload.
        """
        return float(self.query("RES?").split()[-1])

    @property
    def overload(self) -> bool:
        """True if the last A/D conversion resulted in overload."""
        return bool(int(self.query("OVL?").split()[-1]))

    def measure(self) -> float:
        """Trigger a conversion and return resistance in Ohms.

        Convenience wrapper around :meth:`trigger_adc` + :meth:`read_resistance`.
        Raises :class:`RuntimeError` on overload.
        """
        self.trigger_adc()
        resistance = self.read_resistance()
        if abs(resistance) >= RES_OVERLOAD:
            raise RuntimeError(
                f"{self.name}: overload on range {self.range} "
                f"(channel {self.channel})."
            )
        return resistance

    def average(self, n: int) -> dict:
        """Take n averaged A/D conversions and return statistics.

        Parameters
        ----------
        n:
            Number of samples (1–1000).  Each takes ≈ 400 ms.

        Returns
        -------
        dict with keys ``"mean"``, ``"min"``, ``"max"``, ``"std"`` in Ohms,
        and ``"overload"`` (bool).

        Notes
        -----
        The AVS47-IB output queue holds **only one response message at a
        time**.  Each query must therefore be sent as its own program message
        and read back before the next one is issued.  Because all commands are
        strictly sequential, ``AVE?`` sent after ``AVE n`` will block until
        averaging is complete before returning a response — no extra polling
        is needed.
        """
        n = self.validate_range(n, 1, 1000)

        # Each sample takes up to 0.4 s; wait for the full acquisition plus
        # a small margin before querying results.
        wait = n * 0.4 + 1.0
        old_timeout = self._inst.timeout
        self._inst.timeout = int(wait * 1000 + 5_000)
        try:
            self.write(f"AVE {n}", sleep=False)
            time.sleep(wait)
            mean = float(self.query("AVE?").split()[-1])
            minimum = float(self.query("MIN?").split()[-1])
            maximum = float(self.query("MAX?").split()[-1])
            std = float(self.query("STD?").split()[-1])
            ovl = bool(int(self.query("OVL?").split()[-1]))
        finally:
            self._inst.timeout = old_timeout

        return {
            "mean": mean,
            "min": minimum,
            "max": maximum,
            "std": std,
            "overload": ovl,
        }

    def read_temperature(self) -> float:
        """Measure resistance and convert to temperature in Kelvin.

        Requires a :class:`~qtics.calibration.ruox.RuOx` thermometer to have
        been passed at construction time.

        Returns
        -------
        float
            Temperature in Kelvin.

        Raises
        ------
        RuntimeError
            If no thermometer was provided.
        ValueError
            If the measured resistance is outside the calibration range.
        """
        if self.thermometer is None:
            raise RuntimeError(
                f"{self.name}: no thermometer provided. "
                "Pass a RuOx instance at construction time."
            )
        resistance = self.measure()
        return self.thermometer.resistance_to_temperature(resistance)

    def set_temperature(self, temperature: float):
        """Set the TS-530A target temperature.

        Converts *temperature* to the expected resistance via the calibration
        file, then measures the actual ADC count at that resistance on the
        current bridge range and uses it directly as the SPT value.

        This is the correct approach because SPT maps 1:1 to ADC counts
        when the TS-530A is relatively calibrated against the AVS-47B
        (set point 10000 = 1.0000 V = bridge midscale on the current range).

        Parameters
        ----------
        temperature:
            Target temperature in Kelvin.

        Raises
        ------
        RuntimeError
            If no thermometer was provided at construction time, or if the
            bridge is not in remote mode.
        ValueError
            If *temperature* is outside the calibrated range.
        """
        if self.thermometer is None:
            raise RuntimeError(
                f"{self.name}: no thermometer provided. "
                "Pass a RuOx instance at construction time."
            )
        self._ts530_check_remote()

        # T → R via calibration file
        target_r = self.thermometer.temperature_to_resistance(temperature)
        log.info(
            f"{self.name}: set_temperature {temperature:.4f} K "
            f"→ target resistance {target_r:.2f} Ω"
        )

        # Measure the ADC count the bridge would produce at that resistance.
        # We use the current range — the caller is responsible for ensuring
        # the right range is selected for the target temperature.
        self.trigger_adc()
        time.sleep(0.5)
        adc_now = self.read_adc()

        # The ADC result is proportional to resistance on the current range.
        # Scale target_r to ADC counts using the full-scale resistance.
        range_idx = self.range
        fullscale_r = RANGES.get(range_idx)
        if fullscale_r is None:
            raise RuntimeError(
                f"{self.name}: range {range_idx} has no full-scale resistance "
                "(range 0 = no range connected). Select a valid range first."
            )
        # ADC full scale (19999) corresponds to the full-scale resistance.
        spt = round(target_r / fullscale_r * 19999)
        spt = max(1, min(spt, 42000))

        log.info(
            f"{self.name}: range {range_idx} ({fullscale_r} Ω full-scale) "
            f"→ SPT = {spt} ({spt * 100e-6:.4f} V)"
        )
        self.set_point = spt

    # ------------------------------------------------------------------
    # Safe channel-change helper
    # ------------------------------------------------------------------

    def set_channel(
        self,
        channel: int,
        range_idx: int | None = None,
        excitation_idx: int | None = None,
        settle: float = 2.0,
    ):
        """Switch multiplexer channel safely (grounds input during transition).

        Following the manual's recommended practice:

        1. Ground the input (``INP 0``).
        2. Set new MUX channel, range, and excitation.
        3. Wait *settle* seconds.
        4. Re-enable the input (``INP 1``).

        Parameters
        ----------
        channel:
            Target MUX channel (0–7).
        range_idx:
            Range index to apply after switching (unchanged if None).
        excitation_idx:
            Excitation index to apply after switching (unchanged if None).
        settle:
            Seconds to wait after switching before re-enabling input.
        """
        self.input = INP_ZERO
        self.channel = channel
        if range_idx is not None:
            self.range = range_idx
        if excitation_idx is not None:
            self.excitation = excitation_idx
        time.sleep(settle)
        self.input = INP_MEASURE
        log.info(
            f"{self.name}: channel set to {channel} "
            f"(range={self.range}, exc={self.excitation})."
        )

    # ------------------------------------------------------------------
    # TS-530A temperature controller
    # ------------------------------------------------------------------

    def _ts530_check_remote(self):
        """Raise if the bridge is not in remote mode.

        The TS-530A has no independent remote mode — it is controlled
        exclusively through the AVS-47B when REM 1 is active.  Any TS-530A
        command sent while the bridge is in local mode is silently ignored.
        """
        if not self.remote:
            raise RuntimeError(
                f"{self.name}: AVS-47B must be in remote mode (REM 1) "
                "before sending TS-530A commands."
            )

    def configure_controller(
        self,
        set_point: int,
        proportional_gain: int = 5,
        integrator_tc: int = 0,
        derivator_tc: int = 0,
        power_bias: int = 0,
        heater_range: int = 1,
    ):
        """Send all TS-530A parameters in one call.

        The manual states: *"If you want to control any one aspect of the
        TS-530A remotely, you must control them all."*  This method is
        therefore the required entry point for remote temperature control —
        never send individual TS-530A commands without having called this
        first (or at least having sent all parameters yourself).

        Also ensures the bridge is in remote mode before sending, since the
        TS-530A only accepts commands when ``REM 1`` is active.

        Parameters
        ----------
        set_point:
            Target set point in units of 100 µV (1–42000).
        proportional_gain:
            PRO index 0–11 (default 5 = 30 dB).
        integrator_tc:
            ITC index 0–11 (default 0 = reset / disabled).
        derivator_tc:
            DTC index 0–7 (default 0 = off).
        power_bias:
            BIA index 0–5 (default 0 = no bias).
        heater_range:
            POW index 0–7 (default 1).
        """
        if not self.remote:
            self.remote = True

        self.write(f"SPT {self.validate_range(set_point, 1, 42000)}")
        self.write(f"PRO {self.validate_range(proportional_gain, 0, 11)}")
        self.write(f"ITC {self.validate_range(integrator_tc, 0, 11)}")
        self.write(f"DTC {self.validate_range(derivator_tc, 0, 7)}")
        self.write(f"BIA {self.validate_range(power_bias, 0, 5)}")
        self.write(f"POW {self.validate_range(heater_range, 0, 7)}")
        log.info(
            f"{self.name}: TS-530A configured — "
            f"SPT={set_point}, PRO={proportional_gain}, ITC={integrator_tc}, "
            f"DTC={derivator_tc}, BIA={power_bias}, POW={heater_range}."
        )

    @property
    def set_point(self) -> int:
        """TS-530A set point in units of 100 µV (1–42000)."""
        return int(self.query("SPT?").split()[-1])

    @set_point.setter
    def set_point(self, value: int):
        self._ts530_check_remote()
        value = self.validate_range(value, 1, 42000)
        self.write(f"SPT {value}")

    @property
    def proportional_gain(self) -> int:
        """TS-530A proportional gain index (0–11; 15 = error forced to zero)."""
        return int(self.query("PRO?").split()[-1])

    @proportional_gain.setter
    def proportional_gain(self, value: int):
        self._ts530_check_remote()
        self.validate_opt(value, tuple(range(12)) + (15,))
        self.write(f"PRO {value}")

    def force_error_zero(self):
        """Force the TS-530A error signal to zero (``PRO 15``)."""
        self.write("PRO 15")

    @property
    def integrator_tc(self) -> int:
        """TS-530A integrator time constant index (0–11)."""
        return int(self.query("ITC?").split()[-1])

    @integrator_tc.setter
    def integrator_tc(self, value: int):
        self._ts530_check_remote()
        value = self.validate_range(value, 0, 11)
        self.write(f"ITC {value}")

    @property
    def derivator_tc(self) -> int:
        """TS-530A derivator time constant index (0–7)."""
        return int(self.query("DTC?").split()[-1])

    @derivator_tc.setter
    def derivator_tc(self, value: int):
        self._ts530_check_remote()
        value = self.validate_range(value, 0, 7)
        self.write(f"DTC {value}")

    @property
    def power_bias(self) -> int:
        """TS-530A power bias index (0–5; each step = 20% of full range)."""
        return int(self.query("BIA?").split()[-1])

    @power_bias.setter
    def power_bias(self, value: int):
        self._ts530_check_remote()
        value = self.validate_range(value, 0, 5)
        self.write(f"BIA {value}")

    @property
    def heater_range(self) -> int:
        """TS-530A heater output power range index (0–7)."""
        return int(self.query("POW?").split()[-1])

    @heater_range.setter
    def heater_range(self, value: int):
        self._ts530_check_remote()
        value = self.validate_range(value, 0, 7)
        self.write(f"POW {value}")

    # Delay after issuing a macro command before querying the result.
    # SPV / HTV / HTI each take one ADC conversion plus display settling.
    # HTP combines HTV + HTI so takes twice as long.
    _MACRO_DELAY = 3.0  # seconds — SPV, HTV, HTI
    _MACRO_DELAY_HTP = 6.0  # seconds — HTP (two conversions)

    def read_set_point_voltage(self) -> float:
        """Measure and return the TS-530A set point voltage in Volts.

        ``SPV`` is a macro: it sets the display, waits internally, and stores
        the result.  ``SPV?`` retrieves it.  The sleep must cover the full
        internal macro execution (~one ADC conversion + display settling).
        """
        self.write("SPV")
        time.sleep(self._MACRO_DELAY)
        return float(self.query("SPV?").split()[-1])

    def read_heater_voltage(self) -> float:
        """Measure and return the TS-530A heater output voltage in Volts."""
        self.write("HTV")
        time.sleep(self._MACRO_DELAY)
        return float(self.query("HTV?").split()[-1])

    def read_heater_current(self) -> float:
        """Measure and return the TS-530A heater output current in Amps."""
        self.write("HTI")
        time.sleep(self._MACRO_DELAY)
        return float(self.query("HTI?").split()[-1])

    def read_heater_power(self) -> float:
        """Measure and return the TS-530A heater output power in Watts.

        ``HTP`` combines ``HTV`` and ``HTI`` internally, so it takes
        approximately twice as long as the other macros.
        """
        self.write("HTP")
        time.sleep(self._MACRO_DELAY_HTP)
        return float(self.query("HTP?").split()[-1])
