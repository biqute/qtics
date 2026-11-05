"""Test command strings of serial instrument drivers."""

import pytest

from qtics import (
    FSL0010,
    FSL0020,
    FSW0010,
    FSW0020,
    VALON5019,
    Keithley2231A,
    Switch_R591,
)


def mock_io(mocker, inst):
    """Replace write and query of an instrument with mocks."""
    mocker.patch.object(inst, "write")
    mocker.patch.object(inst, "query", return_value="0")
    return inst


@pytest.fixture
def keithley(mocker):
    """Keithley2231A with mocked I/O."""
    return mock_io(mocker, Keithley2231A("/dev/null"))


def test_keithley2231a_channel(keithley):
    """Channel setter must send the channel number."""
    keithley.channel = 2
    keithley.write.assert_called_once_with("INST:NSEL 2")


def test_keithley2231a_channel_invalid(keithley):
    """Invalid channel must raise."""
    with pytest.raises(RuntimeError):
        keithley.channel = 4


def test_keithley2231a_current_limit(keithley):
    """Current limit setter must send CURR:LIMIT."""
    keithley.current_limit = 1
    keithley.write.assert_called_once_with("SOUR:CURR:LIMIT:LEV 1")


@pytest.mark.parametrize(
    "cls, min_freq, max_freq",
    [
        (FSL0010, 0.65e9, 10e9),
        (FSL0020, 0.65e9, 20e9),
        (FSW0010, 0.5e9, 10e9),
        (FSW0020, 0.5e9, 20e9),
    ],
)
def test_quick_synth_freq_limits(cls, min_freq, max_freq):
    """Each QuickSyn model must keep its own frequency limits."""
    synth = cls("/dev/null")
    assert synth.min_freq == min_freq
    assert synth.max_freq == max_freq


def test_valon5019_list_entry(mocker):
    """List entries must be written with 1-based indices, then saved."""
    valon = mock_io(mocker, VALON5019("/dev/null"))
    valon.list_entry = [1e9, 2e9]
    assert valon.write.call_args_list == [
        mocker.call("LI 1 1000000000.0Hz"),
        mocker.call("LI 2 2000000000.0Hz"),
        mocker.call("SAVE"),
    ]


@pytest.mark.parametrize(
    "res, hz", [(["5", "Hz"], 5.0), (["2", "MHz"], 2e6), (["1.5", "GHz"], 1.5e9)]
)
def test_valon5019_freq_result_to_hz(res, hz):
    """Frequency answers are converted to Hz."""
    assert VALON5019.freq_result_to_hz(res) == hz


def test_valon5019_freq_result_unknown_unit():
    """Unknown units must raise."""
    with pytest.raises(ValueError):
        VALON5019.freq_result_to_hz(["1", "THz"])


def test_quick_synth_output_on(mocker):
    """Output state query may answer 1/0."""
    synth = mock_io(mocker, FSL0010("/dev/null"))
    synth.query.return_value = "1"
    assert synth.output_on is True


def test_switch_r591_pulse_length_on_connect(mocker):
    """Pulse length passed at init is sent when connecting."""
    switch = mock_io(mocker, Switch_R591("/dev/null", pulse_lenght=7))
    mocker.patch.object(switch.serial, "open")
    switch.connect()
    switch.write.assert_called_once_with("PUL:LEN 7")
