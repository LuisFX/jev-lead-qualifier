"""Host matcher: a vendor-blind hint becomes InboundMatch, then RecordReply.

TEACHING NOTE: this is not a vendor webhook type. `decide` does not import it.
A miss or a duplicate identity is `UnknownSender`, not a new Arrival and not a
silent drop. Email uniqueness is not a write invariant — match is the refusal.
🔴 UNENFORCED at Arrive: two CSV rows may share an email.

⭐ ENFORCED BY: `tests/test_inbound.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from .workitem import assert_never


@dataclass(frozen=True)
class ByWorkItem:
    work_item_id: str
    kind: Literal["work_item"] = "work_item"


@dataclass(frozen=True)
class ByEmail:
    email: str
    kind: Literal["email"] = "email"


@dataclass(frozen=True)
class ByPhone:
    phone: str
    kind: Literal["phone"] = "phone"


InboundHint = ByWorkItem | ByEmail | ByPhone


@dataclass(frozen=True)
class Matched:
    work_item_id: str
    kind: Literal["matched"] = "matched"


@dataclass(frozen=True)
class UnknownSender:
    kind: Literal["unknown_sender"] = "unknown_sender"


InboundMatch = Matched | UnknownSender


@dataclass
class Directory:
    by_id: set[str] = field(default_factory=set)
    by_email: dict[str, list[str]] = field(default_factory=dict)
    by_phone: dict[str, list[str]] = field(default_factory=dict)


def _norm_email(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    s = raw.strip().casefold()
    return s or None


def _norm_phone(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    return s or None


def directory_from_rows(rows: list[dict[str, Any]]) -> Directory:
    """Scan payload_json. No email column. One spelling: person.email / person.phone."""
    directory = Directory()
    for row in rows:
        wid = str(row["id"])
        directory.by_id.add(wid)
        payload = json.loads(row["payload_json"])
        person = payload.get("person") if isinstance(payload.get("person"), dict) else {}
        email = _norm_email(person.get("email"))
        phone = _norm_phone(person.get("phone"))
        if email is not None:
            directory.by_email.setdefault(email, []).append(wid)
        if phone is not None:
            directory.by_phone.setdefault(phone, []).append(wid)
    return directory


def _one(ids: list[str]) -> InboundMatch:
    if len(ids) == 1:
        return Matched(ids[0])
    return UnknownSender()


def match_inbound(ledger, hint: InboundHint) -> InboundMatch:
    """Port of `matchInbound` in workitem.fsx. Case for case."""
    if isinstance(hint, ByWorkItem):
        wid = hint.work_item_id.strip()
        if not wid:
            return UnknownSender()
        if ledger.get_row(wid) is None:
            return UnknownSender()
        return Matched(wid)
    directory = directory_from_rows(ledger.list_rows())
    if isinstance(hint, ByEmail):
        key = _norm_email(hint.email)
        if key is None:
            return UnknownSender()
        return _one(directory.by_email.get(key, []))
    if isinstance(hint, ByPhone):
        key = _norm_phone(hint.phone)
        if key is None:
            return UnknownSender()
        return _one(directory.by_phone.get(key, []))
    return assert_never(hint)


def decode_hint(raw: dict[str, Any]) -> InboundHint:
    kind = raw.get("kind")
    if kind == "work_item":
        return ByWorkItem(str(raw.get("id") or ""))
    if kind == "email":
        return ByEmail(str(raw.get("email") or ""))
    if kind == "phone":
        return ByPhone(str(raw.get("phone") or ""))
    raise ValueError(f"hint.kind={kind!r}")
