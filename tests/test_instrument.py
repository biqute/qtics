"""Test instrument base class."""

import pytest

from qinst.instrument import Instrument


def mock_query(_, cmd):
    """Mock the query function."""
    if cmd == "*IDN?":
        return "identity"


def test_init():
    """Test initialization."""
    inst = Instrument("name_inst", "address")
    assert isinstance(inst, Instrument)
    assert inst.name == "name_inst"
    assert inst.address == "address"


def test_get_id(mocker):
    """Test get_id function."""
    mocker.patch("qinst.instrument.Instrument.query", new_callable=lambda: mock_query)
    inst = Instrument("name_inst", "address")
    assert "identity" == inst.get_id()


def test_not_implemented_functions():
    """Test functions not implemented."""
    inst = Instrument("name_inst", "address")

    with pytest.raises(NotImplementedError):
        inst.connect()
    with pytest.raises(NotImplementedError):
        inst.disconnect()
    with pytest.raises(NotImplementedError):
        inst.write()
    with pytest.raises(NotImplementedError):
        inst.read()
    with pytest.raises(NotImplementedError):
        inst.query()
