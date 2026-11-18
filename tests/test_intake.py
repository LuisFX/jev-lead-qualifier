"""ts-006 CSV Arrive, ts-007 ApolloPerson Arrive, ts-008 SearchFilters.

TEACHING NOTE: live People Search is not this file. HTTP against Apollo is the
smoke with a key; here the client is faked so Arrive / AlreadyArrived stay cheap.
"""

from __future__ import annotations

from leadqualifier.intake import arrive_apollo_people, arrive_csv, filters_payload
from leadqualifier.ledger import get_ledger
from leadqualifier.workitem import filters_from_icp


CSV3 = """name,domain,title,message
Ada Lovelace,analytical.de,Founder,We are drowning in reports.
Bob Builder,build.de,CMO,Need a better pipeline.
Cara Cox,cox.de,VP Marketing,Can we talk next week?
"""


def test_csv_three_rows_then_already_arrived():
    from leadqualifier.leads import load_leads

    load_leads()
    r = arrive_csv(get_ledger(), CSV3, "batch-1")
    assert r["rows"] == 3 and len(r["inserted"]) == 3
    again = arrive_csv(get_ledger(), CSV3, "batch-1")
    assert again["inserted"] == [] and {s["reason"] for s in again["skipped"]} == {"already_arrived"}
    ids = {row["id"] for row in get_ledger().list_rows()}
    assert set(r["inserted"]) <= ids


def test_csv_maps_email_and_phone():
    r = arrive_csv(
        get_ledger(),
        "name,domain,email,phone,message\nAda,a.de,ada@secret.test,+4940123,Hi\n",
        "phone-1",
    )
    wid = r["inserted"][0]
    payload = __import__("json").loads(get_ledger().get_row(wid)["payload_json"])
    assert payload["person"]["email"] == "ada@secret.test"
    assert payload["person"]["phone"] == "+4940123"


def test_search_filters_from_icp(icp):
    f = filters_payload(icp)
    assert f["titles"]
    assert f["locations"] == []
    assert filters_from_icp(["Founder"], "anywhere").locations == ()
    assert filters_from_icp(["Founder"], "Hamburg").locations == ("Hamburg",)


def test_apollo_person_arrive_idempotent():
    hits = [
        {
            "id": "abc123",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "title": "Founder",
            "email": "ada@secret.test",
            "organization": {"name": "Analytical", "primary_domain": "analytical.de"},
        }
    ]
    first = arrive_apollo_people(get_ledger(), hits)
    assert first["inserted"] == ["ap-abc123"]
    payload = get_ledger().get_row("ap-abc123")["payload_json"]
    assert "ada@secret.test" not in payload
    second = arrive_apollo_people(get_ledger(), hits)
    assert second["inserted"] == [] and second["skipped"][0]["reason"] == "already_arrived"


def test_search_people_surfaces_apollo_error_code(monkeypatch):
    """A 403 from Apollo is keyed on error_details.code, not a silent HTTP number."""

    class _Resp:
        status_code = 403

        def json(self):
            return {"error_details": {"code": "AUTH.AUTHORIZATION.ENDPOINT_ACCESS_DENIED"}}

    monkeypatch.setenv("APOLLO_API_KEY", "test-key-not-real")
    monkeypatch.setattr("leadqualifier.apollo.httpx.post", lambda *a, **k: _Resp())
    from leadqualifier import apollo

    out = apollo.search_people({"titles": ["Founder"]})
    assert out["ok"] is False and out["status"] == 403
    assert "AUTH.AUTHORIZATION.ENDPOINT_ACCESS_DENIED" in out["reason"]


def test_search_endpoint_mocked(monkeypatch):
    from leadqualifier import server
    from fastapi.testclient import TestClient
    from leadqualifier.fake_client import FakeClient

    def fake_search(filters, page=1, per_page=25, timeout=12.0):
        return {
            "ok": True,
            "people": [{"id": "p99", "name": "P Nine", "title": "Founder", "organization": {"name": "N", "primary_domain": "n.de"}}],
            "pagination": {},
        }

    monkeypatch.setattr("leadqualifier.server.apollo.search_people", fake_search)
    server.set_client(FakeClient())
    with TestClient(server.app) as c:
        r = c.post("/api/search", json={"titles": ["Founder"]}).json()
        assert "ap-p99" in r["inserted"] and r["hits"] == 1
        again = c.post("/api/search", json={"titles": ["Founder"]}).json()
        assert again["skipped"][0]["reason"] == "already_arrived"
    server.set_client(None)
