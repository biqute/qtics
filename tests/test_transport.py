"""Test transports."""

import socket
import threading

import pytest

from qtics.transport import FakeTransport, SerialTransport, SocketTransport


@pytest.fixture
def echo_server():
    """Local TCP server answering every line with "ok:<line>"."""
    server = socket.create_server(("127.0.0.1", 0))
    port = server.getsockname()[1]

    def serve():
        conn, _ = server.accept()
        with conn:
            buffer = b""
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line == b"RAW?":
                        conn.sendall(b"\x01\x02\x03")
                    else:
                        conn.sendall(b"ok:" + line + b"\n")

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield port
    server.close()


def test_socket_lazy():
    """Creating a socket transport does not connect."""
    transport = SocketTransport("192.0.2.1")
    assert not transport.is_connected
    assert transport.port == 5025


def test_socket_query(echo_server):
    """Write, read and raw read over a real local socket."""
    transport = SocketTransport("127.0.0.1", port=echo_server, delay=0)
    transport.connect()
    assert transport.is_connected
    assert transport.query("*IDN?") == "ok:*IDN?"
    transport.write("RAW?")
    assert transport.read_raw(3) == b"\x01\x02\x03"
    transport.close()
    assert not transport.is_connected


def test_socket_write_not_connected():
    """Writing on a closed transport raises."""
    with pytest.raises(ConnectionError):
        SocketTransport("127.0.0.1").write("*IDN?")


def test_serial_lazy():
    """Creating a serial transport does not open the port."""
    transport = SerialTransport("/dev/null", baudrate=115200, terminator="\r")
    assert not transport.is_connected
    assert transport.serial.baudrate == 115200


def test_serial_write_flushes(mocker):
    """Serial write flushes the input buffer and appends the terminator."""
    transport = SerialTransport("/dev/null", terminator="\r")
    mocker.patch.object(transport.serial, "is_open", True)
    flush = mocker.patch.object(transport.serial, "reset_input_buffer")
    write = mocker.patch.object(transport.serial, "write")
    transport.write("ID")
    flush.assert_called_once()
    write.assert_called_once_with(b"ID\r")


def test_fake_answers():
    """Fake transport records commands and returns scripted answers."""
    transport = FakeTransport({"*IDN?": "fake", "DATA?": b"\x00\x01"}, default="0")
    transport.connect()
    assert transport.query("*IDN?") == "fake"
    assert transport.query("OTHER?") == "0"
    transport.write("DATA?")
    assert transport.read_raw(2) == b"\x00\x01"
    assert transport.written == ["*IDN?", "OTHER?", "DATA?"]


def test_fake_callable_answer():
    """Callable answers receive the command."""
    transport = FakeTransport({"ECHO": lambda cmd: cmd.lower()})
    transport.connect()
    assert transport.query("ECHO") == "echo"
