"""Test the Valon 5019 driver."""

import pytest

from qtics import Valon5019
from qtics.instruments.types import RFSource
from qtics.transport import FakeTransport, SerialTransport


def echo(cmd, answer):
    """Valon answer: echo of the command (length cmd + terminator + 2) and values."""
    return "x" * (len(cmd) + 1 + 2) + answer


@pytest.fixture
def valon():
    """Connected Valon on a fake transport with the Valon terminator."""
    inst = Valon5019(FakeTransport(terminator="\r"))
    inst.transport.connect()
    return inst


def script(valon, cmd, answer):
    """Script the answer of ``cmd``."""
    valon.transport.answers[cmd] = echo(cmd, answer)


def test_is_rf_source(valon):
    """Valon5019 implements the RFSource interface."""
    assert isinstance(valon, RFSource)


def test_transport_defaults():
    """Serial transport with the Valon defaults."""
    inst = Valon5019("/dev/null")
    assert isinstance(inst.transport, SerialTransport)
    assert inst.transport.terminator == "\r"
    assert inst.transport.delay == 0.3
    assert inst.transport.timeout == 10
    assert inst.transport.serial.baudrate == 9600


def test_list_entry(valon):
    """List entries must be written with 1-based indices, then saved."""
    valon.list_entry = [1e9, 2e9]
    assert valon.transport.written == [
        "LI 1 1000000000.0Hz",
        "LI 2 2000000000.0Hz",
        "SAVE",
    ]


def test_list_entry_getter(valon):
    """Reading the list is not supported."""
    with pytest.raises(NotImplementedError):
        _ = valon.list_entry


@pytest.mark.parametrize(
    "res, hz", [(["5", "Hz"], 5.0), (["2", "MHz"], 2e6), (["1.5", "GHz"], 1.5e9)]
)
def test_freq_result_to_hz(res, hz):
    """Frequency answers are converted to Hz."""
    assert Valon5019.freq_result_to_hz(res) == hz


def test_freq_result_unknown_unit():
    """Unknown units must raise."""
    with pytest.raises(ValueError):
        Valon5019.freq_result_to_hz(["1", "THz"])


def test_read_parses_echo(valon):
    """The command echo is removed and the answer is split in tokens."""
    script(valon, "F", "F 1000 MHz;\r\n\r-->")
    assert valon.query("F") == ["1000", "MHz"]


def test_frequency(valon):
    """Frequency getter returns Hz, setter sends F command."""
    script(valon, "F", "F 2.5 GHz;\r\n\r-->")
    assert valon.frequency == 2.5e9
    valon.frequency = 3e9
    assert valon.transport.written[-1] == "F3000000000.0Hz"


def test_power(valon):
    """Power getter returns float, setter sends PWR."""
    script(valon, "PWR", "PWR -5.5;\r\n\r-->")
    assert valon.power == -5.5
    valon.power = 10
    assert valon.transport.written[-1] == "PWR 10"


def test_output(valon):
    """Output is a bool property."""
    script(valon, "OEN", "OEN 1;\r\n\r-->")
    assert valon.output is True
    script(valon, "OEN", "OEN 0;\r\n\r-->")
    assert valon.output is False
    valon.output = True
    valon.output = False
    assert valon.transport.written[-2:] == ["OEN 1", "OEN 0"]  # codespell:ignore


def test_sweep_names(valon):
    """Sweep range uses f_start/f_stop/f_step."""
    valon.f_start = 1e9
    valon.f_stop = 2e9
    valon.f_step = 1e6
    assert valon.transport.written == [
        "STAR 1000000000.0Hz",
        "STOP 2000000000.0Hz",
        "STEP 1000000.0Hz",
    ]


def test_cw_offset_and_step(valon):
    """CW offset and step have their own commands."""
    valon.f_offset = 1e6
    valon.f_step_cw = 1e3
    assert valon.transport.written == ["OFF 1000000.0Hz", "FS 1000.0Hz"]


def test_mode(valon):
    """Mode validation."""
    valon.mode = "SWE"
    assert valon.transport.written == ["MOD SWE"]
    with pytest.raises(ValueError):
        valon.mode = "BAD"


def test_ref_source(valon):
    """Reference source answers a string."""
    script(valon, "REFS", "REFS 1;\r\n\r-->")
    assert valon.ref_source == "External"
    valon.ref_source = "Internal"
    assert valon.transport.written[-1] == "REFS 0"


def test_reset_and_id(valon):
    """Reset sends RST, ID joins the tokens."""
    valon.reset(defaults=False)
    assert valon.transport.written == ["RST"]
    script(valon, "ID", "ID Valon 5019;\r\n\r-->")
    assert valon.get_id() == "Valon 5019"


@pytest.mark.parametrize(
    "value, cmd", [("OFF", "OEN 0"), ("False", "OEN 0"), ("ON", "OEN 1")]
)
def test_output_string_values(valon, value, cmd):
    """Strings accepted by the old rf_status are still understood."""
    valon.output = value
    assert valon.transport.written[-1] == cmd
