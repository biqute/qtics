"""Common utils for network instruments."""

import numpy as np


def query_data(inst, cmd, datatype="REAL,64") -> np.ndarray:
    """Send a command and parses response in IEEE 488.2 binary block format."""
    inst.data_format = datatype

    if datatype == "ASC,0":
        return np.array(inst.query(cmd).split(",")).astype(float)

    map_types = {"REAL,32": np.float32, "REAL,64": np.float64}
    if datatype not in map_types:
        raise ValueError("Invalid data type selected.")

    inst.write(cmd)

    assert inst.socket is not None

    # Read # character, raise exception if not present.
    if inst.socket.recv(1) != b"#":
        raise ValueError("Data in buffer is not in binblock format.")

    # Extract header length and number of bytes in binblock.
    header_length = int(inst.socket.recv(1).decode("utf-8"), 16)
    n_bytes = int(inst.socket.recv(header_length).decode("utf-8"))

    # Create a buffer and expose a memoryview for efficient socket reading
    raw_data = bytearray(n_bytes)
    buf = memoryview(raw_data)

    while n_bytes:
        # Read data from instrument into buffer.
        bytes_recv = inst.socket.recv_into(buf, n_bytes)
        # Slice buffer to preserve data already written to it.
        buf = buf[bytes_recv:]
        # Subtract bytes received from total bytes.
        n_bytes -= bytes_recv

    # Receive termination character.
    term = inst.socket.recv(1)
    if term != b"\n":
        raise ValueError("Data not terminated correctly.")

    return np.frombuffer(raw_data, dtype=map_types[datatype]).astype(float)
