"""ts-014 organisation snapshot stores fetched_at on the account row.

TEACHING NOTE: `fetched_at` lives on the sqlite account row, not only the hashed
JSON file. The HTTP client is faked; failures must not be stored (not asserted here
because this file covers the success write).
"""

from __future__ import annotations

from leadqualifier import apollo, config
from leadqualifier.ledger import get_ledger


class _Resp:
    status_code = 200

    def json(self):
        return {
            "organization": {
                "name": "Example",
                "website_url": "https://example.com",
                "industry": "software",
                "estimated_num_employees": 40,
                "city": "Berlin",
                "country": "Germany",
                "short_description": "Example co",
                "keywords": ["saas"],
            }
        }


def test_enrich_writes_fetched_at(monkeypatch):
    monkeypatch.setenv("APOLLO_ENRICH", "1")
    monkeypatch.setenv("APOLLO_API_KEY", "test-key-not-real")
    monkeypatch.setattr(apollo.httpx, "get", lambda *a, **k: _Resp())
    out = apollo.enrich("https://www.Example.com/path")
    assert out["ok"] is True
    snap = get_ledger().get_account_snapshot("example.com")
    assert snap is not None and snap.get("fetched_at")
    assert snap["ok"] is True
