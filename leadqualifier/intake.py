"""CSV Arrive and People Search Arrive. One door: `Arrive` on the work-item aggregate.

TEACHING NOTE: a CSV row is `CsvRow (importId, row)`, never a third Arrival case.
The same import id + row → `already_arrived`. Column names map onto the Lead
payload (name, domain, title, message). Apollo is not called from CSV.

⭐ ENFORCED BY: `tests/test_intake.py`.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any
from uuid import uuid4

from .leads import lead_from_payload
from .workitem import (
    ApolloPerson,
    Arrive,
    CsvRow,
    ImportId,
    PersonId,
    Unjudged,
)


ALIASES = {
    "name": ("name", "full_name", "full name", "person", "contact", "first_name"),
    "title": ("title", "job_title", "job title", "role"),
    "domain": ("domain", "company_domain", "website", "company website"),
    "company": ("company", "company_name", "company name", "account", "organization"),
    "message": ("message", "body", "text", "note", "snippet"),
    "email": ("email", "e-mail", "e_mail"),
    "phone": ("phone", "mobile", "tel"),
}


def _cell(row: dict[str, str], *keys: str) -> str | None:
    lower = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
    for key in keys:
        if lower.get(key):
            return lower[key]
    return None


def parse_csv(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    return [dict(r) for r in reader]


def row_payload(raw: dict[str, str], work_item_id: str, import_id: str, row: int) -> dict[str, Any]:
    name = _cell(raw, *ALIASES["name"])
    title = _cell(raw, *ALIASES["title"])
    domain = _cell(raw, *ALIASES["domain"])
    company = _cell(raw, *ALIASES["company"])
    message = _cell(raw, *ALIASES["message"])
    email = _cell(raw, *ALIASES["email"])
    phone = _cell(raw, *ALIASES["phone"])
    person = {k: v for k, v in (("name", name), ("title", title), ("email", email), ("phone", phone)) if v}
    company_d = {k: v for k, v in (("name", company), ("domain", domain)) if v}
    return {
        "id": work_item_id,
        "source": "csv_import",
        "received_at": "",
        "person": person or None,
        "company": company_d or None,
        "message": {"text": message} if message else None,
        "tags": [f"import:{import_id}"],
        "import_id": import_id,
        "import_row": row,
    }


def arrive_csv(ledger, text: str, import_id: str | None = None) -> dict[str, Any]:
    iid = import_id or uuid4().hex[:12]
    rows = parse_csv(text)
    inserted: list[str] = []
    skipped: list[dict[str, str]] = []
    for i, raw in enumerate(rows, start=1):
        arrival = CsvRow(ImportId(iid), i)
        existing = ledger.find_by_arrival(arrival)
        if existing is not None:
            skipped.append({"id": existing, "reason": "already_arrived", "row": i})
            continue
        wid = f"csv-{iid}-{i:04d}"
        payload = row_payload(raw, wid, iid, i)
        result = ledger.apply_command(wid, Arrive(arrival), Unjudged(), payload=payload)
        if getattr(result, "kind", None) == "error":
            skipped.append({"id": wid, "reason": result.error.kind, "row": i})
            continue
        inserted.append(wid)
    return {"import_id": iid, "inserted": inserted, "skipped": skipped, "rows": len(rows)}


def person_payload(hit: dict[str, Any], work_item_id: str) -> dict[str, Any]:
    """Email stays off this JSON until wave 4 `contactOf` (ts-007)."""
    org = hit.get("organization") or {}
    first = hit.get("first_name") or ""
    last = hit.get("last_name") or ""
    name = (hit.get("name") or f"{first} {last}").strip()
    return {
        "id": work_item_id,
        "source": "apollo_export",
        "received_at": "",
        "person": {
            "name": name or None,
            "title": hit.get("title"),
            "company": org.get("name"),
            # email deliberately omitted
        },
        "company": {
            "name": org.get("name"),
            "domain": org.get("primary_domain") or org.get("website_url"),
            "location": ", ".join(p for p in (org.get("city"), org.get("country")) if p) or None,
        },
        "message": None,
        "tags": ["apollo_people_search"],
        "apollo_person_id": hit.get("id"),
    }


def arrive_apollo_people(ledger, hits: list[dict[str, Any]]) -> dict[str, Any]:
    inserted: list[str] = []
    skipped: list[dict[str, str]] = []
    for hit in hits:
        pid = str(hit.get("id") or "").strip()
        if not pid:
            skipped.append({"id": "", "reason": "missing_person_id"})
            continue
        arrival = ApolloPerson(PersonId(pid))
        existing = ledger.find_by_arrival(arrival)
        if existing is not None:
            skipped.append({"id": existing, "reason": "already_arrived", "person_id": pid})
            continue
        wid = f"ap-{pid}"
        payload = person_payload(hit, wid)
        result = ledger.apply_command(wid, Arrive(arrival), Unjudged(), payload=payload)
        if getattr(result, "kind", None) == "error":
            skipped.append({"id": wid, "reason": result.error.kind, "person_id": pid})
            continue
        inserted.append(wid)
    return {"inserted": inserted, "skipped": skipped}


def geography_for_search(geo: str) -> str:
    """Apollo wants a place name. A sentence in `icp.geography` is not one.

    TEACHING NOTE: we do not invent Apollo location ids, and we do not send
    marketing copy as `person_locations`. Short names (`Hamburg`) pass through;
    `anywhere` and prose become an empty location filter.
    """
    g = (geo or "").strip()
    if not g or g.lower() == "anywhere":
        return "anywhere"
    if len(g) > 48 or any(ch in g for ch in ";.\n") or g.count(",") >= 2:
        return "anywhere"
    return g


def filters_payload(icp: dict[str, Any]) -> dict[str, Any]:
    from .workitem import filters_from_icp

    titles = []
    for pid, v in icp.get("personas", {}).items():
        if isinstance(v, dict) and str(v.get("title") or "").strip():
            titles.append(str(v["title"]).strip())
        else:
            titles.append(pid.replace("_", " "))
    f = filters_from_icp(titles, geography_for_search(str(icp.get("geography") or "anywhere")))
    return {
        "titles": list(f.titles),
        "locations": list(f.locations),
        "employee_ranges": list(f.employee_ranges),
        "keywords": list(f.keywords),
    }


def lead_from_row(row: dict[str, Any]):
    return lead_from_payload(json.loads(row["payload_json"]))
