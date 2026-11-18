"""Sequencer / dialer port. FakeComms is the default binding for every channel.

TEACHING NOTE: Queue / HandOff already authorized the send. This module is the
other half, twin of `relay.py` / `hubspot.py`. `Relay` stays HubSpot.
`Outbound` is this destination. Bindings is a Map Channel → Comms, host-only,
not stored on Open. Drain looks up `draft.channel`. A missing key is
`channel_unbound`, not a vendor exception. Revealed plus no address is
`no_address`, not an invented mailbox.

⭐ ENFORCED BY: `tests/test_comms.py`, `tests/test_bindings.py`.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from .workitem import (
    Calendar,
    CaseStudy,
    Channel,
    Copy,
    DeclineDraft,
    Draft,
    Email,
    Form,
    LinkedIn,
    MarkDispatched,
    MarkDispatchFailed,
    Offer,
    QualifyingQuestion,
    RinglessVoicemail,
    Sms,
    Unjudged,
    Voice,
    assert_never,
)

log = logging.getLogger("firstread.comms")

CHANNEL_KINDS: tuple[str, ...] = (
    Email().kind,
    LinkedIn().kind,
    Voice().kind,
    Sms().kind,
    RinglessVoicemail().kind,
)


class NoAddress(Exception):
    def __init__(self) -> None:
        super().__init__("no_address")


class ChannelUnbound(Exception):
    def __init__(self) -> None:
        super().__init__("channel_unbound")


class Comms(Protocol):
    def dispatch(self, *, work_item_id: str, channel: Channel, draft: Draft, payload: dict[str, Any]) -> str: ...


def _strip(raw: object) -> str | None:
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def address_for(channel: Channel, payload: dict[str, Any]) -> str | None:
    """Exhaustive on Channel. LinkedIn is never email.

    CSV intake has no `person.linkedin` today — Queue of LinkedIn is
    `no_address` until a later source supplies it.
    """
    person = payload.get("person") or {}
    company = payload.get("company") or {}
    if isinstance(channel, Email):
        return _strip(person.get("email"))
    if isinstance(channel, LinkedIn):
        return _strip(person.get("linkedin")) or _strip(company.get("linkedin"))
    if isinstance(channel, (Voice, Sms, RinglessVoicemail)):
        return _strip(person.get("phone"))
    return assert_never(channel)


def offer_text(offer: Offer) -> str:
    """Exhaustive. FakeComms records this; an Email adapter uses it as personalization."""
    if isinstance(offer, (Copy, QualifyingQuestion, DeclineDraft)):
        return offer.text
    if isinstance(offer, Calendar):
        return " or ".join(offer.slots)
    if isinstance(offer, (CaseStudy, Form)):
        return offer.url
    return assert_never(offer)


class FakeComms:
    """In-process dispatcher. Records calls; never touches a vendor or a phone."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.n = 0

    def dispatch(self, *, work_item_id: str, channel: Channel, draft: Draft, payload: dict[str, Any]) -> str:
        addr = address_for(channel, payload)
        if addr is None:
            raise NoAddress()
        self.n += 1
        remote = f"fake-comms-{self.n}"
        self.calls.append(
            {
                "work_item_id": work_item_id,
                "channel": channel.kind,
                "text": offer_text(draft.offer),
                "address": addr,
                "remote_id": remote,
            }
        )
        return remote


class Bindings:
    """Map Channel → Comms. Incomplete is speakable; lookup then fails ChannelUnbound.

    TEACHING NOTE: production `default_bindings` is total (Fake on every key).
    `channel_unbound` is a missing key, not an unbound vendor.
    """

    def __init__(self, by_kind: dict[str, Comms]):
        self.by_kind = dict(by_kind)

    def lookup(self, channel: Channel) -> Comms:
        comms = self.by_kind.get(channel.kind)
        if comms is None:
            raise ChannelUnbound()
        return comms

    def with_email(self, comms: Comms) -> Bindings:
        return Bindings({**self.by_kind, "email": comms})


def fake_bindings(fake: FakeComms | None = None) -> Bindings:
    """Fake on every Channel. One FakeComms instance; dispatch is exhaustive."""
    adapter = fake if fake is not None else FakeComms()
    return Bindings({kind: adapter for kind in CHANNEL_KINDS})


def drain_outbound(ledger, bindings: Bindings) -> dict[str, int]:
    dispatched = failed = 0
    for row in ledger.list_pending_outbound():
        wid = row["id"]
        payload = json.loads(row["payload_json"])
        state = ledger.snapshot_state(row)
        outbound = state.outbound
        draft = getattr(outbound, "draft", None)
        if draft is None:
            ledger.apply_command(wid, MarkDispatchFailed("no_draft"), Unjudged())
            failed += 1
            continue
        try:
            adapter = bindings.lookup(draft.channel)
            remote = adapter.dispatch(work_item_id=wid, channel=draft.channel, draft=draft, payload=payload)
            out = ledger.apply_command(wid, MarkDispatched(remote), Unjudged())
            if getattr(out, "kind", None) == "error":
                log.warning("mark dispatched refused id=%s %s", wid, out.error.kind)
                failed += 1
            else:
                dispatched += 1
        except ChannelUnbound:
            ledger.apply_command(wid, MarkDispatchFailed("channel_unbound"), Unjudged())
            failed += 1
        except NoAddress:
            ledger.apply_command(wid, MarkDispatchFailed("no_address"), Unjudged())
            failed += 1
        except Exception as exc:
            ledger.apply_command(wid, MarkDispatchFailed(f"{type(exc).__name__}: {exc}"[:240]), Unjudged())
            failed += 1
            log.warning("comms failed id=%s: %s", wid, exc)
    return {"dispatched": dispatched, "failed": failed}
