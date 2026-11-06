"""Hardware tests of the Oxford Proteox cryostat.

Config: ``[Proteox]``, can be empty, it only enables the test. Credentials
(``WAMP_ROUTER_URL``, ``WAMP_REALM``, ``WAMP_USER``, ``WAMP_USER_SECRET``) come
from the environment or the usual ``.env`` file. Optional non-secret keys:
``timeout``.

STRICTLY READ-ONLY: connect and a few sensor reads. No setter is ever called,
there is no output test.
"""

import pytest

pytest.importorskip("autobahn", reason="needs the proteox extra")

from qtics import Proteox  # noqa: E402


@pytest.fixture(scope="module")
def cryostat(open_instrument):
    """Connected cryostat."""
    return open_instrument(Proteox)


def test_connected(cryostat):
    """The WAMP session is open."""
    assert cryostat.is_connected


def test_readonly(cryostat):
    """Remote mode flag, state and temperatures answer with the expected types."""
    assert isinstance(cryostat.is_in_remote(), bool)
    state = cryostat.get_state()
    assert isinstance(state, str) and state
    for key in ("MC_T", "STILL_T", "CP_T", "PT1_T1", "PT2_T1"):
        temperature = getattr(cryostat, f"get_{key}")()
        assert 0 < temperature < 400, key
