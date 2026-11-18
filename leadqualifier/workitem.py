"""Work-item aggregate: port of `workitem.fsx`. The oracle owns the types.

TEACHING NOTE: think Decider (`decide` / `evolve`), then write Python to match.
`decide` is total: every command against every state is Ok events or a named refusal.
`evolve` is a fold and *can* refuse (Arrived on Open → `not_arrived`). Judgement is
an argument, not a field of State. Contact is derived (`contactOf`): Hidden on
Unreviewed and Dismissed, Revealed after Flag, Queue, or HandOff.

Relay is HubSpot. Outbound is the sequencer / dialer / SMS / RVM slot (F#
`Outbound.Pending` is class `Awaiting` here so it does not collide with HubSpot
`Pending`). Draft is `{ Channel, Offer }`. Queue of Warm/Hot emits `Queued`
then `OutboundPending`. Queue of Nurture is a decision with `NoSend`.
RecordReply of whitespace is `empty_reply`. Empty Offer is `empty_draft`.
Nonempty `DeclineDraft` is `not_sendable`.

⭐ ENFORCED BY: `leadqualifier/workitem.fsx` (the law floor) and `tests/test_workitem.py`
(the same laws, ported). A host that skips `decide` and writes a column is a defect.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, Never


def assert_never(x: Never) -> Never:
    raise AssertionError(f"unhandled: {x!r}")


def _blank(s: str) -> bool:
    return not s.strip()


# --- identity -----------------------------------------------------------------


@dataclass(frozen=True)
class WorkItemId:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("WorkItemId")


@dataclass(frozen=True)
class PersonId:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("PersonId")


@dataclass(frozen=True)
class ImportId:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("ImportId")


@dataclass(frozen=True)
class IcpVersionId:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("IcpVersionId")


# --- arrival ------------------------------------------------------------------


@dataclass(frozen=True)
class ApolloPerson:
    """People Search hit. Email is not on this record — see `contactOf`."""

    person_id: PersonId
    kind: Literal["apollo_person"] = "apollo_person"


@dataclass(frozen=True)
class CsvRow:
    import_id: ImportId
    row: int
    kind: Literal["csv_row"] = "csv_row"

    def __post_init__(self) -> None:
        if self.row < 1:
            raise ValueError("CsvRow.row")


Arrival = ApolloPerson | CsvRow


def decode_arrival(kind: str, person_id: str | None, import_id: str | None, import_row: int | None) -> Arrival:
    """One constructor that can fail. Junk `kind` names the field."""
    if kind == "apollo_person":
        if not person_id:
            raise ValueError("arrival.person_id")
        return ApolloPerson(PersonId(person_id))
    if kind == "csv_row":
        if not import_id:
            raise ValueError("arrival.import_id")
        if import_row is None:
            raise ValueError("arrival.import_row")
        return CsvRow(ImportId(import_id), int(import_row))
    raise ValueError(f"arrival.kind={kind!r}")


# --- judgement / disposition / relay ------------------------------------------

Tier = Literal["hot", "warm", "nurture", "disqualify", "existing"]
TIERS: tuple[Tier, ...] = ("hot", "warm", "nurture", "disqualify", "existing")


def decode_tier(value: str) -> Tier:
    if value in TIERS:
        return value  # type: ignore[return-value]
    raise ValueError(f"judgement.tier={value!r}")


@dataclass(frozen=True)
class Unjudged:
    kind: Literal["unjudged"] = "unjudged"


@dataclass(frozen=True)
class Judged:
    icp_version_id: IcpVersionId
    tier: Tier
    needs_review: bool
    kind: Literal["judged"] = "judged"


Judgement = Unjudged | Judged


@dataclass(frozen=True)
class Unreviewed:
    kind: Literal["unreviewed"] = "unreviewed"


@dataclass(frozen=True)
class HeldForHuman:
    kind: Literal["held_for_human"] = "held_for_human"


@dataclass(frozen=True)
class Dismissed:
    kind: Literal["dismissed"] = "dismissed"


@dataclass(frozen=True)
class QueuedForSequence:
    kind: Literal["queued_for_sequence"] = "queued_for_sequence"


@dataclass(frozen=True)
class HandedToCloser:
    kind: Literal["handed_to_closer"] = "handed_to_closer"


Disposition = Unreviewed | HeldForHuman | Dismissed | QueuedForSequence | HandedToCloser


def decode_disposition(kind: str) -> Disposition:
    mapping: dict[str, Disposition] = {
        "unreviewed": Unreviewed(),
        "held_for_human": HeldForHuman(),
        "dismissed": Dismissed(),
        "queued_for_sequence": QueuedForSequence(),
        "handed_to_closer": HandedToCloser(),
    }
    if kind not in mapping:
        raise ValueError(f"disposition.kind={kind!r}")
    return mapping[kind]


@dataclass(frozen=True)
class NoWrite:
    kind: Literal["no_write"] = "no_write"


@dataclass(frozen=True)
class Pending:
    kind: Literal["pending"] = "pending"


@dataclass(frozen=True)
class Delivered:
    remote_id: str
    kind: Literal["delivered"] = "delivered"

    def __post_init__(self) -> None:
        if not self.remote_id.strip():
            raise ValueError("relay.remote_id")


@dataclass(frozen=True)
class Failed:
    reason: str
    kind: Literal["failed"] = "failed"

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("relay.reason")


Relay = NoWrite | Pending | Delivered | Failed


def decode_relay(kind: str, remote_id: str | None, reason: str | None) -> Relay:
    if kind == "no_write":
        return NoWrite()
    if kind == "pending":
        return Pending()
    if kind == "delivered":
        if not remote_id:
            raise ValueError("relay.remote_id")
        return Delivered(remote_id)
    if kind == "failed":
        if not reason:
            raise ValueError("relay.reason")
        return Failed(reason)
    raise ValueError(f"relay.kind={kind!r}")


# --- channel / offer / draft / outbound (sequencer slot) ----------------------

FOUNDER_SLOTS: tuple[str, ...] = ("Tuesday 11:00 CET", "Thursday 15:00 CET")


@dataclass(frozen=True)
class Email:
    kind: Literal["email"] = "email"


@dataclass(frozen=True)
class LinkedIn:
    kind: Literal["linkedin"] = "linkedin"


@dataclass(frozen=True)
class Voice:
    kind: Literal["voice"] = "voice"


@dataclass(frozen=True)
class Sms:
    kind: Literal["sms"] = "sms"


@dataclass(frozen=True)
class RinglessVoicemail:
    kind: Literal["ringless_voicemail"] = "ringless_voicemail"


Channel = Email | LinkedIn | Voice | Sms | RinglessVoicemail


def decode_channel(kind: str) -> Channel:
    if kind == "email":
        return Email()
    if kind == "linkedin":
        return LinkedIn()
    if kind == "voice":
        return Voice()
    if kind == "sms":
        return Sms()
    if kind == "ringless_voicemail":
        return RinglessVoicemail()
    raise ValueError(f"channel.kind={kind!r}")


@dataclass(frozen=True)
class Copy:
    text: str
    kind: Literal["copy"] = "copy"


@dataclass(frozen=True)
class CaseStudy:
    url: str
    kind: Literal["case_study"] = "case_study"


@dataclass(frozen=True)
class QualifyingQuestion:
    text: str
    kind: Literal["qualifying_question"] = "qualifying_question"


@dataclass(frozen=True)
class Calendar:
    slots: tuple[str, ...]
    kind: Literal["calendar"] = "calendar"


@dataclass(frozen=True)
class Form:
    url: str
    kind: Literal["form"] = "form"


@dataclass(frozen=True)
class DeclineDraft:
    text: str
    kind: Literal["decline_draft"] = "decline_draft"


Offer = Copy | CaseStudy | QualifyingQuestion | Calendar | Form | DeclineDraft


def decode_offer(body: dict[str, Any] | None) -> Offer:
    """One constructor that can fail. Missing required field names field / entity."""
    if not isinstance(body, dict):
        raise ValueError("draft.offer")
    kind = str(body.get("kind") or "")
    if kind == "copy":
        if "text" not in body:
            raise ValueError("draft.offer.text")
        return Copy(str(body["text"]))
    if kind == "qualifying_question":
        if "text" not in body:
            raise ValueError("draft.offer.text")
        return QualifyingQuestion(str(body["text"]))
    if kind == "decline_draft":
        if "text" not in body:
            raise ValueError("draft.offer.text")
        return DeclineDraft(str(body["text"]))
    if kind == "case_study":
        if "url" not in body:
            raise ValueError("draft.offer.url")
        return CaseStudy(str(body["url"]))
    if kind == "form":
        if "url" not in body:
            raise ValueError("draft.offer.url")
        return Form(str(body["url"]))
    if kind == "calendar":
        if "slots" not in body:
            raise ValueError("draft.offer.slots")
        slots = body["slots"]
        if not isinstance(slots, (list, tuple)):
            raise ValueError("draft.offer.slots")
        return Calendar(tuple(str(s) for s in slots))
    raise ValueError(f"draft.offer.kind={kind!r}")


def encode_offer(offer: Offer) -> dict[str, Any]:
    if isinstance(offer, Copy):
        return {"kind": "copy", "text": offer.text}
    if isinstance(offer, QualifyingQuestion):
        return {"kind": "qualifying_question", "text": offer.text}
    if isinstance(offer, DeclineDraft):
        return {"kind": "decline_draft", "text": offer.text}
    if isinstance(offer, CaseStudy):
        return {"kind": "case_study", "url": offer.url}
    if isinstance(offer, Form):
        return {"kind": "form", "url": offer.url}
    if isinstance(offer, Calendar):
        return {"kind": "calendar", "slots": list(offer.slots)}
    return assert_never(offer)


def empty_offer(offer: Offer) -> bool:
    """Port of `emptyOffer`. Exhaustive — a new arm is a type error here."""
    if isinstance(offer, (Copy, QualifyingQuestion, DeclineDraft)):
        return _blank(offer.text)
    if isinstance(offer, (CaseStudy, Form)):
        return _blank(offer.url)
    if isinstance(offer, Calendar):
        return len(offer.slots) == 0
    return assert_never(offer)


def decline_not_sent(offer: Offer) -> bool:
    """Port of `declineNotSent`. Blank DeclineDraft is EmptyDraft, not this."""
    if isinstance(offer, DeclineDraft):
        return not _blank(offer.text)
    if isinstance(offer, (Copy, CaseStudy, QualifyingQuestion, Calendar, Form)):
        return False
    return assert_never(offer)


@dataclass(frozen=True)
class Draft:
    """Channel plus Offer. Empty offer is `empty_draft` at decide."""

    channel: Channel
    offer: Offer


def empty_draft(draft: Draft) -> bool:
    return empty_offer(draft.offer)


def decode_draft(body: dict[str, Any] | None) -> Draft:
    if not body:
        raise ValueError("draft")
    return Draft(decode_channel(str(body["channel"])), decode_offer(body.get("offer")))


def encode_draft(draft: Draft) -> dict[str, Any]:
    return {"channel": draft.channel.kind, "offer": encode_offer(draft.offer)}


@dataclass(frozen=True)
class NoSend:
    kind: Literal["no_send"] = "no_send"


@dataclass(frozen=True)
class Awaiting:
    """Port of F# `Outbound.Pending`. Named so it does not collide with HubSpot `Pending`."""

    draft: Draft
    kind: Literal["pending"] = "pending"


@dataclass(frozen=True)
class Dispatched:
    remote_id: str
    kind: Literal["dispatched"] = "dispatched"

    def __post_init__(self) -> None:
        if not self.remote_id.strip():
            raise ValueError("outbound.remote_id")


@dataclass(frozen=True)
class SendFailed:
    reason: str
    kind: Literal["failed"] = "failed"

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("outbound.reason")


Outbound = NoSend | Awaiting | Dispatched | SendFailed


def decode_outbound(
    kind: str,
    channel: str | None,
    offer_kind: str | None,
    offer_json: str | None,
    remote_id: str | None,
    reason: str | None,
) -> Outbound:
    if kind == "no_send" or not kind:
        return NoSend()
    if kind == "pending":
        if not channel:
            raise ValueError("outbound.channel")
        if not offer_json:
            raise ValueError("outbound.offer")
        payload = json.loads(offer_json) if isinstance(offer_json, str) else offer_json
        if not isinstance(payload, dict):
            raise ValueError("outbound.offer")
        if offer_kind and payload.get("kind") != offer_kind:
            raise ValueError("outbound.offer.kind")
        return Awaiting(Draft(decode_channel(channel), decode_offer(payload)))
    if kind == "dispatched":
        if not remote_id:
            raise ValueError("outbound.remote_id")
        return Dispatched(remote_id)
    if kind == "failed":
        if not reason:
            raise ValueError("outbound.reason")
        return SendFailed(reason)
    raise ValueError(f"outbound.kind={kind!r}")


COPY_ACTIONS = frozenset({"send_case_study_agency", "send_case_study_coach"})
QUESTION_ACTIONS = frozenset({"ask_qualifying_question_size", "ask_qualifying_question_pain"})


def channel_for_action(action_id: str) -> Channel | None:
    """Host map: playbook id → Channel. Nurture / decline / existing have none.

    Sms / RinglessVoicemail / LinkedIn arms exist so a future playbook row does
    not fall through to Email. 🔴 UNENFORCED in production: `data/playbook.json`
    has no such ids. Tests construct those drafts directly.
    """
    if action_id == "book_call":
        return Voice()
    if action_id in COPY_ACTIONS or action_id in QUESTION_ACTIONS:
        return Email()
    if action_id == "linkedin":
        return LinkedIn()
    if action_id == "sms":
        return Sms()
    if action_id == "ringless_voicemail":
        return RinglessVoicemail()
    return None


def _action_text(action: dict[str, Any]) -> str:
    return str(action.get("text") or action.get("label") or "queued")


def offer_for_action(action: dict[str, Any]) -> Offer:
    """Playbook strings → Offer. No URLs. ⛔ Do not invent CaseStudy / Form urls.

    TEACHING NOTE: CaseStudy, Form, DeclineDraft, Sms, RinglessVoicemail are
    unrepresentable from `pick_action`. Tests construct them. 🔴 UNENFORCED in
    production until a later ticket names a playbook row or a URL source.
    """
    aid = str(action.get("id") or "")
    text = _action_text(action)
    if aid in QUESTION_ACTIONS:
        return QualifyingQuestion(text)
    return Copy(text)


def draft_from_result(result: dict[str, Any] | None) -> Draft:
    """Fill a Draft from `assemble`'s next_action. Does not send."""
    action = (result or {}).get("next_action") or {}
    ch = channel_for_action(str(action.get("id") or ""))
    return Draft(ch or Email(), offer_for_action(action))


def draft_for_queue(result: dict[str, Any] | None) -> Draft:
    """Queue authorizes the sequencer. Voice (book_call) becomes Email + Copy of the CET sentence."""
    action = (result or {}).get("next_action") or {}
    d = draft_from_result(result)
    if isinstance(d.channel, Voice):
        return Draft(Email(), Copy(_action_text(action)))
    return d


def draft_for_handoff(result: dict[str, Any] | None) -> Draft:
    """HandOff authorizes Voice + Calendar of the founder slots, plus HubSpot relay.

    Slots come from `next_action.slots` when present; otherwise the CET pair the
    oracle names. Playbook.json has no slots key and no URLs.
    """
    action = (result or {}).get("next_action") or {}
    raw = action.get("slots")
    if isinstance(raw, (list, tuple)) and raw:
        slots = tuple(str(s) for s in raw)
    else:
        slots = FOUNDER_SLOTS
    return Draft(Voice(), Calendar(slots))


def email_draft(text: str = "Hi — case study") -> Draft:
    return Draft(Email(), Copy(text))


def calendar_draft(slots: tuple[str, ...] | None = None) -> Draft:
    return Draft(Voice(), Calendar(FOUNDER_SLOTS if slots is None else slots))


def voice_draft(slots: tuple[str, ...] | None = None) -> Draft:
    return calendar_draft(slots)


def question_draft(text: str = "roughly how many clients do you serve today?") -> Draft:
    return Draft(Email(), QualifyingQuestion(text))


def decline_draft(text: str = "not a fit") -> Draft:
    return Draft(Email(), DeclineDraft(text))


# --- contact (derived) --------------------------------------------------------


@dataclass(frozen=True)
class Hidden:
    kind: Literal["hidden"] = "hidden"


@dataclass(frozen=True)
class Revealed:
    kind: Literal["revealed"] = "revealed"


Contact = Hidden | Revealed


# --- commands / events / refusals ---------------------------------------------


@dataclass(frozen=True)
class Arrive:
    arrival: Arrival
    kind: Literal["arrive"] = "arrive"


@dataclass(frozen=True)
class Flag:
    kind: Literal["flag"] = "flag"


@dataclass(frozen=True)
class Dismiss:
    kind: Literal["dismiss"] = "dismiss"


@dataclass(frozen=True)
class Queue:
    draft: Draft
    kind: Literal["queue"] = "queue"


@dataclass(frozen=True)
class HandOff:
    draft: Draft
    kind: Literal["hand_off"] = "hand_off"


@dataclass(frozen=True)
class RecordReply:
    body: str
    kind: Literal["record_reply"] = "record_reply"


@dataclass(frozen=True)
class MarkDelivered:
    remote_id: str
    kind: Literal["mark_delivered"] = "mark_delivered"


@dataclass(frozen=True)
class MarkFailed:
    reason: str
    kind: Literal["mark_failed"] = "mark_failed"


@dataclass(frozen=True)
class MarkDispatched:
    remote_id: str
    kind: Literal["mark_dispatched"] = "mark_dispatched"


@dataclass(frozen=True)
class MarkDispatchFailed:
    reason: str
    kind: Literal["mark_dispatch_failed"] = "mark_dispatch_failed"


Command = (
    Arrive
    | Flag
    | Dismiss
    | Queue
    | HandOff
    | RecordReply
    | MarkDelivered
    | MarkFailed
    | MarkDispatched
    | MarkDispatchFailed
)


@dataclass(frozen=True)
class Arrived:
    arrival: Arrival
    kind: Literal["arrived"] = "arrived"


@dataclass(frozen=True)
class Flagged:
    kind: Literal["flagged"] = "flagged"


@dataclass(frozen=True)
class PersonDismissed:
    kind: Literal["person_dismissed"] = "person_dismissed"


@dataclass(frozen=True)
class Queued:
    kind: Literal["queued"] = "queued"


@dataclass(frozen=True)
class HandedOff:
    kind: Literal["handed_off"] = "handed_off"


@dataclass(frozen=True)
class ReplyArrived:
    body: str
    kind: Literal["reply_arrived"] = "reply_arrived"


@dataclass(frozen=True)
class RelayPending:
    kind: Literal["relay_pending"] = "relay_pending"


@dataclass(frozen=True)
class RelayDelivered:
    remote_id: str
    kind: Literal["relay_delivered"] = "relay_delivered"


@dataclass(frozen=True)
class RelayFailed:
    reason: str
    kind: Literal["relay_failed"] = "relay_failed"


@dataclass(frozen=True)
class OutboundPending:
    draft: Draft
    kind: Literal["outbound_pending"] = "outbound_pending"


@dataclass(frozen=True)
class OutboundDispatched:
    remote_id: str
    kind: Literal["outbound_dispatched"] = "outbound_dispatched"


@dataclass(frozen=True)
class OutboundFailed:
    reason: str
    kind: Literal["outbound_failed"] = "outbound_failed"


Event = (
    Arrived
    | Flagged
    | PersonDismissed
    | Queued
    | HandedOff
    | ReplyArrived
    | RelayPending
    | RelayDelivered
    | RelayFailed
    | OutboundPending
    | OutboundDispatched
    | OutboundFailed
)

RefusalKind = Literal[
    "not_arrived",
    "already_arrived",
    "not_judged",
    "not_held",
    "not_hot",
    "not_sequenceable",
    "not_queueable",
    "already_dismissed",
    "not_dismissable",
    "already_handed_off",
    "not_handoffable",
    "relay_not_pending",
    "empty_reply",
    "empty_draft",
    "not_sendable",
    "outbound_not_pending",
]


@dataclass(frozen=True)
class Refusal:
    kind: RefusalKind


@dataclass(frozen=True)
class Err:
    error: Refusal
    kind: Literal["error"] = "error"


@dataclass(frozen=True)
class EventsOk:
    events: tuple[Event, ...]
    kind: Literal["ok"] = "ok"


@dataclass(frozen=True)
class StateOk:
    state: "State"
    kind: Literal["ok"] = "ok"


@dataclass(frozen=True)
class ApplyOk:
    state: "State"
    events: tuple[Event, ...]
    kind: Literal["ok"] = "ok"


# --- state --------------------------------------------------------------------


@dataclass(frozen=True)
class Nothing:
    kind: Literal["nothing"] = "nothing"


@dataclass(frozen=True)
class Open:
    arrival: Arrival
    disposition: Disposition
    relay: Relay
    outbound: Outbound
    kind: Literal["open"] = "open"


State = Nothing | Open


# --- SearchFilters (wave 3; oracle SF1–SF3) -----------------------------------


@dataclass(frozen=True)
class SearchFilters:
    """People Search input. Empty lists mean "do not send that filter".

    TEACHING NOTE: this is a record, not a union. Titles come from the live
    ICP's personas; we do not invent Apollo industry ids (ts-008).
    """

    titles: tuple[str, ...]
    locations: tuple[str, ...]
    employee_ranges: tuple[str, ...]
    keywords: tuple[str, ...]


def filters_from_icp(persona_titles: list[str], geography: str) -> SearchFilters:
    loc: tuple[str, ...] = () if geography.strip().lower() == "anywhere" else (geography.strip(),)
    return SearchFilters(
        titles=tuple(t for t in persona_titles if t.strip()),
        locations=loc,
        employee_ranges=(),
        keywords=(),
    )


# --- decide / evolve / fold / apply / contactOf -------------------------------


def _ok(*events: Event) -> EventsOk:
    return EventsOk(events=events)


def _err(kind: RefusalKind) -> Err:
    return Err(error=Refusal(kind))


def decide(cmd: Command, state: State, judgement: Judgement) -> EventsOk | Err:
    """Port of `decide` in `workitem.fsx`. Case for case."""
    if isinstance(cmd, Arrive):
        if isinstance(state, Nothing):
            return _ok(Arrived(cmd.arrival))
        return _err("already_arrived")

    if isinstance(cmd, Flag):
        if isinstance(state, Nothing):
            return _err("not_arrived")
        if isinstance(state.disposition, Unreviewed):
            if isinstance(judgement, Unjudged):
                return _err("not_judged")
            if judgement.needs_review:
                return _ok(Flagged())
            return _err("not_held")
        return _err("not_held")

    if isinstance(cmd, Dismiss):
        if isinstance(state, Nothing):
            return _err("not_arrived")
        if isinstance(state.disposition, (Unreviewed, HeldForHuman)):
            return _ok(PersonDismissed())
        if isinstance(state.disposition, Dismissed):
            return _err("already_dismissed")
        return _err("not_dismissable")

    if isinstance(cmd, Queue):
        if isinstance(state, Nothing):
            return _err("not_arrived")
        if isinstance(state.disposition, (Unreviewed, HeldForHuman)):
            if isinstance(judgement, Unjudged):
                return _err("not_judged")
            if judgement.tier in ("disqualify", "existing"):
                return _err("not_sequenceable")
            if judgement.tier == "nurture":
                return _ok(Queued())
            if empty_draft(cmd.draft):
                return _err("empty_draft")
            if decline_not_sent(cmd.draft.offer):
                return _err("not_sendable")
            return _ok(Queued(), OutboundPending(cmd.draft))
        return _err("not_queueable")

    if isinstance(cmd, HandOff):
        if isinstance(state, Nothing):
            return _err("not_arrived")
        if isinstance(state.disposition, (Unreviewed, HeldForHuman)):
            if isinstance(judgement, Unjudged):
                return _err("not_judged")
            if judgement.tier == "hot":
                if empty_draft(cmd.draft):
                    return _err("empty_draft")
                if decline_not_sent(cmd.draft.offer):
                    return _err("not_sendable")
                return _ok(HandedOff(), RelayPending(), OutboundPending(cmd.draft))
            return _err("not_hot")
        if isinstance(state.disposition, HandedToCloser):
            return _err("already_handed_off")
        return _err("not_handoffable")

    if isinstance(cmd, RecordReply):
        if isinstance(state, Nothing):
            return _err("not_arrived")
        if _blank(cmd.body):
            return _err("empty_reply")
        return _ok(ReplyArrived(cmd.body))

    if isinstance(cmd, MarkDelivered):
        if isinstance(state, Open) and isinstance(state.relay, Pending):
            return _ok(RelayDelivered(cmd.remote_id))
        return _err("relay_not_pending")

    if isinstance(cmd, MarkFailed):
        if isinstance(state, Open) and isinstance(state.relay, Pending):
            return _ok(RelayFailed(cmd.reason))
        return _err("relay_not_pending")

    if isinstance(cmd, MarkDispatched):
        if isinstance(state, Open) and isinstance(state.outbound, Awaiting):
            return _ok(OutboundDispatched(cmd.remote_id))
        return _err("outbound_not_pending")

    if isinstance(cmd, MarkDispatchFailed):
        if isinstance(state, Open) and isinstance(state.outbound, Awaiting):
            return _ok(OutboundFailed(cmd.reason))
        return _err("outbound_not_pending")

    return assert_never(cmd)


def evolve(state: State, event: Event) -> StateOk | Err:
    """Port of `evolve`. Fold may refuse (Arrived on Open → not_arrived)."""
    if isinstance(state, Nothing) and isinstance(event, Arrived):
        return StateOk(Open(event.arrival, Unreviewed(), NoWrite(), NoSend()))
    if isinstance(state, Open):
        a, d, r, o = state.arrival, state.disposition, state.relay, state.outbound
        if isinstance(event, Flagged):
            return StateOk(Open(a, HeldForHuman(), r, o))
        if isinstance(event, PersonDismissed):
            return StateOk(Open(a, Dismissed(), r, o))
        if isinstance(event, Queued):
            return StateOk(Open(a, QueuedForSequence(), r, o))
        if isinstance(event, HandedOff):
            return StateOk(Open(a, HandedToCloser(), r, o))
        if isinstance(event, ReplyArrived):
            return StateOk(Open(a, Unreviewed(), r, o))
        if isinstance(event, RelayPending):
            return StateOk(Open(a, d, Pending(), o))
        if isinstance(event, RelayDelivered) and isinstance(r, Pending):
            return StateOk(Open(a, d, Delivered(event.remote_id), o))
        if isinstance(event, RelayFailed) and isinstance(r, Pending):
            return StateOk(Open(a, d, Failed(event.reason), o))
        if isinstance(event, OutboundPending):
            return StateOk(Open(a, d, r, Awaiting(event.draft)))
        if isinstance(event, OutboundDispatched) and isinstance(o, Awaiting):
            return StateOk(Open(a, d, r, Dispatched(event.remote_id)))
        if isinstance(event, OutboundFailed) and isinstance(o, Awaiting):
            return StateOk(Open(a, d, r, SendFailed(event.reason)))
    return _err("not_arrived")


def fold(state: State, events: list[Event] | tuple[Event, ...]) -> StateOk | Err:
    current = state
    for event in events:
        stepped = evolve(current, event)
        if isinstance(stepped, Err):
            return stepped
        current = stepped.state
    return StateOk(current)


def apply(cmd: Command, state: State, judgement: Judgement) -> ApplyOk | Err:
    decided = decide(cmd, state, judgement)
    if isinstance(decided, Err):
        return decided
    folded = fold(state, decided.events)
    if isinstance(folded, Err):
        return folded
    return ApplyOk(state=folded.state, events=decided.events)


def contact_of(state: State) -> Contact:
    """Port of `contactOf`. Unreviewed and Dismissed omit the address."""
    if isinstance(state, Open) and isinstance(state.disposition, (HeldForHuman, QueuedForSequence, HandedToCloser)):
        return Revealed()
    return Hidden()


def contact_json(state: State, address: str | None) -> dict[str, str]:
    """Wire shape: hidden | revealed. Address only when Revealed and present."""
    if isinstance(contact_of(state), Revealed) and address and address.strip():
        return {"kind": "revealed", "address": address.strip()}
    return {"kind": "hidden"}


def outbound_json(state: State) -> dict[str, Any]:
    """Wire shape for the sequencer slot. Never includes HubSpot relay."""
    if not isinstance(state, Open):
        return {"kind": "no_send"}
    o = state.outbound
    if isinstance(o, NoSend):
        return {"kind": "no_send"}
    if isinstance(o, Awaiting):
        return {"kind": "pending", "draft": encode_draft(o.draft)}
    if isinstance(o, Dispatched):
        return {"kind": "dispatched", "remote_id": o.remote_id}
    if isinstance(o, SendFailed):
        return {"kind": "failed", "reason": o.reason}
    return assert_never(o)


def judgement_from_result(version_id: str, result: dict) -> Judgement:
    return Judged(
        IcpVersionId(version_id),
        decode_tier(str(result["tier"])),
        bool(result.get("confidence", {}).get("needs_review")),
    )


def parse_command(kind: str, body: dict | None = None) -> Command:
    body = body or {}
    if kind == "flag":
        return Flag()
    if kind == "dismiss":
        return Dismiss()
    if kind == "queue":
        return Queue(decode_draft(body.get("draft") if isinstance(body.get("draft"), dict) else None))
    if kind == "hand_off":
        return HandOff(decode_draft(body.get("draft") if isinstance(body.get("draft"), dict) else None))
    if kind == "record_reply":
        return RecordReply(str(body.get("text") or ""))
    if kind == "mark_delivered":
        return MarkDelivered(str(body["remote_id"]))
    if kind == "mark_failed":
        return MarkFailed(str(body["reason"]))
    if kind == "mark_dispatched":
        return MarkDispatched(str(body["remote_id"]))
    if kind == "mark_dispatch_failed":
        return MarkDispatchFailed(str(body["reason"]))
    raise ValueError(f"command.kind={kind!r}")
