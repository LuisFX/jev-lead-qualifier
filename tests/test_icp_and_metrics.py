from __future__ import annotations

import copy

import pytest

from leadqualifier import config, icp as icp_mod
from leadqualifier.metrics import compute_metrics, format_table


def test_presets_load_and_validate():
    ids = [p["id"] for p in icp_mod.list_presets()]
    assert set(ids) >= {"lanternfield_agencies", "b2b_saas_founders", "ecommerce_brands"}
    for pid in ids:
        icp = icp_mod.load_preset(pid)
        assert icp["pains"] and icp["personas"] and icp["industries"] and icp["disqualifiers"]
        assert all(isinstance(v, dict) and "weight" in v for v in icp["pains"].values())


def test_live_icp_is_seeded_from_default_and_saved_to_isolated_file():
    assert not config.ICP_FILE.exists()
    icp = icp_mod.load()
    assert icp["id"] == config.DEFAULT_PRESET and config.ICP_FILE.exists()
    icp["thresholds"]["fit_hot"] = 0.7
    icp_mod.save(icp)
    assert icp_mod.load()["thresholds"]["fit_hot"] == 0.7
    assert icp_mod.reset()["thresholds"]["fit_hot"] != 0.7


@pytest.mark.parametrize("mutate,msg", [
    (lambda d: d.pop("pains"), "missing"),
    (lambda d: d["industries"].__setitem__("Bad Id", "x"), "slug"),
    (lambda d: d["thresholds"].__setitem__("fit_warm", 0.9), "warm thresholds"),
    (lambda d: d.__setitem__("min_revenue_band", "1m_plus"), "min_revenue_band"),
    (lambda d: d["industries"].__setitem__("other", "x"), "other"),
])
def test_validation_errors(icp, mutate, msg):
    d = copy.deepcopy(icp)
    mutate(d)
    with pytest.raises(icp_mod.ICPError, match=msg):
        icp_mod.validate(d)


def test_string_pains_are_upgraded_to_objects(icp):
    d = copy.deepcopy(icp)
    d["pains"]["new_one"] = "A plain string pain"
    v = icp_mod.validate(d)
    assert v["pains"]["new_one"] == {"description": "A plain string pain", "weight": 1.0}


def _res(lid, tier, persona="founder_owner", pain="manual_reporting", review=False, fit=0.9, intent=0.8):
    return {"lead_id": lid, "tier": tier, "fit": fit, "intent": intent, "primary_pain": pain, "why": ["x"],
            "components": {"persona": {"choice": persona}}, "confidence": {"needs_review": review}}


def test_metrics_split_by_confidence():
    gold = {"A": {"tier": "hot", "persona": "founder_owner", "primary_pain": "manual_reporting"},
            "B": {"tier": "warm", "persona": "founder_owner", "primary_pain": None},
            "C": {"tier": "disqualify"}, "D": {"tier": "nurture", "persona": "marketing_lead", "primary_pain": None}}
    results = [_res("A", "hot"), _res("B", "nurture", pain=None, review=True), _res("C", "disqualify"), _res("D", "nurture", persona="marketing_lead", pain=None)]
    m = compute_metrics(results, gold)
    assert m["n"] == 4 and m["tier_accuracy"] == 0.75 and m["tier_accuracy_adjacent"] == 1.0
    assert m["persona_accuracy"] == 1.0 and m["persona_n"] == 3
    assert m["pain_accuracy"] == 1.0 and m["pain_n"] == 3
    assert m["by_confidence"]["auto"] == {"n": 3, "tier_accuracy": 1.0}
    assert m["by_confidence"]["review"] == {"n": 1, "tier_accuracy": 0.0}
    assert m["confusion"]["warm"]["nurture"] == 1 and m["errors"][0]["lead_id"] == "B"
    assert m["per_tier"]["hot"]["precision"] == 1.0
    assert "tier accuracy 0.750" in format_table(m)
    assert compute_metrics([], gold) == {"n": 0}
