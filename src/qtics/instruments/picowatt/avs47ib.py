"""
Driver for the Picowatt AVS-47B resistance bridge with AVS47-IB GPIB interface.

Hardware:  AVS-47B AC resistance bridge (Picowatt)
Interface: AVS47-IB two-stage GPIB computer interface (firmware >= 3R4)
Bus:       IEEE-488 (GPIB), factory default device address 20

The AVS47-IB follows IEEE-488.2 with minor deviations. All commands are
case-insensitive and strictly sequential: the previous operation is always
fully completed before the next command is processed.

References
----------
* AVS47-IB Instruction Manual, Picowatt, rev. 2015-02-17 (firmware 3R4)
* TS-530A Temperature Controller Instruction Manual, Picowatt, rev. 1999-07-28
"""

import time
from typing import Optional, Protocol, Union

from qtics import log
from qtics.instruments.base import SCPIInstrument
from qtics.transport import GPIBTransport, Transport

# RAN [0..7]: range index -> full-scale resistance in Ohm
RANGES = {
    0: None,  # no range connected (power-on default; do not use)
    1: 2,
    2: 20,
    3: 200,
    4: 2_000,
    5: 20_000,
    6: 200_000,
    7: 2_000_000,
}

# EXC [0..7]: excitation index -> nominal excitation voltage in V
EXCITATIONS = {
    0: 0,  # no excitation
    1: 3e-6,
    2: 10e-6,
    3: 30e-6,
    4: 100e-6,
    5: 300e-6,
    6: 1e-3,
    7: 3e-3,
}

# INP [0..2]: input source
INP_ZERO = 0  # bridge input grounded (offset measurement)
INP_MEASURE = 1  # measurement (sensor selected by MUX)
INP_CAL = 2  # internal 100 Ohm calibration reference

# ADC overload sentinel value (raw integer)
ADC_OVERLOAD = 20001
# RES overload sentinel value (Ohm)
RES_OVERLOAD = 2.0001e6


class Thermometer(Protocol):
    """Calibration of a resistance thermometer."""

    def resistance_to_temperature(self, resistance: float) -> float:
        """Temperature in K at ``resistance`` in Ohm."""

    def temperature_to_resistance(self, temperature: float) -> float:
        """Resistance in Ohm at ``temperature`` in K."""


class AVS47IB(SCPIInstrument):
    """Picowatt AVS-47B resistance bridge via AVS47-IB GPIB interface.

    The AVS47-IB wraps the analogue AVS-47B into a fully computer-controlled
    instrument. It also forwards commands to the optional TS-530A temperature
    controller when the two units are connected with the 37-way ribbon cable.

    The transport is a :class:`~qtics.transport.gpib.GPIBTransport`: pass the GPIB
    primary address (factory default 20) or a ready transport. ``thermometer``
    converts resistance and temperature, it is needed only by
    :meth:`read_temperature` and :meth:`set_temperature`.

    ``*IDN?`` answers ``*IDN PICOWATT,AVS47-IB,0,<firmware_version>``. It is the
    only query returning a string; all others are numeric.

    **Safe channel-change sequence** (manual recommendation)::

        bridge.input = INP_ZERO          # disconnect input
        bridge.channel = n               # select new MUX channel
        bridge.range = r                 # set range
        bridge.excitation = e            # set excitation
        time.sleep(2)
        bridge.input = INP_MEASURE       # re-enable input

    The :meth:`set_channel` helper performs this sequence automatically.
    """

    default_transport = GPIBTransport
    transport_defaults = {"delay": 0.1}

    #: Factory-default GPIB address (stored in EEPROM, writable via IBA).
    DEFAULT_ADDRESS: int = 20

    # Delay after issuing a macro command before querying the result.
    # SPV / HTV / HTI each take one ADC conversion plus display settling.
    # HTP combines HTV + HTI so takes twice as long.
    _MACRO_DELAY = 3.0
    _MACRO_DELAY_HTP = 6.0

    def __init__(
        self,
        transport: Union[Transport, str, int] = DEFAULT_ADDRESS,
        name: str = "AVS47IB",
        thermometer: Optional[Thermometer] = None,
        **transport_kwargs,
    ):
        """Initialize."""
        if isinstance(transport, int):
            transport = str(transport)
        super().__init__(transport, name, **transport_kwargs)
        self.thermometer = thermometer

    def _value(self, cmd: str) -> str:
        """Query and return the last field of the answer (e.g. "INP 1" -> "1")."""
        return self.query(cmd).split()[-1]

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _after_connect(self):
        """Clear the status registers and take remote control."""
        self.clear()
        self.remote = True

    def _before_disconnect(self):
        """Release the front-panel controls to local mode."""
        self.remote = False

    # ------------------------------------------------------------------
    # Identification / status
    # ------------------------------------------------------------------

    def self_test(self) -> int:
        """Run the built-in self-test and return the error byte.

        A return value of 0 means all checks passed. 96 (bits 5+6) is the
        minimum expected value when no TS-530A is connected.

        .. warning::
            Do not run during an experiment. Resets both AVS-47B and TS-530A.
        """
        return int(self._value("*TST?"))

    # ------------------------------------------------------------------
    # Remote / local mode
    # ------------------------------------------------------------------

    @property
    def remote(self) -> bool:
        """True when the bridge is computer-controlled (remote mode)."""
        return bool(int(self._value("REM?")))

    @remote.setter
    def remote(self, state: bool):
        self.write(f"REM {int(state)}")

    # ------------------------------------------------------------------
    # AVS-47B bridge settings
    # ------------------------------------------------------------------

    @property
    def input(self) -> int:
        """Input source: 0 = zero (gnd), 1 = measure, 2 = calibrate."""
        return int(self._value("INP?"))

    @input.setter
    def input(self, value: int):
        self.write(f"INP {self.validate_range(value, 0, 2)}")

    @property
    def channel(self) -> int:
        """Multiplexer channel, 0-7."""
        return int(self._value("MUX?"))

    @channel.setter
    def channel(self, value: int):
        self.write(f"MUX {self.validate_range(value, 0, 7)}")

    @property
    def range(self) -> int:
        """Resistance range index (0-7). See :data:`RANGES` for mapping."""
        return int(self._value("RAN?"))

    @range.setter
    def range(self, value: int):
        self.write(f"RAN {self.validate_range(value, 0, 7)}")

    @property
    def excitation(self) -> int:
        """Excitation index (0-7). See :data:`EXCITATIONS` for mapping."""
        return int(self._value("EXC?"))

    @excitation.setter
    def excitation(self, value: int):
        self.write(f"EXC {self.validate_range(value, 0, 7)}")

    @property
    def display(self) -> int:
        """Display selector (0-7; 0 = R, 7 = TS-530 set point)."""
        return int(self._value("DIS?"))

    @display.setter
    def display(self, value: int):
        self.write(f"DIS {self.validate_range(value, 0, 7)}")

    @property
    def autorange(self) -> bool:
        """True when software autoranging is enabled."""
        return bool(int(self._value("ARN?")))

    @autorange.setter
    def autorange(self, state: bool):
        self.write(f"ARN {int(state)}")

    @property
    def stabilization_delay(self) -> int:
        """Autoranging stabilization delay in seconds (1-100)."""
        return int(self._value("SDY?"))

    @stabilization_delay.setter
    def stabilization_delay(self, seconds: int):
        self.write(f"SDY {self.validate_range(seconds, 1, 100)}")

    @property
    def reference_source(self) -> int:
        """Reference source: 0 = memory DAC, 1 = direct potentiometer."""
        return int(self._value("RFS?"))

    @property
    def magnifier(self) -> int:
        """Difference magnifier: 0 = dR x1, 1 = dR x10."""
        return int(self._value("MAG?"))

    def set_reference(self, value: int):
        """Set the difference reference DAC value (0-20000, 19999 is about 2.0 V).

        The value is internally rounded to the nearest multiple of 5. There is
        no corresponding query; use ``DIS 3; DLY 1; ADC; ADC?`` to read back the
        actual reference voltage.
        """
        self.write(f"REF {self.validate_range(value, 0, 20000)}")

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
        """Return the raw A/D result of the last :meth:`trigger_adc` call.

        Waits 0.5 s first, as the conversion takes up to 400 ms. Returns -19999
        to 19999, :data:`ADC_OVERLOAD` (20001) on overload.
        """
        time.sleep(0.5)
        return int(self._value("ADC?"))

    def read_resistance(self) -> float:
        """Return the resistance in Ohm of the last :meth:`trigger_adc` call.

        Accounts for the current range and magnifier setting. Returns
        :data:`RES_OVERLOAD` (2.0001e6) on overload.
        """
        return float(self._value("RES?"))

    @property
    def overload(self) -> bool:
        """True if the last A/D conversion resulted in overload."""
        return bool(int(self._value("OVL?")))

    def measure(self) -> float:
        """Trigger a conversion and return the resistance in Ohm.

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
        """Take ``n`` (1-1000) averaged A/D conversions and return statistics.

        Each sample takes about 400 ms. Returns a dict with keys ``"mean"``,
        ``"min"``, ``"max"``, ``"std"`` in Ohm, and ``"overload"`` (bool).

        The AVS47-IB output queue holds only one response message at a time, so
        each query is sent and read back before the next one.
        """
        n = self.validate_range(n, 1, 1000)
        wait = n * 0.4 + 1.0
        old_timeout = self.transport.timeout
        self.transport.timeout = wait + 5
        try:
            self.write(f"AVE {n}")
            time.sleep(wait)
            result = {
                "mean": float(self._value("AVE?")),
                "min": float(self._value("MIN?")),
                "max": float(self._value("MAX?")),
                "std": float(self._value("STD?")),
                "overload": bool(int(self._value("OVL?"))),
            }
        finally:
            self.transport.timeout = old_timeout
        return result

    def _require_thermometer(self) -> Thermometer:
        if self.thermometer is None:
            raise RuntimeError(
                f"{self.name}: no thermometer provided, pass one at construction."
            )
        return self.thermometer

    def read_temperature(self) -> float:
        """Measure the resistance and convert it to temperature in K."""
        return self._require_thermometer().resistance_to_temperature(self.measure())

    def set_temperature(self, temperature: float):
        """Set the TS-530A target temperature in K.

        The temperature is converted to resistance by the thermometer, then to a
        set point by scaling it to the full-scale resistance of the current range
        (set point 19999 = full scale). The caller selects a range suitable for
        the target temperature.
        """
        thermometer = self._require_thermometer()
        self._ts530_check_remote()

        target_r = thermometer.temperature_to_resistance(temperature)
        log.info(
            f"{self.name}: set_temperature {temperature:.4f} K "
            f"-> target resistance {target_r:.2f} Ohm"
        )
        range_idx = self.range
        fullscale_r = RANGES.get(range_idx)
        if fullscale_r is None:
            raise RuntimeError(
                f"{self.name}: range {range_idx} has no full-scale resistance "
                "(range 0 = no range connected). Select a valid range first."
            )
        spt = max(1, min(round(target_r / fullscale_r * 19999), 42000))
        log.info(
            f"{self.name}: range {range_idx} ({fullscale_r} Ohm full-scale) "
            f"-> SPT = {spt} ({spt * 100e-6:.4f} V)"
        )
        self.set_point = spt

    def set_channel(
        self,
        channel: int,
        range_idx: Optional[int] = None,
        excitation_idx: Optional[int] = None,
        settle: float = 2.0,
    ):
        """Switch multiplexer channel safely, grounding the input meanwhile.

        Grounds the input, sets channel, range and excitation (unchanged if
        None), waits ``settle`` seconds and re-enables the input.
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

        The TS-530A is controlled only through the AVS-47B when ``REM 1`` is
        active: commands sent in local mode are silently ignored.
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
        """Send all TS-530A parameters in one call, switching to remote mode.

        The manual states: *"If you want to control any one aspect of the
        TS-530A remotely, you must control them all."* Call this before any
        individual TS-530A command.

        Args:
            set_point: set point in units of 100 uV (1-42000).
            proportional_gain: PRO index 0-11 (5 = 30 dB).
            integrator_tc: ITC index 0-11 (0 = reset / disabled).
            derivator_tc: DTC index 0-7 (0 = off).
            power_bias: BIA index 0-5 (0 = no bias).
            heater_range: POW index 0-7.
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
            f"{self.name}: TS-530A configured: "
            f"SPT={set_point}, PRO={proportional_gain}, ITC={integrator_tc}, "
            f"DTC={derivator_tc}, BIA={power_bias}, POW={heater_range}."
        )

    @property
    def set_point(self) -> int:
        """TS-530A set point in units of 100 uV (1-42000)."""
        return int(self._value("SPT?"))

    @set_point.setter
    def set_point(self, value: int):
        self._ts530_check_remote()
        self.write(f"SPT {self.validate_range(value, 1, 42000)}")

    @property
    def proportional_gain(self) -> int:
        """TS-530A proportional gain index (0-11; 15 = error forced to zero)."""
        return int(self._value("PRO?"))

    @proportional_gain.setter
    def proportional_gain(self, value: int):
        self._ts530_check_remote()
        self.write(f"PRO {self.validate_opt(value, tuple(range(12)) + (15,))}")

    def force_error_zero(self):
        """Force the TS-530A error signal to zero (``PRO 15``)."""
        self.write("PRO 15")

    @property
    def integrator_tc(self) -> int:
        """TS-530A integrator time constant index (0-11)."""
        return int(self._value("ITC?"))

    @integrator_tc.setter
    def integrator_tc(self, value: int):
        self._ts530_check_remote()
        self.write(f"ITC {self.validate_range(value, 0, 11)}")

    @property
    def derivator_tc(self) -> int:
        """TS-530A derivator time constant index (0-7)."""
        return int(self._value("DTC?"))

    @derivator_tc.setter
    def derivator_tc(self, value: int):
        self._ts530_check_remote()
        self.write(f"DTC {self.validate_range(value, 0, 7)}")

    @property
    def power_bias(self) -> int:
        """TS-530A power bias index (0-5; each step = 20% of full range)."""
        return int(self._value("BIA?"))

    @power_bias.setter
    def power_bias(self, value: int):
        self._ts530_check_remote()
        self.write(f"BIA {self.validate_range(value, 0, 5)}")

    @property
    def heater_range(self) -> int:
        """TS-530A heater output power range index (0-7)."""
        return int(self._value("POW?"))

    @heater_range.setter
    def heater_range(self, value: int):
        self._ts530_check_remote()
        self.write(f"POW {self.validate_range(value, 0, 7)}")

    def _macro(self, cmd: str, delay: float) -> float:
        """Run a measurement macro, wait for it and read its result."""
        self.write(cmd)
        time.sleep(delay)
        return float(self._value(f"{cmd}?"))

    def read_set_point_voltage(self) -> float:
        """Measure and return the TS-530A set point voltage in V."""
        return self._macro("SPV", self._MACRO_DELAY)

    def read_heater_voltage(self) -> float:
        """Measure and return the TS-530A heater output voltage in V."""
        return self._macro("HTV", self._MACRO_DELAY)

    def read_heater_current(self) -> float:
        """Measure and return the TS-530A heater output current in A."""
        return self._macro("HTI", self._MACRO_DELAY)

    def read_heater_power(self) -> float:
        """Measure and return the TS-530A heater output power in W.

        ``HTP`` combines ``HTV`` and ``HTI`` internally, so it takes about twice
        as long as the other macros.
        """
        return self._macro("HTP", self._MACRO_DELAY_HTP)
