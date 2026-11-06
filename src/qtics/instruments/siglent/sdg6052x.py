"""Controller of the Siglent SDG6052X arbitrary waveform generator."""

import re
from typing import Any, Dict, List, Union

import numpy as np

from qtics import log
from qtics.instruments.base import SCPIInstrument
from qtics.instruments.utils import to_bool
from qtics.transport import SocketTransport, Transport

_NUMBER = re.compile(r"^([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*([A-Za-z%]*)$")
_MODULATIONS = ("AM", "DSBAM", "FM", "PM", "FSK", "ASK", "PSK", "PWM")
_WAVE_NAME = re.compile(r"^[A-Za-z0-9_]{1,32}$")


def _convert(token: str) -> Union[float, str]:
    """Convert an answer token, stripping its unit (HZ, V, S, %, ...)."""
    match = _NUMBER.match(token.strip())
    return float(match.group(1)) if match else token.strip()


def parse_params(answer: str) -> Dict[str, Any]:
    """Parse the answer of a ``BSWV?``-like query into a dictionary.

    ``"C1:BSWV WVTP,SINE,FRQ,1000HZ,AMP,2V"`` gives
    ``{"WVTP": "SINE", "FRQ": 1000.0, "AMP": 2.0}``: numbers are converted to float
    without unit, other values stay strings. The carrier parameters following
    ``CARR`` go in a nested dictionary, a modulation type given without value
    (``AM``, ``FM``, ...) is stored as ``"TYPE"``.
    """
    body = answer.split(" ", 1)[1] if " " in answer else answer
    tokens = [token.strip() for token in body.split(",")]
    return _parse_tokens(tokens)


def _parse_tokens(tokens: List[str]) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    i = 0
    while i < len(tokens):
        key = tokens[i]
        if key == "CARR":
            params["CARR"] = _parse_tokens(tokens[i + 1 :])
            break
        if key in _MODULATIONS:
            params["TYPE"] = key
            i += 1
        elif i + 1 < len(tokens):
            params[key] = _convert(tokens[i + 1])
            i += 2
        else:
            break
    return params


class SDGChannel:
    """One output channel of the SDG6052X, see :meth:`SDG6052X.channel`.

    The burst, sweep and modulation parameters can only be read (and mostly
    written) while the respective mode is enabled, as stated by the instrument.
    """

    def __init__(self, awg: "SDG6052X", number: int):
        """Initialize, ``number`` is 1 or 2."""
        self.awg = awg
        self.number = awg.validate_opt(number, (1, 2))

    def _write(self, cmd: str):
        self.awg.write(f"C{self.number}:{cmd}")

    def _params(self, cmd: str) -> Dict[str, Any]:
        return parse_params(self.awg.query(f"C{self.number}:{cmd}?"))

    def _param(self, cmd: str, key: str) -> Any:
        params = self._params(cmd)
        if key not in params:
            raise RuntimeError(
                f"C{self.number}:{cmd} has no {key} parameter (is the mode enabled?)"
            )
        return params[key]

    def _outp(self) -> Dict[str, Any]:
        """Answer of ``OUTP?``: the state, then LOAD and PLRT pairs."""
        answer = self.awg.query(f"C{self.number}:OUTP?")
        state, _, rest = answer.split(" ", 1)[1].partition(",")
        return {"STATE": state.strip(), **_parse_tokens(rest.split(","))}

    @property
    def output(self) -> bool:
        """Whether the output is on."""
        return to_bool(self._outp()["STATE"])

    @output.setter
    def output(self, state: bool):
        self._write(f"OUTP {'ON' if state else 'OFF'}")

    @property
    def load(self) -> Union[float, str]:
        """Output load: "HZ" (high impedance) or a value in ohm (50 to 100000)."""
        return self._outp()["LOAD"]

    @load.setter
    def load(self, load: Union[float, str]):
        if isinstance(load, str):
            self.awg.validate_opt(load.upper(), ("HZ",))
            load = load.upper()
        else:
            load = self.awg.validate_range(load, 50, 100000)
        self._write(f"OUTP LOAD,{load}")

    @property
    def polarity(self) -> str:
        """Output polarity: "NOR" (normal) or "INVT" (inverted)."""
        return self._outp()["PLRT"]

    @polarity.setter
    def polarity(self, polarity: str):
        self.awg.validate_opt(polarity, ("NOR", "INVT"))
        self._write(f"OUTP PLRT,{polarity}")

    def basic_wave(self) -> Dict[str, Any]:
        """All the basic wave parameters (``BSWV?``) as a dictionary."""
        return self._params("BSWV")

    @property
    def waveform(self) -> str:
        """Basic wave type: SINE, SQUARE, RAMP, PULSE, NOISE, DC or ARB."""
        return self._param("BSWV", "WVTP")

    @waveform.setter
    def waveform(self, wave: str):
        self.awg.validate_opt(
            wave, ("SINE", "SQUARE", "RAMP", "PULSE", "NOISE", "DC", "ARB")
        )
        self._write(f"BSWV WVTP,{wave}")

    @property
    def frequency(self) -> float:
        """Frequency [Hz], not available for NOISE and DC."""
        return self._param("BSWV", "FRQ")

    @frequency.setter
    def frequency(self, frequency: float):
        frequency = self.awg.validate_range(frequency, 1e-6, self.awg.f_max)
        self._write(f"BSWV FRQ,{frequency}")

    @property
    def amplitude(self) -> float:
        """Peak to peak amplitude [V], not available for NOISE and DC."""
        return self._param("BSWV", "AMP")

    @amplitude.setter
    def amplitude(self, amplitude: float):
        amplitude = self.awg.validate_range(amplitude, 0.002, 20)
        self._write(f"BSWV AMP,{amplitude}")

    @property
    def offset(self) -> float:
        """DC offset [V], not available for NOISE and DC."""
        return self._param("BSWV", "OFST")

    @offset.setter
    def offset(self, offset: float):
        self._write(f"BSWV OFST,{offset}")

    @property
    def phase(self) -> float:
        """Phase [deg], not available for NOISE, PULSE and DC."""
        return self._param("BSWV", "PHSE")

    @phase.setter
    def phase(self, phase: float):
        phase = self.awg.validate_range(phase, 0, 360)
        self._write(f"BSWV PHSE,{phase}")

    @property
    def duty(self) -> float:
        """Duty cycle [%] of SQUARE and PULSE waves."""
        return self._param("BSWV", "DUTY")

    @duty.setter
    def duty(self, duty: float):
        duty = self.awg.validate_range(duty, 0, 100)
        self._write(f"BSWV DUTY,{duty}")

    @property
    def symmetry(self) -> float:
        """Symmetry [%] of RAMP waves."""
        return self._param("BSWV", "SYM")

    @symmetry.setter
    def symmetry(self, symmetry: float):
        symmetry = self.awg.validate_range(symmetry, 0, 100)
        self._write(f"BSWV SYM,{symmetry}")

    @property
    def high_level(self) -> float:
        """High level [V]."""
        return self._param("BSWV", "HLEV")

    @high_level.setter
    def high_level(self, level: float):
        self._write(f"BSWV HLEV,{level}")

    @property
    def low_level(self) -> float:
        """Low level [V]."""
        return self._param("BSWV", "LLEV")

    @low_level.setter
    def low_level(self, level: float):
        self._write(f"BSWV LLEV,{level}")

    @property
    def burst_enable(self) -> bool:
        """Whether the burst mode is on."""
        return to_bool(self._param("BTWV", "STATE"))

    @burst_enable.setter
    def burst_enable(self, state: bool):
        self._write(f"BTWV STATE,{'ON' if state else 'OFF'}")

    @property
    def burst_mode(self) -> str:
        """Burst mode: "NCYC" (N cycles) or "GATE"."""
        return self._param("BTWV", "GATE_NCYC")

    @burst_mode.setter
    def burst_mode(self, mode: str):
        self.awg.validate_opt(mode, ("NCYC", "GATE"))
        self._write(f"BTWV GATE_NCYC,{mode}")

    @property
    def burst_cycles(self) -> Union[int, str]:
        """Number of cycles of each burst, or "INF"."""
        cycles = self._param("BTWV", "TIME")
        return cycles if isinstance(cycles, str) else int(cycles)

    @burst_cycles.setter
    def burst_cycles(self, cycles: Union[int, str]):
        if isinstance(cycles, str):
            self.awg.validate_opt(cycles.upper(), ("INF",))
            cycles = cycles.upper()
        else:
            cycles = int(self.awg.validate_range(cycles, 1, 1e6))
        self._write(f"BTWV TIME,{cycles}")

    @property
    def burst_period(self) -> float:
        """Burst period [s] (internal trigger)."""
        return self._param("BTWV", "PRD")

    @burst_period.setter
    def burst_period(self, period: float):
        self._write(f"BTWV PRD,{period}")

    @property
    def burst_delay(self) -> float:
        """Burst delay [s]."""
        return self._param("BTWV", "DLAY")

    @burst_delay.setter
    def burst_delay(self, delay: float):
        self._write(f"BTWV DLAY,{delay}")

    @property
    def burst_trigger_source(self) -> str:
        """Burst trigger source: INT, EXT or MAN."""
        return self._param("BTWV", "TRSR")

    @burst_trigger_source.setter
    def burst_trigger_source(self, source: str):
        self.awg.validate_opt(source, ("INT", "EXT", "MAN"))
        self._write(f"BTWV TRSR,{source}")

    def trigger_burst(self):
        """Send a manual trigger (burst trigger source MAN)."""
        self._write("BTWV MTRIG")

    @property
    def sweep_enable(self) -> bool:
        """Whether the frequency sweep is on."""
        return to_bool(self._param("SWWV", "STATE"))

    @sweep_enable.setter
    def sweep_enable(self, state: bool):
        self._write(f"SWWV STATE,{'ON' if state else 'OFF'}")

    @property
    def sweep_start(self) -> float:
        """Sweep start frequency [Hz]."""
        return self._param("SWWV", "START")

    @sweep_start.setter
    def sweep_start(self, frequency: float):
        self._write(f"SWWV START,{frequency}")

    @property
    def sweep_stop(self) -> float:
        """Sweep stop frequency [Hz]."""
        return self._param("SWWV", "STOP")

    @sweep_stop.setter
    def sweep_stop(self, frequency: float):
        self._write(f"SWWV STOP,{frequency}")

    @property
    def sweep_time(self) -> float:
        """Sweep time [s]."""
        return self._param("SWWV", "TIME")

    @sweep_time.setter
    def sweep_time(self, time: float):
        self._write(f"SWWV TIME,{time}")

    @property
    def sweep_mode(self) -> str:
        """Sweep style: "LINE" or "LOG"."""
        return self._param("SWWV", "SWMD")

    @sweep_mode.setter
    def sweep_mode(self, mode: str):
        self.awg.validate_opt(mode, ("LINE", "LOG"))
        self._write(f"SWWV SWMD,{mode}")

    @property
    def sweep_direction(self) -> str:
        """Sweep direction: "UP" or "DOWN"."""
        return self._param("SWWV", "DIR")

    @sweep_direction.setter
    def sweep_direction(self, direction: str):
        self.awg.validate_opt(direction, ("UP", "DOWN"))
        self._write(f"SWWV DIR,{direction}")

    @property
    def sweep_trigger_source(self) -> str:
        """Sweep trigger source: INT, EXT or MAN."""
        return self._param("SWWV", "TRSR")

    @sweep_trigger_source.setter
    def sweep_trigger_source(self, source: str):
        self.awg.validate_opt(source, ("INT", "EXT", "MAN"))
        self._write(f"SWWV TRSR,{source}")

    def trigger_sweep(self):
        """Send a manual trigger (sweep trigger source MAN)."""
        self._write("SWWV MTRIG")

    @property
    def mod_enable(self) -> bool:
        """Whether the modulation is on."""
        return to_bool(self._param("MDWV", "STATE"))

    @mod_enable.setter
    def mod_enable(self, state: bool):
        self._write(f"MDWV STATE,{'ON' if state else 'OFF'}")

    @property
    def mod_type(self) -> str:
        """Modulation type: AM, DSBAM, FM, PM, FSK, ASK, PSK or PWM."""
        return self._param("MDWV", "TYPE")

    @mod_type.setter
    def mod_type(self, mod_type: str):
        self.awg.validate_opt(mod_type, _MODULATIONS)
        self._write(f"MDWV {mod_type}")

    def _mod_write(self, key: str, value: Any, types: tuple = _MODULATIONS):
        """Set a parameter of the current modulation type."""
        mod_type = self.awg.validate_opt(self.mod_type, types)
        self._write(f"MDWV {mod_type},{key},{value}")

    @property
    def mod_source(self) -> str:
        """Modulating signal source: "INT" or "EXT"."""
        return self._param("MDWV", "SRC")

    @mod_source.setter
    def mod_source(self, source: str):
        self.awg.validate_opt(source, ("INT", "EXT"))
        self._mod_write("SRC", source)

    @property
    def mod_shape(self) -> str:
        """Internal modulating wave: SINE, SQUARE, TRIANGLE, UPRAMP, DNRAMP, NOISE, ARB."""
        return self._param("MDWV", "MDSP")

    @mod_shape.setter
    def mod_shape(self, shape: str):
        self.awg.validate_opt(
            shape, ("SINE", "SQUARE", "TRIANGLE", "UPRAMP", "DNRAMP", "NOISE", "ARB")
        )
        self._mod_write("MDSP", shape, ("AM", "DSBAM", "FM", "PM", "PWM"))

    @property
    def mod_frequency(self) -> float:
        """Modulating frequency [Hz] (key frequency for FSK, ASK and PSK)."""
        params = self._params("MDWV")
        for key in ("FRQ", "KFRQ"):
            if key in params:
                return params[key]
        raise RuntimeError("No modulating frequency (is the modulation enabled?)")

    @mod_frequency.setter
    def mod_frequency(self, frequency: float):
        key = "KFRQ" if self.mod_type in ("FSK", "ASK", "PSK") else "FRQ"
        self._mod_write(key, frequency)

    @property
    def mod_depth(self) -> float:
        """AM depth [%]."""
        return self._param("MDWV", "DEPTH")

    @mod_depth.setter
    def mod_depth(self, depth: float):
        depth = self.awg.validate_range(depth, 0, 120)
        self._mod_write("DEPTH", depth, ("AM",))

    @property
    def mod_deviation(self) -> float:
        """Deviation of FM [Hz], PM [deg] or PWM [%]."""
        return self._param("MDWV", "DEVI")

    @mod_deviation.setter
    def mod_deviation(self, deviation: float):
        self._mod_write("DEVI", deviation, ("FM", "PM", "PWM"))

    @property
    def arb_name(self) -> str:
        """Name of the selected arbitrary waveform."""
        return str(self._param("ARWV", "NAME"))

    @arb_name.setter
    def arb_name(self, name: str):
        self._write(f"ARWV NAME,{name}")

    def upload_waveform(
        self,
        data: np.ndarray,
        name: str,
        frequency: float = 1000.0,
        amplitude: float = 1.0,
        offset: float = 0.0,
        select: bool = True,
    ):
        """Upload an arbitrary waveform and optionally select it on this channel.

        Args:
            data: samples in [-1, 1] (values outside are clipped), at least 8. They
                are sent as 16-bit signed little-endian integers, scaled by 32767.
            name: waveform name (letters, digits and underscore), an existing
                waveform with the same name is replaced.
            frequency: waveform frequency [Hz] stored with the waveform.
            amplitude: peak to peak amplitude [V] stored with the waveform.
            offset: offset [V] stored with the waveform.
            select: select the waveform (``ARWV``) and set the wave type to ARB.
        """
        if not _WAVE_NAME.match(name):
            raise ValueError("Name must be 1-32 letters, digits or underscores.")
        samples = np.asarray(data, dtype=float)
        if samples.ndim != 1 or samples.size < 8:
            raise ValueError("Data must be a 1D array of at least 8 samples.")
        if np.abs(samples).max() > 1:
            log.warning("Waveform samples outside [-1, 1] will be clipped.")
        raw = np.round(np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
        header = (
            f"C{self.number}:WVDT WVNM,{name},FREQ,{frequency},TYPE,8,"
            f"AMPL,{amplitude},OFST,{offset},PHASE,0.0,WAVEDATA,"
        )
        transport = self.awg.transport
        if not transport.is_connected:
            raise ConnectionError(f"Transport to {transport.address} is not connected.")
        with transport.lock:
            transport._write_bytes(
                header.encode() + raw + transport.terminator.encode()
            )
            if select:
                self.arb_name = name
                self.waveform = "ARB"


class SDG6052X(SCPIInstrument):
    """Siglent SDG6052X 2-channel arbitrary waveform generator.

    The channels are accessed with :meth:`channel`. The instrument is controlled
    with the SCPI commands on the raw socket port 5025.
    """

    default_transport = SocketTransport
    transport_defaults = {"port": 5025, "timeout": 10, "delay": 0.1, "no_delay": True}

    f_max = 500e6
    """Maximum output frequency [Hz]."""

    def __init__(
        self, transport: Transport | str, name: str = "SDG6052X", **transport_kwargs
    ):
        """Initialize instrument."""
        super().__init__(transport, name, **transport_kwargs)
        self._channels = {n: SDGChannel(self, n) for n in (1, 2)}

    def channel(self, number: int) -> SDGChannel:
        """Channel 1 or 2."""
        self.validate_opt(number, (1, 2))
        return self._channels[number]
