"""Host parser: Instantly `reply_received` → InboundHint. decide never sees this JSON.

TEACHING NOTE: this file sits beside Instantly, not in `inbound.py`.
`inbound.py` stays vendor-blind (`rg Instantly leadqualifier/inbound.py` is 0).
Other Instantly event types are Ignore (HTTP 204), not `unknown_sender`.
Empty `reply_text` still becomes a hint; `RecordReply` then refuses `empty_reply`.

⭐ ENFORCED BY: `tests/test_inbound.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .inbound import ByEmail


@dataclass(frozen=True)
class ParsedReply:
    hint: ByEmail
    body: str
    kind: Literal["parsed"] = "parsed"


@dataclass(frozen=True)
class Ignore:
    kind: Literal["ignore"] = "ignore"


def parse_instantly_inbound(payload: dict[str, Any]) -> ParsedReply | Ignore:
    """Map Instantly webhook JSON to a vendor-blind hint. Not a Command."""
    if str(payload.get("event_type") or "") != "reply_received":
        return Ignore()
    email = str(payload.get("lead_email") or "")
    text = str(payload.get("reply_text") or "")
    return ParsedReply(ByEmail(email), text)
