"""API surface with a fake Jev client injected. Files are isolated by conftest.

TEACHING NOTE: 409 is a named refusal (`detail.refusal`), not a validation error.
Draft POST /api/rescore must not insert an `icp_version` row.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from leadqualifier import server
from leadqualifier.fake_client import FakeClient


@pytest.fixture
def client():
    server.set_client(FakeClient())
    with TestClient(server.app) as c:
        yield c
    server.set_client(None)


def _sse(text: str) -> list[tuple[str, dict]]:
    out = []
    for chunk in text.split("\n\n"):
        kind, data = None, None
        for line in chunk.split("\n"):
            if line.startswith("event:"):
                kind = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:])
        if kind and data is not None:
            out.append((kind, data))
    return out


def test_status_and_leads(client):
    s = client.get("/api/status").json()
    assert s["leads"] == 65 and s["icp"]["id"] == "lanternfield_agencies" and s["jev_key"] and s["has_gold"]
    assert "cache" in s and "apollo" in s
    leads = client.get("/api/leads").json()
    assert len(leads) == 65 and all("sentences" in l for l in leads)
    assert all("email" not in json.dumps(l.get("person") or {}) for l in leads)


def test_index_and_static(client):
    assert client.get("/").status_code == 200 and "First Read" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200


def test_run_stream_then_results_from_cache(client):
    r = client.get("/api/run/stream?ids=L001,L047,L060")
    events = _sse(r.text)
    kinds = [k for k, _ in events]
    assert kinds[0] == "start" and kinds[-1] == "done" and kinds.count("result") == 3
    done = events[-1][1]
    assert done["totals"]["leads"] == 3 and done["totals"]["requests"] == 3
    res = client.get("/api/results").json()
    assert len(res["results"]) == 3 and res["totals"]["from_cache"] == 3
    assert res["stale"]["cached_leads"] == 3  # the other 62 leads would still be asked everything
    detail = client.get("/api/leads/L001").json()
    assert detail["result"]["lead_id"] == "L001" and detail["result"]["meta"]["cached"]
    assert len(detail["questions"]) == detail["result"]["meta"]["n_questions"]


def test_score_one_and_unknown_lead(client):
    r = client.post("/api/score/L001").json()
    assert r["lead_id"] == "L001" and r["meta"]["n_asked"] > 20
    assert r["icp_version_id"]
    assert client.post("/api/score/NOPE").status_code == 404


def test_icp_roundtrip_reports_stale_questions(client):
    client.get("/api/run/stream?ids=L001")
    icp = client.get("/api/icp").json()["icp"]
    icp["pains"]["client_churn"] = {"description": "Clients leave", "weight": 0.8}
    put = client.put("/api/icp", json={"icp": icp}).json()
    assert put["stale"]["questions_to_ask"] > 0
    assert set(put["stale"]["stale_question_ids"]) >= {"pain_client_churn", "evidence_client_churn"}
    # unsaved draft: rescore from cache, zero calls, tiers may move
    draft = put["icp"]
    draft["thresholds"]["fit_hot"] = 0.99
    live = client.post("/api/rescore", json={"icp": draft}).json()
    assert live["totals"]["tiers"]["hot"] == 0 and len(live["results"]) == 1
    bad = dict(draft)
    bad["thresholds"] = dict(draft["thresholds"], fit_warm=0.999)
    assert client.put("/api/icp", json={"icp": bad}).status_code == 422
    reset = client.post("/api/icp/reset").json()
    assert "client_churn" not in reset["icp"]["pains"]


def test_presets_switch_and_gold_only_for_default(client):
    presets = client.get("/api/icp/presets").json()
    assert {p["id"] for p in presets} >= {"b2b_saas_founders", "ecommerce_brands"}
    d = client.post("/api/icp/presets/ecommerce_brands").json()
    assert d["icp"]["id"] == "ecommerce_brands"
    assert client.get("/api/status").json()["has_gold"] is False
    assert client.get("/api/metrics").status_code == 404
    assert client.post("/api/icp/presets/nope").status_code == 404
    client.post("/api/icp/reset")


def test_questions_playbook_crm_and_cache_delete(client):
    q = client.get("/api/questions").json()
    assert q["n"] > 25 and {x["group"] for x in q["questions"]} >= {"fit", "pain", "intent"}
    assert "book_call" in client.get("/api/playbook").json()
    assert len(client.get("/api/crm").json()) == 12
    client.get("/api/run/stream?ids=L001")
    assert client.delete("/api/cache").json()["ok"]
    assert client.get("/api/results").json()["results"] == []


def test_apollo_is_gracefully_off(client):
    r = client.post("/api/apollo/enrich", json={"domain": "example.com"}).json()
    assert r["ok"] is False and "off" in r["reason"]


def test_jev_test_with_fake(client):
    assert client.get("/api/jev/test").json()["ok"]


def test_every_page_renders_without_a_key(monkeypatch):
    for name in ("TYPESAFE_API_KEY", "JEV_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(server, "FAKE_MODE", False)
    server.set_client(None)
    with TestClient(server.app) as c:
        s = c.get("/api/status").json()
        assert s["jev_key"] is False and s["leads"] == 65
        for url in ("/", "/api/leads", "/api/leads/L001", "/api/results", "/api/icp", "/api/icp/presets", "/api/questions", "/api/playbook", "/api/crm", "/api/review"):
            assert c.get(url).status_code == 200, url
        r = c.post("/api/score/L001")
        assert r.status_code == 503 and "TYPESAFE_API_KEY" in r.json()["detail"]


def test_flag_unjudged_is_409(client):
    r = client.post("/api/leads/L001/command", json={"kind": "flag"})
    assert r.status_code == 409 and r.json()["detail"]["refusal"] == "not_judged"


def test_send_decline_unjudged_is_409(client):
    r = client.post("/api/leads/L001/command", json={"kind": "send_decline"})
    assert r.status_code == 409 and r.json()["detail"]["refusal"] == "not_judged"


def test_empty_reply_is_409(client):
    r = client.post("/api/leads/L001/reply", json={"text": "  "})
    assert r.status_code == 409 and r.json()["detail"]["refusal"] == "empty_reply"


def test_dismiss_hides_contact(client):
    r = client.post("/api/leads/L001/command", json={"kind": "dismiss"})
    assert r.status_code == 200
    lead = r.json()["lead"]
    assert lead["disposition"] == "dismissed" and lead["contact"]["kind"] == "hidden"
    assert "email" not in json.dumps(lead.get("person") or {})


def test_csv_import_http(client):
    csv = "name,domain,title,message\nAda,a.de,Founder,Hi\nBob,b.de,CMO,Hello\nCara,c.de,VP,Hey\n"
    r = client.post("/api/imports", json={"csv": csv, "import_id": "http-1"}).json()
    assert r["rows"] == 3 and len(r["inserted"]) == 3
    again = client.post("/api/imports", json={"csv": csv, "import_id": "http-1"}).json()
    assert again["inserted"] == []


def test_rescore_draft_does_not_mint_a_version(client):
    from leadqualifier.ledger import get_ledger

    n = len(get_ledger().list_icp_versions())
    icp = client.get("/api/icp").json()["icp"]
    icp["thresholds"]["fit_hot"] = 0.99
    client.post("/api/rescore", json={"icp": icp})
    assert len(get_ledger().list_icp_versions()) == n
