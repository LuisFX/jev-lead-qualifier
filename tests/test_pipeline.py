"""Qualifier with a fake Jev: one request per lead, cache reuse, ICP edits, privacy of the state.

TEACHING NOTE: `Ledger` here is the answer store. A persist proof belongs in
`test_ledger.py` (new connection), not in these scoring tests.
"""

from __future__ import annotations

import copy
import json

from leadqualifier import icp as icp_mod
from leadqualifier.ledger import Ledger
from leadqualifier.leads import split_sentences, normalise_domain
from leadqualifier.pipeline import Qualifier, run_totals


def test_state_never_contains_contact_details(make_lead):
    lead = make_lead()
    blob = json.dumps(lead.to_state())
    assert "mara@test-agency.de" not in blob and "+49 40 123" not in blob
    assert "Mara Test" in blob and "drowning in reporting" in blob
    assert lead.to_state()["sentences"]["S1"].startswith("We are drowning")


def test_sentence_ids_are_stable_and_split_sanely():
    s = split_sentences("Hi — we're drowning. Every month we lose a week! Do you do this? Could we talk?")
    assert s == ["Hi — we're drowning.", "Every month we lose a week!", "Do you do this?", "Could we talk?"]
    assert normalise_domain("https://www.Example.com/path") == "example.com"


def test_one_request_then_cache(icp, crm, playbook, fake_client, make_lead, tmp_path):
    cache = Ledger(tmp_path / "c.sqlite")
    q = Qualifier(icp, crm, playbook, client=fake_client, cache=cache)
    lead = make_lead()
    r1 = q.score(lead)
    assert len(fake_client.calls) == 1
    assert r1["meta"]["n_asked"] == r1["meta"]["n_questions"] > 25
    assert set(fake_client.calls[0]["qids"]) == set(r1["answers"])
    r2 = q.score(lead)
    assert len(fake_client.calls) == 1 and r2["meta"]["cached"] and r2["meta"]["n_asked"] == 0
    assert r2["tier"] == r1["tier"]


def test_adding_a_pain_asks_only_two_questions(icp, crm, playbook, fake_client, make_lead, tmp_path):
    cache = Ledger(tmp_path / "c.sqlite")
    lead = make_lead()
    Qualifier(icp, crm, playbook, client=fake_client, cache=cache).score(lead)
    icp2 = copy.deepcopy(icp)
    icp2["pains"]["client_churn"] = {"description": "Clients leave because reports are late", "weight": 0.8}
    q2 = Qualifier(icp2, crm, playbook, client=fake_client, cache=cache)
    assert q2.stale_summary([lead])["questions_to_ask"] == 2
    r = q2.score(lead)
    assert sorted(fake_client.calls[-1]["qids"]) == ["evidence_client_churn", "pain_client_churn"]
    assert "client_churn" in r["components"]["pains"]["scores"]


def test_threshold_change_rescoring_needs_no_call(icp, crm, playbook, fake_client, make_lead, tmp_path):
    cache = Ledger(tmp_path / "c.sqlite")
    lead = make_lead()
    Qualifier(icp, crm, playbook, client=fake_client, cache=cache).score(lead)
    strict = copy.deepcopy(icp)
    strict["thresholds"]["fit_hot"] = 0.99
    strict["thresholds"]["intent_hot"] = 0.99
    r = Qualifier(icp_mod.validate(strict), crm, playbook, client=None, cache=cache).rescore(lead)
    assert r is not None and r["tier"] != "hot" and r["meta"]["n_asked"] == 0 and r["meta"]["stale"] == []
    assert len(fake_client.calls) == 1


def test_rescore_without_cache_returns_none(icp, crm, playbook, make_lead, tmp_path):
    q = Qualifier(icp, crm, playbook, client=None, cache=Ledger(tmp_path / "c.sqlite"))
    assert q.rescore(make_lead()) is None


def test_profile_lead_skips_message_questions(icp, crm, playbook, fake_client, make_lead):
    lead = make_lead(message=None, company={"name": "Profile Co", "domain": "profile.de", "description": "Agency", "location": "Berlin", "news": "Profile Co hires two account managers."})
    r = Qualifier(icp, crm, playbook, client=fake_client, cache=None).score(lead)
    asked = set(fake_client.calls[-1]["qids"])
    assert "is_spam_or_automated" not in asked and "asks_for_meeting" not in asked
    assert "purchase_intent" in asked and "evidence_manual_reporting" in asked  # news sentences exist
    assert r["tier"] != "disqualify" and any(f["id"] == "no_message" for f in r["flags"])


def test_crm_shortlist_adds_same_account_question(icp, crm, playbook, fake_client, make_lead):
    lead = make_lead(company={"name": "Hafenblick Digital", "domain": "hafenblick-digital.de", "description": "x", "location": "Hamburg"})
    r = Qualifier(icp, crm, playbook, client=fake_client, cache=None).score(lead)
    assert "same_account" in fake_client.calls[-1]["qids"]
    assert r["dedupe"]["candidates"][0]["id"] == "acc_hafenblick"
    assert r["tier"] == "existing" and r["route"]["owner"] == "Lena Berg"


def test_score_many_keeps_order_and_reports_errors(icp, crm, playbook, make_lead, tmp_path):
    class Flaky:
        def __init__(self):
            self.n = 0
        def system_one(self, state, questions):
            self.n += 1
            if "Broken" in json.dumps(state):
                raise RuntimeError("boom")
            from leadqualifier.fake_client import FakeClient
            return FakeClient().system_one(state, questions)
    leads = [make_lead(id="A"), make_lead(id="B", company={"name": "Broken Co", "domain": "b.de", "description": "x", "location": "x"}), make_lead(id="C")]
    errors = []
    q = Qualifier(icp, crm, playbook, client=Flaky(), cache=Ledger(tmp_path / "c.sqlite"))
    results = q.score_many(leads, workers=2, on_error=lambda l, e: errors.append(l.id))
    assert [r["lead_id"] for r in results] == ["A", "C"] and errors == ["B"]
    totals = run_totals(results, len(errors), 1.0)
    assert totals["leads"] == 2 and totals["errors"] == 1 and totals["requests"] == 2 and totals["sdr_minutes_saved"] == 12
    assert totals["cost_per_1000_usd"] > 0


def test_whole_dataset_runs_offline(icp, crm, playbook, fake_client, leads, tmp_path):
    q = Qualifier(icp, crm, playbook, client=fake_client, cache=Ledger(tmp_path / "c.sqlite"))
    results = q.score_many(leads, workers=4)
    assert len(results) == len(leads) == 65
    assert all(r["tier"] in ("hot", "warm", "nurture", "disqualify", "existing") for r in results)
    assert all(r["next_action"]["text"] for r in results)
