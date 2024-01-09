"""Test network instrument base class."""
import socket

import pytest

from qtics.instrument import Instrument
from qtics.network_inst import NetworkInst


def mock_pass(_=None, __=None):
    """Mock function with no return."""
    pass


def mock_read(_, __):
    """Mock read function."""
    return b"test_read\n"


class TestNetworklInst:
    """Test class for NetworkInst."""

    @pytest.fixture
    def network_inst(self, mocker):
        """Patch functions used in other methods."""
        mocker.patch("ipaddress.ip_address", new_callable=lambda: mock_pass)
        mocker.patch("socket.socket.connect", new_callable=lambda: mock_pass)
        mocker.patch("socket.socket.shutdown", new_callable=lambda: mock_pass)
        mocker.patch("socket.socket.close", new_callable=lambda: mock_pass)
        return NetworkInst("name_inst", "address")

    def test_init(self, network_inst):
        """Test initialization."""
        inst = network_inst
        assert isinstance(inst, NetworkInst)
        assert isinstance(inst, Instrument)
        assert inst.name == "name_inst"
        assert inst.address == "address"
        assert inst.port == 5025
        assert inst.sleep == 0.1
        assert isinstance(inst.socket, socket.socket)
        assert inst.no_delay == True
        assert inst.socket.timeout == 10

    def test_del(self, network_inst):
        """Test destructor."""
        inst = network_inst
        inst.connect()
        del inst

    def test_connect(self, network_inst):
        """Test connect function."""
        inst = network_inst
        inst.connect()

    def test_disconnect(self, network_inst):
        """Test disconnect function."""
        inst = network_inst
        inst.connect()
        inst.disconnect()

    def test_write(self, network_inst, mocker):
        """Test write function."""
        mocker.patch("socket.socket.sendall", new_callable=lambda: mock_pass)
        inst = network_inst
        inst.write("test_cmd")

    def test_read(self, network_inst, mocker):
        """Test read function."""
        mocker.patch("socket.socket.recv", new_callable=lambda: mock_read)
        inst = network_inst
        assert inst.read() == "test_read"

    def test_query(self, network_inst, mocker):
        """Test query function."""
        mocker.patch("socket.socket.recv", new_callable=lambda: mock_read)
        mocker.patch("socket.socket.sendall", new_callable=lambda: mock_pass)
        inst = network_inst
        assert inst.query("CMD?") == "test_read"
        with pytest.raises(ValueError):
            inst.query("CMD")

    def test_validate_opt(self, network_inst):
        """Test validate_opt function."""
        inst = network_inst
        with pytest.raises(RuntimeError):
            inst.validate_opt("OPT3", ("OPT1", "OPT2"))

    def test_validate_range(self, network_inst):
        """Test validate_range function."""
        inst = network_inst
        assert inst.validate_range(19.3, 1, 100) == 19.3
        assert inst.validate_range(-19.3, 1, 100) == 1
        assert inst.validate_range(193, 1, 100) == 100

    def test_update_defaults(self, network_inst):
        """Test update defaults function."""
        network_inst.update_defaults(sleep=5, port=1000)
        assert network_inst.defaults == {"sleep": 5, "port": 1000}
        with pytest.raises(RuntimeError):
            network_inst.update_defaults(noattr=1)

    def test_clear_defaults(self, network_inst):
        """Test clear defaults function."""
        network_inst.update_defaults(sleep=5, port=1000)
        network_inst.clear_defaults()
        assert network_inst.defaults == {}

    def test_set_defaults(self, network_inst):
        """Test set defaults function."""
        network_inst.update_defaults(sleep=5, port=1000)
        network_inst.set_defaults()
        assert network_inst.sleep == 5
        assert network_inst.port == 1000
