"""Work-item aggregate: port of `workitem.fsx`. The oracle owns the types.

TEACHING NOTE: think Decider (`decide` / `evolve`), then write Python to match.
`decide` is total: every command against every state is Ok events or a named refusal.
`evolve` is a fold and *can* refuse (Arrived on Open → `not_arrived`). Judgement is
an argument, not a field of State. Contact is derived (`contactOf`): Hidden on
Unreviewed and Dismissed, Revealed after Flag, Queue, or HandOff.

⭐ ENFORCED BY: `leadqualifier/workitem.fsx` (the law floor) and `tests/test_workitem.py`
(the same laws, ported). A host that skips `decide` and writes a column is a defect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Never


def assert_never(x: Never) -> Never:
    raise AssertionError(f"unhandled: {x!r}")


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
    kind: Literal["queue"] = "queue"


@dataclass(frozen=True)
class HandOff:
    kind: Literal["hand_off"] = "hand_off"


@dataclass(frozen=True)
class RecordReply:
    kind: Literal["record_reply"] = "record_reply"


@dataclass(frozen=True)
class MarkDelivered:
    remote_id: str
    kind: Literal["mark_delivered"] = "mark_delivered"


@dataclass(frozen=True)
class MarkFailed:
    reason: str
    kind: Literal["mark_failed"] = "mark_failed"


Command = Arrive | Flag | Dismiss | Queue | HandOff | RecordReply | MarkDelivered | MarkFailed


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
            return _ok(Queued())
        return _err("not_queueable")

    if isinstance(cmd, HandOff):
        if isinstance(state, Nothing):
            return _err("not_arrived")
        if isinstance(state.disposition, (Unreviewed, HeldForHuman)):
            if isinstance(judgement, Unjudged):
                return _err("not_judged")
            if judgement.tier == "hot":
                return _ok(HandedOff(), RelayPending())
            return _err("not_hot")
        if isinstance(state.disposition, HandedToCloser):
            return _err("already_handed_off")
        return _err("not_handoffable")

    if isinstance(cmd, RecordReply):
        if isinstance(state, Nothing):
            return _err("not_arrived")
        return _ok(ReplyArrived())

    if isinstance(cmd, MarkDelivered):
        if isinstance(state, Open) and isinstance(state.relay, Pending):
            return _ok(RelayDelivered(cmd.remote_id))
        return _err("relay_not_pending")

    if isinstance(cmd, MarkFailed):
        if isinstance(state, Open) and isinstance(state.relay, Pending):
            return _ok(RelayFailed(cmd.reason))
        return _err("relay_not_pending")

    return assert_never(cmd)


def evolve(state: State, event: Event) -> StateOk | Err:
    """Port of `evolve`. Fold may refuse (Arrived on Open → not_arrived)."""
    if isinstance(state, Nothing) and isinstance(event, Arrived):
        return StateOk(Open(event.arrival, Unreviewed(), NoWrite()))
    if isinstance(state, Open):
        a, d, r = state.arrival, state.disposition, state.relay
        if isinstance(event, Flagged):
            return StateOk(Open(a, HeldForHuman(), r))
        if isinstance(event, PersonDismissed):
            return StateOk(Open(a, Dismissed(), r))
        if isinstance(event, Queued):
            return StateOk(Open(a, QueuedForSequence(), r))
        if isinstance(event, HandedOff):
            return StateOk(Open(a, HandedToCloser(), r))
        if isinstance(event, ReplyArrived):
            return StateOk(Open(a, Unreviewed(), r))
        if isinstance(event, RelayPending):
            return StateOk(Open(a, d, Pending()))
        if isinstance(event, RelayDelivered) and isinstance(r, Pending):
            return StateOk(Open(a, d, Delivered(event.remote_id)))
        if isinstance(event, RelayFailed) and isinstance(r, Pending):
            return StateOk(Open(a, d, Failed(event.reason)))
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
        return Queue()
    if kind == "hand_off":
        return HandOff()
    if kind == "record_reply":
        return RecordReply()
    if kind == "mark_delivered":
        return MarkDelivered(str(body["remote_id"]))
    if kind == "mark_failed":
        return MarkFailed(str(body["reason"]))
    raise ValueError(f"command.kind={kind!r}")
