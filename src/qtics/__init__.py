"""Qtics module.

Drivers are imported lazily, so that optional heavy dependencies (e.g. autobahn,
niscope) are loaded only when the corresponding driver is used.
"""

# nopycln: file
import importlib
import importlib.metadata as im
from typing import TYPE_CHECKING

__version__ = im.version(__package__)

from qtics.logger import qtics_log as log  # isort: skip

_EXPORTS = {
    "BaseExperiment": "qtics.experiment",
    "Experiment": "qtics.experiment",
    "MonitorExperiment": "qtics.experiment",
    "VNAN9916A": "qtics.instruments.keysight.n9916a",
    "SAN9916A": "qtics.instruments.keysight.n9916a",
    "ZNB": "qtics.instruments.rohde_schwarz.znb",
    "FSV3030": "qtics.instruments.rohde_schwarz.fsv3030",
    "SMA100B": "qtics.instruments.rohde_schwarz.sma100b",
    "Keithley2231A": "qtics.instruments.keithley.k2231a",
    "Keithley6514": "qtics.instruments.keithley.k6514",
    "QuickSyn": "qtics.instruments.ni.quicksyn",
    "FSL0010": "qtics.instruments.ni.quicksyn",
    "FSL0020": "qtics.instruments.ni.quicksyn",
    "FSW0010": "qtics.instruments.ni.quicksyn",
    "FSW0020": "qtics.instruments.ni.quicksyn",
    "Pxie5170R": "qtics.instruments.ni.pxie5170r",
    "Valon5019": "qtics.instruments.valon.v5019",
    "SIM928": "qtics.instruments.srs.sim928",
    "Triton": "qtics.instruments.oxford.triton",
    "Proteox": "qtics.instruments.oxford.proteox",
    "AsyncProteox": "qtics.instruments.oxford.proteox",
    "R591Switch": "qtics.instruments.arduino.r591_switch",
    "Kratos3494Attenuator": "qtics.instruments.arduino.kratos_3494",
}

# Names of qtics < 0.1, kept for backward compatibility
_ALIASES = {
    "RSZNB": "ZNB",
    "VALON5019": "Valon5019",
    "FSQS": "QuickSyn",
    "Pxie570R": "Pxie5170R",
    "Switch_R591": "R591Switch",
    "Radiall_R591722600": "R591Switch",
    "Attenuator_3494_64": "Kratos3494Attenuator",
    "Kratos_349464": "Kratos3494Attenuator",
    "SRS_SIM928": "SIM928",
    "Keithley_6514": "Keithley6514",
    "Keithley_2231A": "Keithley2231A",
}

__all__ = ["log", *_EXPORTS, *_ALIASES]


def __getattr__(name: str):
    """Import exported classes on first access."""
    target = _ALIASES.get(name, name)
    if target in _EXPORTS:
        try:
            module = importlib.import_module(_EXPORTS[target])
        except ModuleNotFoundError as exc:
            if exc.name is None or exc.name.split(".")[0] == "qtics":
                raise
            raise ModuleNotFoundError(
                f"{name} requires the optional package '{exc.name}', install it to "
                "use this driver."
            ) from exc
        value = getattr(module, target)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'qtics' has no attribute '{name}'")


def __dir__():
    """List the exported names."""
    return sorted(__all__)


if TYPE_CHECKING:
    from qtics.experiment import BaseExperiment, Experiment, MonitorExperiment
    from qtics.instruments.arduino.kratos_3494 import Kratos3494Attenuator
    from qtics.instruments.arduino.r591_switch import R591Switch
    from qtics.instruments.keithley.k2231a import Keithley2231A
    from qtics.instruments.keithley.k6514 import Keithley6514
    from qtics.instruments.keysight.n9916a import SAN9916A, VNAN9916A
    from qtics.instruments.ni.pxie5170r import Pxie5170R
    from qtics.instruments.ni.quicksyn import (
        FSL0010,
        FSL0020,
        FSW0010,
        FSW0020,
        QuickSyn,
    )
    from qtics.instruments.oxford.proteox import AsyncProteox, Proteox
    from qtics.instruments.oxford.triton import Triton
    from qtics.instruments.rohde_schwarz.fsv3030 import FSV3030
    from qtics.instruments.rohde_schwarz.sma100b import SMA100B
    from qtics.instruments.rohde_schwarz.znb import ZNB
    from qtics.instruments.srs.sim928 import SIM928
    from qtics.instruments.valon.v5019 import Valon5019

    RSZNB = ZNB
    VALON5019 = Valon5019
    FSQS = QuickSyn
    Pxie570R = Pxie5170R
    Switch_R591 = R591Switch
    Radiall_R591722600 = R591Switch
    Attenuator_3494_64 = Kratos3494Attenuator
    Kratos_349464 = Kratos3494Attenuator
    SRS_SIM928 = SIM928
    Keithley_6514 = Keithley6514
    Keithley_2231A = Keithley2231A
