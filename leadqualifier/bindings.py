"""Host composition: Bindings = compose(catalog, mounts).

TEACHING NOTE: Fake fills Unmounted. A mounted plugin occupies that
channel only if the catalog declares Send of it. Occupancy is sqlite
mounts, not an env send flag. The Email factory is imported from
`integrations.py`, not here. Mount/unmount invalidates the singleton;
env keys still require process restart.

⭐ ENFORCED BY: `tests/test_integrations.py`, `tests/test_bindings.py`.
"""

from __future__ import annotations

from .comms import Bindings, FakeComms, fake_bindings

_bindings: Bindings | None = None


def default_bindings() -> Bindings:
    from .integrations import compose_from_ledger
    from .ledger import get_ledger

    return compose_from_ledger(get_ledger())


def get_bindings() -> Bindings:
    global _bindings
    if _bindings is None:
        _bindings = default_bindings()
    return _bindings


def invalidate_bindings() -> None:
    global _bindings
    _bindings = None


def reset_bindings_for_tests(bindings: Bindings | None = None) -> Bindings:
    global _bindings
    _bindings = bindings if bindings is not None else fake_bindings(FakeComms())
    return _bindings
