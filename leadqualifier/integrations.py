"""Catalog, mounts, compose. Port of `integrations.fsx`.

TEACHING NOTE: Queue / HandOff still authorize. This module occupies a
Channel slot. Unmounted is Fake. Mounted is a plugin that declares
`Send` of that channel. Two plugins on one slot is unspeakable (one
Mount per Channel). A plugin that only sends Email cannot occupy Voice.

`compose` is total on Channel. Unmounted is not `channel_unbound`.
Mounted without a process credential is `plugin_unready` on dispatch —
Fake is not silently kept while sqlite says Mounted.

Secrets stay in env. This file never stores a key. Ready is "the process
has the credential." Env is resolved at process start; after adding a
key, restart. ⭐ ENFORCED BY: `tests/test_integrations.py`.
The catalog factory for Email lives in `instantly.py`; this file is the
only composition import of it. `decide` does not import it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from . import config
from .comms import Bindings, Comms, FakeComms, PluginUnready
from .workitem import Channel, Email, LinkedIn, RinglessVoicemail, Sms, Voice, assert_never

EMAIL_PLUGIN = "email-plugin"


@dataclass(frozen=True)
class PluginId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or self.value != self.value.strip():
            raise ValueError("plugin_id")


def plugin_id(raw: str) -> PluginId:
    v = raw.strip()
    if not v:
        raise ValueError("plugin_id")
    return PluginId(v)


@dataclass(frozen=True)
class Send:
    channel: Channel
    kind: Literal["send"] = "send"


Capability = Send


@dataclass(frozen=True)
class Unmounted:
    kind: Literal["unmounted"] = "unmounted"


@dataclass(frozen=True)
class Mounted:
    plugin_id: PluginId
    kind: Literal["mounted"] = "mounted"


Mount = Unmounted | Mounted


@dataclass(frozen=True)
class UnknownPlugin:
    kind: Literal["unknown_plugin"] = "unknown_plugin"


@dataclass(frozen=True)
class CapabilityMismatch:
    kind: Literal["capability_mismatch"] = "capability_mismatch"


ComposeError = UnknownPlugin | CapabilityMismatch


@dataclass(frozen=True)
class ComposeOk:
    bindings: Bindings
    kind: Literal["ok"] = "ok"


@dataclass(frozen=True)
class ComposeErr:
    error: ComposeError
    kind: Literal["error"] = "error"


ALL_CHANNELS: tuple[Channel, ...] = (
    Email(),
    LinkedIn(),
    Voice(),
    Sms(),
    RinglessVoicemail(),
)


def host_catalog() -> dict[PluginId, frozenset[Send]]:
    """Host catalog. Plugin ids are opaque labels; the Email factory is InstantlyEmail."""
    return {PluginId(EMAIL_PLUGIN): frozenset({Send(Email())})}


class UnreadyComms:
    """Mounted plugin whose process lacks the credential. Dispatch is loud."""

    def dispatch(self, *, work_item_id: str, channel: Channel, draft, payload) -> str:
        raise PluginUnready()


def plugin_ready(pid: PluginId) -> bool:
    if pid.value == EMAIL_PLUGIN:
        return config.instantly_api_key() is not None and config.instantly_campaign_id() is not None
    return False


def adapter_for(pid: PluginId, channel: Channel) -> Comms:
    if pid.value == EMAIL_PLUGIN and isinstance(channel, Email):
        if plugin_ready(pid):
            from .instantly import InstantlyEmail

            return InstantlyEmail()
        return UnreadyComms()
    raise AssertionError(f"unhandled plugin={pid.value!r} channel={channel.kind}")


def compose(
    catalog: dict[PluginId, frozenset[Send]],
    mounts: dict[str, Mount],
    *,
    fake: FakeComms | None = None,
) -> ComposeOk | ComposeErr:
    adapter_fake = fake if fake is not None else FakeComms()
    by_kind: dict[str, Comms] = {}
    for ch in ALL_CHANNELS:
        mount = mounts.get(ch.kind, Unmounted())
        if isinstance(mount, Unmounted):
            by_kind[ch.kind] = adapter_fake
            continue
        if isinstance(mount, Mounted):
            caps = catalog.get(mount.plugin_id)
            if caps is None:
                return ComposeErr(UnknownPlugin())
            if Send(ch) not in caps:
                return ComposeErr(CapabilityMismatch())
            by_kind[ch.kind] = adapter_for(mount.plugin_id, ch)
            continue
        assert_never(mount)
    return ComposeOk(Bindings(by_kind))


def candidates_for(catalog: dict[PluginId, frozenset[Send]], channel: Channel) -> list[str]:
    return [pid.value for pid, caps in catalog.items() if Send(channel) in caps]


def mounts_from_rows(rows: dict[str, str]) -> dict[str, Mount]:
    """sqlite channel → plugin_id. Absence is Unmounted. Do not store `fake`."""
    out: dict[str, Mount] = {}
    for ch in ALL_CHANNELS:
        raw = rows.get(ch.kind)
        if raw is None:
            out[ch.kind] = Unmounted()
        else:
            out[ch.kind] = Mounted(plugin_id(raw))
    return out


def load_mounts(ledger) -> dict[str, Mount]:
    return mounts_from_rows(ledger.list_mounts())


def compose_from_ledger(ledger) -> Bindings:
    out = compose(host_catalog(), load_mounts(ledger))
    if isinstance(out, ComposeErr):
        raise ValueError(f"compose: {out.error.kind}")
    return out.bindings


def slot_snapshot(ledger) -> list[dict[str, object]]:
    """JSON for GET /api/integrations. Never includes a secret value."""
    catalog = host_catalog()
    mounts = load_mounts(ledger)
    slots: list[dict[str, object]] = []
    for ch in ALL_CHANNELS:
        mount = mounts[ch.kind]
        if isinstance(mount, Unmounted):
            slots.append(
                {
                    "channel": ch.kind,
                    "mount": {"kind": "unmounted"},
                    "ready": True,
                    "needs_credential": False,
                    "candidates": candidates_for(catalog, ch),
                }
            )
            continue
        if isinstance(mount, Mounted):
            ready = plugin_ready(mount.plugin_id)
            slots.append(
                {
                    "channel": ch.kind,
                    "mount": {"kind": "mounted", "plugin_id": mount.plugin_id.value},
                    "ready": ready,
                    "needs_credential": not ready,
                    "candidates": candidates_for(catalog, ch),
                }
            )
            continue
        assert_never(mount)
    return slots


def try_mount(ledger, channel: Channel, pid: PluginId) -> ComposeOk | ComposeErr:
    mounts = load_mounts(ledger)
    mounts[channel.kind] = Mounted(pid)
    return compose(host_catalog(), mounts)


def try_unmount(ledger, channel: Channel) -> ComposeOk | ComposeErr:
    mounts = load_mounts(ledger)
    mounts[channel.kind] = Unmounted()
    return compose(host_catalog(), mounts)


def mounts_status(ledger) -> dict[str, dict[str, object]]:
    """`/api/status` summary: kind unmounted|mounted, ready bool. Never keys."""
    out: dict[str, dict[str, object]] = {}
    for slot in slot_snapshot(ledger):
        kind = slot["channel"]
        assert isinstance(kind, str)
        mount = slot["mount"]
        assert isinstance(mount, dict)
        out[kind] = {"kind": mount["kind"], "ready": slot["ready"]}
    return out
