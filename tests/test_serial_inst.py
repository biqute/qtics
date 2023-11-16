"""Test serial instrument base class."""

from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE, Serial

from qinst.instrument import Instrument
from qinst.serial_inst import SerialInst


def mock_pass(_=None, __=None):
    """Mock function with no return."""
    pass


def mock_read(_, __):
    """Mock read function."""
    return "test_read"


def test_init():
    """Test initialization."""
    inst = SerialInst("name_inst", "address")
    assert isinstance(inst, SerialInst)
    assert isinstance(inst, Instrument)
    assert inst.name == "name_inst"
    assert inst.address == "address"
    assert isinstance(inst.serial, Serial)
    assert inst.serial.port == "address"
    assert inst.serial.baudrate == 9600
    assert inst.serial.bytesize == EIGHTBITS
    assert inst.serial.parity == PARITY_NONE
    assert inst.serial.stopbits == STOPBITS_ONE
    assert inst.serial.timeout == 5
    assert inst.sleep == 0


def test_del(mocker):
    """Test destructor."""
    mocker.patch("serial.Serial.open", new_callable=lambda: mock_pass)
    mocker.patch("serial.Serial.close", new_callable=lambda: mock_pass)
    inst = SerialInst("name_inst", "address")
    inst.connect()
    del inst


def test_connect(mocker):
    """Test connect function."""
    mocker.patch("serial.Serial.open", new_callable=lambda: mock_pass)
    inst = SerialInst("name_inst", "address")
    inst.connect()
    assert inst.is_connected


def test_disconnect(mocker):
    """Test disconnect function."""
    mocker.patch("serial.Serial.open", new_callable=lambda: mock_pass)
    mocker.patch("serial.Serial.close", new_callable=lambda: mock_pass)
    inst = SerialInst("name_inst", "address")
    inst.connect()
    inst.serial.is_open = True  # patch connection
    inst.disconnect()
    assert not inst.is_connected


def test_write(mocker):
    """Test write function."""
    mocker.patch("serial.Serial.write", new_callable=lambda: mock_pass)
    inst = SerialInst("name_inst", "address")
    inst.write("test_cmd")


def test_read(mocker):
    """Test read function."""
    mocker.patch("serial.Serial.read", new_callable=lambda: mock_read)
    mocker.patch("serial.Serial.in_waiting", new_callable=lambda: 5)
    inst = SerialInst("name_inst", "address")
    assert inst.read() == None
    inst.serial.is_open = True
    inst.serial.fd = None
    assert inst.read() == "test_read"


def test_query(mocker):
    """Test query function."""
    mocker.patch("serial.Serial.write", new_callable=lambda: mock_pass)
    mocker.patch("serial.Serial.read", new_callable=lambda: mock_read)
    mocker.patch("serial.Serial.in_waiting", new_callable=lambda: 5)
    inst = SerialInst("name_inst", "address")
    assert inst.query("cmd") == None
    inst.serial.is_open = True
    inst.serial.fd = None
    assert inst.read() == "test_read"
