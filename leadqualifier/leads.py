"""Leads, CRM accounts and gold labels on disk; the state Jev sees for one lead.

A lead links a person, a company and optionally a message. Any of the three may be null:
inbound messages often come with only a name, LinkedIn exports have a bio but no message,
Apollo exports have a company profile and nothing else.

Privacy: the state sent to Jev never contains the lead's e-mail address or phone number.
Names, titles, bios, company descriptions and the message text are needed for the
judgements and are sent; contact details are not.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config
from .constants import MAX_SENTENCES

SOURCE_LABELS = {
    "website_form": "Website form",
    "linkedin_dm": "LinkedIn DM",
    "email_reply": "E-mail reply",
    "instantly_reply": "Instantly reply",
    "apollo_export": "Apollo export",
    "linkedin_export": "LinkedIn export",
    "referral": "Referral note",
}


@dataclass
class Lead:
    id: str
    source: str
    received_at: str
    person: dict[str, Any] | None = None
    company: dict[str, Any] | None = None
    message: dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ display helpers
    @property
    def company_name(self) -> str:
        if self.company and self.company.get("name"):
            return self.company["name"]
        if self.person and self.person.get("company"):
            return self.person["company"]
        return "Unknown company"

    @property
    def person_name(self) -> str:
        if self.person and self.person.get("name"):
            return self.person["name"]
        if self.message and self.message.get("from_name"):
            return self.message["from_name"]
        return "Unknown sender"

    @property
    def domain(self) -> str | None:
        for cand in ((self.company or {}).get("domain"), (self.message or {}).get("from_domain"), (self.person or {}).get("domain")):
            if cand:
                return normalise_domain(cand)
        return None

    @property
    def shape(self) -> str:
        """Which of the three input shapes dominates."""
        if self.message and self.message.get("text"):
            return "message"
        if self.person and self.person.get("bio"):
            return "bio"
        return "profile"

    # ------------------------------------------------------------------ text → sentences
    def sentences(self) -> list[dict[str, str]]:
        """Sentences with stable ids: S1.. for the message, N1.. for company news, B1.. for the bio."""
        out: list[dict[str, str]] = []
        if self.message and self.message.get("text"):
            for i, s in enumerate(split_sentences(self.message["text"]), 1):
                out.append({"id": f"S{i}", "text": s, "part": "message"})
        if self.company and self.company.get("news"):
            for i, s in enumerate(split_sentences(self.company["news"]), 1):
                out.append({"id": f"N{i}", "text": s, "part": "news"})
        if self.person and self.person.get("bio"):
            for i, s in enumerate(split_sentences(self.person["bio"]), 1):
                out.append({"id": f"B{i}", "text": s, "part": "bio"})
        return out[:MAX_SENTENCES]

    # ------------------------------------------------------------------ state for Jev
    def to_state(self) -> dict[str, Any]:
        person = None
        if self.person:
            person = {k: self.person.get(k) for k in ("name", "title", "company", "location", "bio") if self.person.get(k) is not None}
        company = None
        if self.company:
            company = {k: self.company.get(k) for k in ("name", "domain", "description", "size", "location", "services", "news", "founded")
                       if self.company.get(k) is not None}
        message = None
        if self.message and self.message.get("text"):
            message = self.message["text"]
            subj = self.message.get("subject")
            if subj:
                message = f"Subject: {subj}\n\n{message}"
        return {
            "lead_source": SOURCE_LABELS.get(self.source, self.source),
            "company": company,
            "person": person,
            "message": message,
            "sentences": {s["id"]: s["text"] for s in self.sentences()} or None,
        }

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "source": self.source, "source_label": SOURCE_LABELS.get(self.source, self.source),
                "received_at": self.received_at, "person": self.person, "company": self.company, "message": self.message,
                "tags": self.tags, "company_name": self.company_name, "person_name": self.person_name, "domain": self.domain,
                "shape": self.shape, "sentences": self.sentences()}


_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9\"'(])|\n{2,}|(?<=[.!?])\n")


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = [p.strip() for p in _SENT_RE.split(text) if p and p.strip()]
    merged: list[str] = []
    for p in parts:
        if merged and len(p) < 12:  # glue fragments like "Thanks!" onto the previous sentence
            merged[-1] = f"{merged[-1]} {p}"
        else:
            merged.append(p)
    return merged


def normalise_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    d = domain.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0]
    if d.startswith("www."):
        d = d[4:]
    return d or None


# --------------------------------------------------------------------------- loading


def load_leads(directory: Path | None = None) -> list[Lead]:
    directory = directory or config.LEADS_DIR
    leads: list[Lead] = []
    for path in sorted(directory.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        items = d if isinstance(d, list) else [d]
        for item in items:
            leads.append(Lead(id=item["id"], source=item.get("source", "website_form"), received_at=item.get("received_at", ""),
                              person=item.get("person"), company=item.get("company"), message=item.get("message"),
                              tags=list(item.get("tags", []))))
    return leads


def load_crm(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or config.CRM_FILE
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("accounts", data) if isinstance(data, dict) else data


def load_gold(path: Path | None = None) -> dict[str, dict[str, Any]]:
    path = path or config.GOLD_FILE
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("leads", data)


def load_playbook(path: Path | None = None) -> dict[str, Any]:
    path = path or config.PLAYBOOK_FILE
    return json.loads(path.read_text(encoding="utf-8"))
