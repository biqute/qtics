"""Helpers shared by the drivers."""

from typing import Any

import numpy as np

BINBLOCK_TYPES = {"REAL,32": np.float32, "REAL,64": np.float64}


def to_bool(answer: Any) -> bool:
    """Convert an instrument on/off answer (1/0, ON/OFF, TRUE/FALSE) to bool."""
    return str(answer).strip().upper() in ("1", "ON", "TRUE")


def query_binblock(inst, cmd: str, datatype: str = "REAL,64") -> np.ndarray:
    """Send a query and parse the answer in IEEE 488.2 binary block format.

    ``inst`` must provide ``data_format``, ``write``, ``query`` and ``read_raw``.
    With ``datatype="ASC,0"`` the answer is parsed as comma separated values.
    """
    inst.data_format = datatype

    if datatype == "ASC,0":
        return np.array(inst.query(cmd).split(",")).astype(float)

    if datatype not in BINBLOCK_TYPES:
        raise ValueError("Invalid data type selected.")

    with inst.transport.lock:
        inst.write(cmd)
        if inst.read_raw(1) != b"#":
            raise ValueError("Data in buffer is not in binblock format.")
        header_length = int(inst.read_raw(1).decode("utf-8"), 16)
        n_bytes = int(inst.read_raw(header_length).decode("utf-8"))
        raw_data = inst.read_raw(n_bytes)
        if inst.read_raw(1) != b"\n":
            raise ValueError("Data not terminated correctly.")

    return np.frombuffer(raw_data, dtype=BINBLOCK_TYPES[datatype]).astype(float)
