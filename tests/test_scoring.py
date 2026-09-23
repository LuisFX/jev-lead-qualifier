"""Composite fit/intent, tier matrix, overrides, gating, routing, actions — all pure code, no Jev."""

from __future__ import annotations

from datetime import datetime

import pytest

from leadqualifier import scoring as S
from tests.conftest import choice, noul, score


def assemble(icp, lead, answers, playbook, candidates=None):
    return S.assemble(icp, lead, answers, candidates or [], playbook, now=datetime(2026, 9, 22, 10, 0))


# --------------------------------------------------------------------------- composite


def test_fit_is_weighted_mean_of_components(icp, answers):
    comps = S.fit_components(icp, answers())
    fit, penalties, contrib = S.composite_fit(icp, comps, answers())
    assert penalties == []
    assert abs(sum(contrib.values()) - fit) < 1e-6
    # industry 0.9 (1 - P(other)), maturity level 2 → 1.0-ish, persona founder → 0.9, pains → 0.95
    assert comps["industry"]["fit"] == pytest.approx(1 - 0.1 / 4, abs=0.01)
    assert comps["persona"]["fit"] > 0.85
    assert comps["pains"]["primary"] == "manual_reporting"
    assert fit > 0.85


def test_other_industry_and_other_persona_lower_fit(icp, answers):
    industries = list(icp["industries"]) + ["other"]
    personas = list(icp["personas"]) + ["other"]
    a = answers(industry=choice("other", industries), persona=choice("other", personas))
    comps = S.fit_components(icp, a)
    assert comps["industry"]["fit"] < 0.15
    assert comps["persona"]["fit"] < 0.15
    fit, _, _ = S.composite_fit(icp, comps, a)
    assert fit < 0.5


def test_maturity_fit_uses_icp_vector(icp, answers):
    lvl0 = S.fit_components(icp, answers(company_maturity=score(0, 5)))["maturity"]["fit"]
    lvl2 = S.fit_components(icp, answers(company_maturity=score(2, 5)))["maturity"]["fit"]
    lvl4 = S.fit_components(icp, answers(company_maturity=score(4, 5)))["maturity"]["fit"]
    assert lvl0 < lvl4 < lvl2


def test_size_band_outside_target_and_geo_penalties(icp, answers):
    bands = icp["size_bands"] + ["not_stated"]
    a = answers(size_band_stated=choice("200+", bands), geo_fit=noul(0.1))
    comps = S.fit_components(icp, a)
    fit_pen, penalties, _ = S.composite_fit(icp, comps, a)
    fit_ok, _, _ = S.composite_fit(icp, comps, answers())
    assert len(penalties) == 2
    assert fit_pen == pytest.approx(fit_ok * 0.8 * 0.85, abs=0.01)


def test_size_band_below_confidence_floor_is_not_used(icp, answers):
    bands = icp["size_bands"] + ["not_stated"]
    a = answers(size_band_stated=choice("200+", bands, p=0.4))
    _, penalties, _ = S.composite_fit(icp, S.fit_components(icp, a), a)
    assert penalties == []


def test_intent_composite_and_profile_without_message(icp, answers):
    a = answers()
    intent, contrib = S.composite_intent(icp, a, has_message=True)
    assert intent > 0.7 and contrib["asks_for_meeting"] > 0
    intent_profile, contrib_p = S.composite_intent(icp, a, has_message=False)
    assert contrib_p["asks_for_meeting"] == 0 and contrib_p["urgency"] == 0
    assert intent_profile < intent


# --------------------------------------------------------------------------- tier matrix


@pytest.mark.parametrize("fit,intent,tier", [
    (0.9, 0.9, "hot"), (0.9, 0.4, "warm"), (0.9, 0.1, "nurture"),
    (0.5, 0.9, "warm"), (0.5, 0.4, "warm"), (0.5, 0.1, "nurture"),
    (0.2, 0.9, "warm"), (0.2, 0.4, "nurture"), (0.2, 0.1, "nurture"),
])
def test_tier_matrix(icp, fit, intent, tier):
    assert S.tier_from_matrix(icp, fit, intent) == tier


def test_thresholds_are_inclusive(icp):
    t = icp["thresholds"]
    assert S.tier_from_matrix(icp, t["fit_hot"], t["intent_hot"]) == "hot"
    assert S.tier_from_matrix(icp, t["fit_hot"], t["intent_hot"] - 0.001) == "warm"


# --------------------------------------------------------------------------- overrides


def test_hot_lead_end_to_end(icp, playbook, make_lead, answers):
    r = assemble(icp, make_lead(), answers(), playbook)
    assert r["tier"] == "hot"
    assert r["route"]["label"] == "Founder call" and len(r["route"]["slots"]) == 2
    assert r["route"]["slots"][0].startswith("Tue")
    assert r["next_action"]["id"] == "book_call" and "Mara" in r["next_action"]["text"]
    assert r["primary_pain"] == "manual_reporting"
    assert r["evidence"]["pains"]["manual_reporting"]["sentence"] == "S2"
    assert r["evidence"]["intent"]["sentence"] == "S3"
    assert not r["confidence"]["needs_review"] and "hold" not in r["route"]


def test_vendor_pitch_overrides_a_perfect_fit(icp, playbook, make_lead, answers):
    r = assemble(icp, make_lead(), answers(is_vendor_pitch=noul(0.95)), playbook)
    assert r["tier"] == "disqualify"
    assert [d["id"] for d in r["disqualifiers"]] == ["is_vendor_pitch"]
    assert r["next_action"]["id"] == "decline_politely" and r["next_action"]["source"] == "rule"
    assert r["route"]["label"] == "Polite decline"


def test_icp_disqualifier_and_threshold(icp, modified_icp, playbook, make_lead, answers):
    a = answers(dq_enterprise=noul(0.75))
    assert assemble(icp, make_lead(), a, playbook)["tier"] == "disqualify"
    lenient = modified_icp(thresholds={"disqualifier_p": 0.8})
    assert assemble(lenient, make_lead(), a, playbook)["tier"] == "hot"


def test_revenue_gate_and_raising_the_minimum(icp, modified_icp, playbook, make_lead, answers):
    bands = icp["revenue_bands"] + ["not_stated"]
    a = answers(revenue_band_stated=choice("10k_30k", bands))
    assert assemble(icp, make_lead(), a, playbook)["tier"] == "hot"
    strict = modified_icp(min_revenue_band="30k_100k")
    r = assemble(strict, make_lead(), a, playbook)
    assert r["tier"] == "disqualify" and r["disqualifiers"][0]["id"] == "revenue_below_minimum"
    assert "revenue gate" in r["move_up"].lower() or "revenue" in r["move_up"].lower()
    # a low-confidence revenue reading is never used to disqualify
    a_unsure = answers(revenue_band_stated=choice("under_10k", bands, p=0.4))
    assert assemble(icp, make_lead(), a_unsure, playbook)["tier"] == "hot"


def test_existing_account_routes_to_owner(icp, playbook, make_lead, answers):
    cands = [{"id": "acc_x", "name": "Test Agency GmbH", "domain": "test-agency.de", "status": "customer", "owner": "Lena Berg", "code_score": 1.0, "code_reasons": ["same domain"]}]
    a = answers(same_account=choice("acc_x", ["acc_x", "none"], p=0.92))
    r = assemble(icp, make_lead(), a, playbook, cands)
    assert r["tier"] == "existing"
    assert r["existing_account"]["owner"] == "Lena Berg" and r["route"]["owner"] == "Lena Berg"
    assert r["next_action"]["id"] == "route_to_account_owner" and "Lena Berg" in r["next_action"]["text"]
    assert not r["confidence"]["needs_review"]


def test_existing_account_below_dedupe_threshold_is_ignored(icp, playbook, make_lead, answers):
    cands = [{"id": "acc_x", "name": "Test Agency GmbH", "domain": "test-agency.de", "status": "customer", "owner": "Lena", "code_score": .6, "code_reasons": []}]
    a = answers(same_account=choice("acc_x", ["acc_x", "none"], p=0.5))
    r = assemble(icp, make_lead(), a, playbook, cands)
    assert r["tier"] == "hot" and r["existing_account"] is None and r["dedupe"]["verdict"] == "none"


def test_spam_beats_existing_account(icp, playbook, make_lead, answers):
    cands = [{"id": "acc_x", "name": "Test", "domain": "test-agency.de", "status": "customer", "owner": "Lena", "code_score": 1, "code_reasons": []}]
    a = answers(same_account=choice("acc_x", ["acc_x", "none"]), is_spam_or_automated=noul(0.9))
    assert assemble(icp, make_lead(), a, playbook, cands)["tier"] == "disqualify"


def test_timing_objection_parks_a_warm_lead(icp, playbook, make_lead, answers):
    a = answers(purchase_intent=score(2, 5), asks_for_meeting=noul(0.1), urgency=noul(0.05),
                timeline_stated=choice("later", ["this_month", "this_quarter", "later", "not_stated"]))
    r0 = assemble(icp, make_lead(), a, playbook)
    assert r0["tier"] == "warm"
    a["objection_present"] = choice("timing", ["price", "timing", "trust", "none"], p=0.9)
    r1 = assemble(icp, make_lead(), a, playbook)
    assert r1["tier"] == "nurture" and any("timing objection" in w for w in r1["why"])


# --------------------------------------------------------------------------- gating & routing


def test_low_confidence_flags_for_review_and_holds_route(icp, playbook, make_lead, answers):
    industries = list(icp["industries"]) + ["other"]
    a = answers(industry=choice("marketing_agency", industries, p=0.4))
    r = assemble(icp, make_lead(), a, playbook)
    assert r["confidence"]["needs_review"] and r["confidence"]["label"] == "low"
    assert r["route"]["hold"] and "confidence" in r["route"]["hold_reason"]


def test_borderline_score_is_flagged(icp, playbook, make_lead, answers):
    t = icp["thresholds"]
    # force intent just under the hot threshold: level 3 (0.375) + meeting 0.95×0.2 (0.19) + budget 0.3×0.1 (0.03) ≈ 0.595
    a = answers(urgency=noul(0.0), timeline_stated=choice("not_stated", ["this_month", "this_quarter", "later", "not_stated"]), asks_for_meeting=noul(0.95), budget_signal=noul(0.3))
    r = assemble(icp, make_lead(), a, playbook)
    assert abs(r["intent"] - t["intent_hot"]) < S.BORDERLINE
    assert r["confidence"]["needs_review"] and any("within" in x for x in r["confidence"]["reasons"])


def test_pii_request_flags_security_review(icp, playbook, make_lead, answers):
    r = assemble(icp, make_lead(), answers(contains_pii_request=noul(0.9)), playbook)
    assert any(f["id"] == "pii_request" for f in r["flags"])
    assert r["route"]["hold"] and "security review" in r["confidence"]["reasons"][0]


def test_action_is_constrained_to_the_tier(icp, playbook, make_lead, answers):
    a = answers(purchase_intent=score(2, 5), asks_for_meeting=noul(0.1), urgency=noul(0.05),
                timeline_stated=choice("not_stated", ["this_month", "this_quarter", "later", "not_stated"]))
    r = assemble(icp, make_lead(), a, playbook)
    assert r["tier"] == "warm"
    assert r["next_action"]["id"] != "book_call" and r["next_action"]["source"] == "jev-constrained"
    assert "warm" in playbook[r["next_action"]["id"]]["tiers"]


def test_move_up_explains_the_gap(icp, playbook, make_lead, answers):
    a = answers(purchase_intent=score(2, 5), asks_for_meeting=noul(0.1), urgency=noul(0.05),
                timeline_stated=choice("not_stated", ["this_month", "this_quarter", "later", "not_stated"]))
    r = assemble(icp, make_lead(), a, playbook)
    assert r["move_up"].startswith("To reach Hot") and "asks for a call" in r["move_up"]
    hot = assemble(icp, make_lead(), answers(), playbook)
    assert hot["move_up"].startswith("Already")


def test_checklist_never_guesses_size_or_revenue(icp, playbook, make_lead, answers):
    r = assemble(icp, make_lead(), answers(), playbook)
    by = {c["label"]: c for c in r["checklist"]}
    assert by["Team size"]["state"] == "unknown" and by["Revenue band"]["state"] == "unknown"
    assert by["No disqualifier"]["state"] == "ok"


def test_next_slots_are_deterministic():
    slots = S.next_slots(datetime(2026, 9, 22, 10, 0))  # a Tuesday
    assert slots == ["Tue 29 Sep · 11:00 CET", "Thu 24 Sep · 15:00 CET"]


def test_to_generic_shapes():
    assert S.to_generic({"type": "noul"}, {"noul": 0.73}) == {"type": "noul", "p": 0.73}
    c = S.to_generic({"type": "choice"}, {"choice": "a", "confidence": 0.8, "probabilities": {"a": 0.8, "b": 0.2}})
    assert c["choice"] == "a" and c["probabilities"]["b"] == 0.2
    s = S.to_generic({"type": "score", "criteria": ["x", "y", "z"]}, {"score": 1.6, "confidence": 0.7, "probabilities": {"0": 0.1, "1": 0.2, "2": 0.7}})
    assert s["level"] == 2 and s["n_levels"] == 3
