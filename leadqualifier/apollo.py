"""Optional read-only enrichment via Apollo (organization by domain). Behind APOLLO_ENRICH=1.

Cached on disk per domain; every failure degrades to `{"ok": false, "reason": ...}` so the demo
never depends on it. Nothing from Apollo is written to the dataset; the UI shows it side by side.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx

from . import config
from .leads import normalise_domain

API = "https://api.apollo.io/api/v1/organizations/enrich"


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
    return out
