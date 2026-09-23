"""Code shortlists CRM accounts that *might* be the same organisation; Jev decides.

Exact domain match, name similarity (difflib on normalised names) and token overlap put up to
ten candidates in front of the `same_account` Choice. The shortlist is deliberately generous:
a wrong candidate costs a few tokens, a missed one costs a duplicate outreach.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from .constants import MAX_CRM_CANDIDATES
from .leads import Lead, normalise_domain

_STOP = {"gmbh", "ag", "ltd", "limited", "llc", "inc", "co", "kg", "ug", "bv", "b.v.", "the", "and", "&", "studio", "agency",
         "agentur", "group", "digital", "media", "consulting", "partners", "coaching"}


def normalise_name(name: str | None) -> str:
    if not name:
        return ""
    n = name.lower()
    n = re.sub(r"[^a-z0-9äöüß ]+", " ", n)
    return " ".join(t for t in n.split() if t not in _STOP)


def name_tokens(name: str | None) -> set[str]:
    return {t for t in normalise_name(name).split() if len(t) > 2}


def _registrable(domain: str | None) -> str | None:
    d = normalise_domain(domain)
    if not d:
        return None
    parts = d.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else d


def similarity(lead: Lead, account: dict[str, Any]) -> tuple[float, list[str]]:
    """0..1 shortlist score plus the code-level reasons (shown to the human next to Jev's verdict)."""
    reasons: list[str] = []
    score = 0.0
    lead_dom = _registrable(lead.domain)
    acc_dom = _registrable(account.get("domain"))
    if lead_dom and acc_dom and lead_dom == acc_dom:
        score = max(score, 1.0)
        reasons.append(f"same domain {acc_dom}")
    names_lead = [lead.company_name]
    if lead.person and lead.person.get("company"):
        names_lead.append(lead.person["company"])
    for ln in names_lead:
        a, b = normalise_name(ln), normalise_name(account.get("name"))
        if not a or not b:
            continue
        ratio = SequenceMatcher(None, a, b).ratio()
        if ratio >= 0.72:
            score = max(score, 0.55 + 0.45 * ratio)
            reasons.append(f"name similarity {ratio:.2f}")
        toks = name_tokens(ln) & name_tokens(account.get("name"))
        if toks:
            score = max(score, 0.5 + 0.1 * len(toks))
            reasons.append("shared name token " + ", ".join(sorted(toks)))
    for contact in account.get("contacts", []):
        if lead.person and lead.person.get("name") and normalise_name(contact.get("name")) == normalise_name(lead.person["name"]):
            score = max(score, 0.9)
            reasons.append(f"contact {contact['name']} on the account")
    return min(score, 1.0), sorted(set(reasons))


def shortlist(lead: Lead, accounts: list[dict[str, Any]], limit: int = MAX_CRM_CANDIDATES, floor: float = 0.45) -> list[dict[str, Any]]:
    scored = []
    for acc in accounts:
        s, reasons = similarity(lead, acc)
        if s >= floor:
            scored.append({"id": acc["id"], "name": acc["name"], "domain": acc.get("domain"), "about": acc.get("about"),
                           "status": acc.get("status"), "owner": acc.get("owner"), "code_score": round(s, 3), "code_reasons": reasons})
    scored.sort(key=lambda c: -c["code_score"])
    return scored[:limit]
