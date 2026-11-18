"""Apollo: organisation enrich (optional) and People Search intake.

TEACHING NOTE: People Search is POST `/api/v1/mixed_people/api_search` with
`x-api-key`. That endpoint does not return email or phone — `contactOf` stays
Hidden until a later reveal. We do not invent Apollo industry tag ids (ts-008).
A refused search is keyed on Apollo's `error_details.code` (HTTP status alone
does not say whether the key is dead or the plan forbids the endpoint).
Organisation enrich writes `account_snapshot` on success (ts-014); hashed files
are a short-ttl duplicate, not the only copy. Failures stay uncached.

⭐ ENFORCED BY: `tests/test_intake.py`, `tests/test_account_snapshot.py`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx

from . import config
from .leads import normalise_domain

API = "https://api.apollo.io/api/v1/organizations/enrich"
PEOPLE_SEARCH = "https://api.apollo.io/api/v1/mixed_people/api_search"


def status() -> dict[str, Any]:
    return {"enabled": config.apollo_enabled(), "has_key": config.apollo_api_key() is not None,
            "flag": config.apollo_enabled(), "cached": len(list(config.APOLLO_CACHE_DIR.glob("*.json"))) if config.APOLLO_CACHE_DIR.exists() else 0}


def enrich(domain: str, timeout: float = 8.0) -> dict[str, Any]:
    dom = normalise_domain(domain)
    if not dom:
        return {"ok": False, "reason": "no domain"}
    if not config.apollo_enabled():
        return {"ok": False, "reason": "Apollo enrichment is off (set APOLLO_ENRICH=1 and APOLLO_API_KEY)"}
    config.APOLLO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = config.APOLLO_CACHE_DIR / (hashlib.sha1(dom.encode()).hexdigest()[:16] + ".json")
    if cache_file.exists():
        try:
            return {**json.loads(cache_file.read_text(encoding="utf-8")), "cached": True}
        except ValueError:
            pass
    try:
        r = httpx.get(API, params={"domain": dom}, headers={"x-api-key": config.apollo_api_key() or "", "Cache-Control": "no-cache"}, timeout=timeout)
    except httpx.HTTPError as exc:
        return {"ok": False, "reason": f"connection error: {type(exc).__name__}"}
    if r.status_code >= 400:
        return {"ok": False, "reason": f"Apollo returned HTTP {r.status_code}"}
    org = (r.json() or {}).get("organization") or {}
    if not org:
        out = {"ok": False, "reason": "no organization found for this domain", "domain": dom}
    else:
        out = {"ok": True, "domain": dom, "organization": {
            "name": org.get("name"), "website": org.get("website_url"), "industry": org.get("industry"),
            "employees": org.get("estimated_num_employees"), "founded": org.get("founded_year"), "city": org.get("city"),
            "country": org.get("country"), "linkedin": org.get("linkedin_url"), "description": (org.get("short_description") or "")[:600],
            "keywords": (org.get("keywords") or [])[:12], "revenue": org.get("annual_revenue_printed")}}
    if out["ok"]:  # failures are not cached so a later retry can succeed
        cache_file.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        from .ledger import get_ledger

        get_ledger().put_account_snapshot(dom, out)
        out = {**out, **(get_ledger().get_account_snapshot(dom) or {})}
    return out


def search_people(filters: dict[str, Any], page: int = 1, per_page: int = 25, timeout: float = 12.0) -> dict[str, Any]:
    """Read-only People Search. Email is not on the hit (Apollo's documented contract)."""
    if not config.apollo_api_key():
        return {"ok": False, "reason": "APOLLO_API_KEY is not set", "people": []}
    body: dict[str, Any] = {"page": page, "per_page": per_page}
    if filters.get("titles"):
        body["person_titles"] = list(filters["titles"])
    if filters.get("locations"):
        body["person_locations"] = list(filters["locations"])
    if filters.get("employee_ranges"):
        body["organization_num_employees_ranges"] = list(filters["employee_ranges"])
    if filters.get("keywords"):
        body["q_keywords"] = " ".join(filters["keywords"]) if isinstance(filters["keywords"], list) else filters["keywords"]
    try:
        r = httpx.post(
            PEOPLE_SEARCH,
            json=body,
            headers={"x-api-key": config.apollo_api_key() or "", "Content-Type": "application/json", "Cache-Control": "no-cache"},
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        return {"ok": False, "reason": f"connection error: {type(exc).__name__}", "people": []}
    if r.status_code >= 400:
        code = None
        try:
            payload = r.json() or {}
            details = payload.get("error_details") if isinstance(payload, dict) else None
            if isinstance(details, dict):
                code = details.get("code")
        except ValueError:
            pass
        reason = f"Apollo {code} (HTTP {r.status_code})" if code else f"Apollo returned HTTP {r.status_code}"
        return {"ok": False, "reason": reason, "people": [], "status": r.status_code}
    data = r.json() or {}
    people = data.get("people") or data.get("contacts") or []
    return {"ok": True, "people": people, "pagination": data.get("pagination") or {}, "status": r.status_code}
