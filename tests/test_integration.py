"""Real TypeSafe API over the whole dataset. Skipped without a key.

TEACHING NOTE: this suite spends money. It stays skipped until TYPESAFE_API_KEY
wakes it. Answers go to a temp sqlite ledger, never data/firstread.sqlite.
"""

    ./run.sh test-all            (or: uv run pytest -m integration -s)
Cost: 65 requests ≈ 1.5 cents, plus a partial re-run for the added pain (≈ 0.2 cents).
Uses a temporary cache so the numbers are fresh, never the demo cache in data/cache.
"""

from __future__ import annotations

import copy

import pytest

from leadqualifier import config, icp as icp_mod
from leadqualifier.ledger import Ledger
from leadqualifier.leads import load_crm, load_gold, load_leads, load_playbook
from leadqualifier.metrics import compute_metrics, format_table
from leadqualifier.pipeline import Qualifier, run_totals

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if not config.typesafe_api_key():
        pytest.skip("TYPESAFE_API_KEY / JEV_API_KEY not set")
    icp = icp_mod.load_preset(config.DEFAULT_PRESET)
    leads = load_leads()
    cache = Ledger(tmp_path_factory.mktemp("cache") / "answers.sqlite")
    qual = Qualifier(icp, load_crm(), load_playbook(), cache=cache)
    results = qual.score_many(leads, workers=config.workers())
    totals = run_totals(results, len(leads) - len(results), 0.0)
    metrics = compute_metrics(results, load_gold())
    print("\n" + format_table(metrics))
    print(f"requests={totals['requests']} tokens={totals['input_tokens']} cost=${totals['cost_usd']:.4f} "
          f"per_1000=${totals['cost_per_1000_usd']:.3f} latency_mean={totals['latency_mean_ms']}ms p50={totals['latency_p50_ms']}ms")
    return {"icp": icp, "leads": leads, "cache": cache, "qual": qual, "results": {r["lead_id"]: r for r in results}, "totals": totals, "metrics": metrics}


def test_all_leads_scored_with_one_request_each(run):
    assert len(run["results"]) == 65 and run["totals"]["errors"] == 0
    assert run["totals"]["requests"] == 65
    assert all(r["meta"]["n_asked"] == r["meta"]["n_questions"] for r in run["results"].values())


def test_tier_accuracy_vs_gold(run):
    m = run["metrics"]
    assert m["tier_accuracy"] >= 0.8, format_table(m)
    assert m["persona_accuracy"] >= 0.85
    assert m["pain_accuracy"] >= 0.85
    # everything routed without a human must be at least as accurate as the flagged bucket
    assert m["by_confidence"]["auto"]["tier_accuracy"] >= 0.9


def test_cost_and_latency_per_lead(run):
    t = run["totals"]
    assert t["cost_per_1000_usd"] < 1.0          # well under a dollar per 1,000 leads
    assert t["latency_p50_ms"] < 2000


def test_demo_beat_b_vague_but_hot(run):
    r = run["results"]["L001"]
    assert r["tier"] == "hot", r["why"]
    assert r["primary_pain"] == "manual_reporting"
    assert r["evidence"]["pains"]["manual_reporting"]["sentence"] in ("S1", "S2")
    assert r["evidence"]["intent"] is not None and r["evidence"]["intent"]["sentence"] == "S4"
    assert r["route"]["label"] == "Founder call" and r["next_action"]["id"] == "book_call"


def test_demo_beat_c_vendor_and_student_disqualified(run):
    v = run["results"]["L047"]
    assert v["tier"] == "disqualify" and any(d["id"] in ("is_vendor_pitch", "competitor", "is_competitor") for d in v["disqualifiers"])
    s = run["results"]["L048"]
    assert s["tier"] == "disqualify" and any("student" in d["id"] for d in s["disqualifiers"])
    for r in (v, s):
        assert r["next_action"]["id"] == "decline_politely"


def test_demo_beat_d_duplicate_goes_to_account_owner(run):
    r = run["results"]["L060"]
    assert r["tier"] == "existing" and r["existing_account"]["id"] == "acc_hafenblick"
    assert r["route"]["owner"] == "Lena Berg" and r["existing_account"]["p"] >= 0.6
    near = run["results"]["L065"]  # Kontor Süd vs CRM account Kontor Nord: shortlisted by code, rejected by Jev
    assert near["dedupe"]["candidates"] and near["existing_account"] is None and near["tier"] != "existing"


def test_demo_beat_e_revenue_gate_and_new_pain(run):
    icp, cache, leads = run["icp"], run["cache"], run["leads"]
    strict = copy.deepcopy(icp)
    strict["min_revenue_band"] = "30k_100k"
    q = Qualifier(icp_mod.validate(strict), load_crm(), load_playbook(), client=None, cache=cache)
    moved = {}
    for lead in leads:
        before = run["results"][lead.id]["tier"]
        after = q.rescore(lead)["tier"]
        if before != after:
            moved[lead.id] = (before, after)
    assert {"L006", "L020", "L025"} <= set(moved), moved
    assert all(a == "disqualify" for _, a in moved.values())

    with_pain = copy.deepcopy(icp)
    with_pain["pains"]["client_churn"] = {"description": "Clients leave or threaten to leave because results are not visible, reports are late or communication is slow", "weight": 0.8}
    q2 = Qualifier(icp_mod.validate(with_pain), load_crm(), load_playbook(), cache=cache)
    stale = q2.stale_summary(leads)
    # one pain Noul per lead, plus one evidence Choice for every lead that has any sentence to point at
    assert stale["questions_to_ask"] == sum(2 if lead.sentences() else 1 for lead in leads)
    results = q2.score_many(leads, workers=config.workers())
    asked = [r["meta"]["n_asked"] for r in results]
    assert max(asked) == 2 and sum(r["meta"]["input_tokens"] for r in results) < run["totals"]["input_tokens"] * 0.6
    churn = [r["lead_id"] for r in results if r["components"]["pains"]["scores"]["client_churn"] >= icp["thresholds"]["pain_p"]]
    print(f"\nclient_churn detected on {churn}")
    assert "L022" in churn and len(churn) <= 6


def test_profiles_are_not_marked_spam(run):
    for lid in ("L063", "L028", "L015"):
        r = run["results"][lid]
        assert "is_spam_or_automated" not in r["answers"] and r["tier"] != "disqualify" or lid == "L063" and r["tier"] == "existing"
