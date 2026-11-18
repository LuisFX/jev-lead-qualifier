"""Host composition: Bindings = Map Channel → Comms.

TEACHING NOTE: Fake fills every key. A live Email vendor, when env is on,
replaces only the Email key. This file is the only Instantly import.
`decide` does not import it. `comms.py` does not import it.

⭐ ENFORCED BY: `tests/test_bindings.py`.
"""

from __future__ import annotations

from . import config
from .comms import Bindings, FakeComms, fake_bindings

_bindings: Bindings | None = None


def default_bindings() -> Bindings:
    b = fake_bindings()
    if config.instantly_send_enabled():
        from .instantly import InstantlyEmail

        b = b.with_email(InstantlyEmail())
    return b


def get_bindings() -> Bindings:
    global _bindings
    if _bindings is None:
        _bindings = default_bindings()
    return _bindings


def reset_bindings_for_tests(bindings: Bindings | None = None) -> Bindings:
    global _bindings
    _bindings = bindings if bindings is not None else fake_bindings(FakeComms())
    return _bindings
