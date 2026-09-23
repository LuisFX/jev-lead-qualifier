"""Question fingerprints drive cache invalidation: edit one pain → only its questions are re-asked."""

from __future__ import annotations

import copy

from leadqualifier import constants as C
from leadqualifier.cache import ResultCache


def test_store_and_fetch_by_fingerprint(tmp_path):
    cache = ResultCache(tmp_path / "c.json")
    fps = {"a": "fp1", "b": "fp2"}
    cache.store("L1", fps, {"a": {"type": "noul", "p": 0.5}, "b": {"type": "noul", "p": 0.1}}, {"qids": ["a", "b"], "latency_ms": 300, "input_tokens": 1000})
    assert cache.cached_answers("L1", fps) == {"a": {"type": "noul", "p": 0.5}, "b": {"type": "noul", "p": 0.1}}
    assert cache.missing("L1", {"a": "fp1", "b": "CHANGED"}) == ["b"]
    cache.save()
    again = ResultCache(tmp_path / "c.json")
    assert again.cached_answers("L1", fps)["a"]["p"] == 0.5
    assert again.history()["requests"] == 1 and again.history()["tokens_in"] == 1000


def test_invalidate_specific_questions(tmp_path):
    cache = ResultCache(tmp_path / "c.json")
    cache.store("L1", {"a": "1", "b": "2"}, {"a": {"p": 1}, "b": {"p": 2}})
    cache.store("L2", {"a": "1"}, {"a": {"p": 1}})
    assert cache.invalidate(["a"]) == 2
    assert cache.missing("L1", {"a": "1", "b": "2"}) == ["a"]
    cache.clear()
    assert len(cache) == 0


def test_editing_one_pain_changes_only_its_two_fingerprints(icp):
    q0 = C.build_questions(icp, sentence_ids=["S1", "S2"], playbook={"book_call": {"description": "x"}})
    icp2 = copy.deepcopy(icp)
    icp2["pains"]["manual_reporting"]["description"] += " and quarterly reviews"
    q1 = C.build_questions(icp2, sentence_ids=["S1", "S2"], playbook={"book_call": {"description": "x"}})
    f0, f1 = C.fingerprints(q0), C.fingerprints(q1)
    changed = sorted(k for k in f0 if f0[k] != f1.get(k))
    assert changed == ["evidence_manual_reporting", "pain_manual_reporting"]


def test_adding_a_pain_adds_two_questions_and_keeps_the_rest(icp):
    q0 = C.build_questions(icp, sentence_ids=["S1"], playbook={"book_call": {"description": "x"}})
    icp2 = copy.deepcopy(icp)
    icp2["pains"]["client_churn"] = {"description": "Clients leave", "weight": 0.8}
    q1 = C.build_questions(icp2, sentence_ids=["S1"], playbook={"book_call": {"description": "x"}})
    f0, f1 = C.fingerprints(q0), C.fingerprints(q1)
    assert set(f1) - set(f0) == {"pain_client_churn", "evidence_client_churn"}
    assert all(f0[k] == f1[k] for k in f0)


def test_thresholds_and_weights_do_not_touch_fingerprints(icp):
    q0 = C.build_questions(icp, playbook={"book_call": {"description": "x"}})
    icp2 = copy.deepcopy(icp)
    icp2["thresholds"]["fit_hot"] = 0.9
    icp2["weights"]["pains"] = 0.5
    icp2["min_revenue_band"] = "over_100k"
    q1 = C.build_questions(icp2, playbook={"book_call": {"description": "x"}})
    assert C.fingerprints(q0) == C.fingerprints(q1)


def test_message_only_questions_are_skipped_for_profiles(icp):
    q_msg = C.build_questions(icp, sentence_ids=["S1"], has_message=True)
    q_prof = C.build_questions(icp, sentence_ids=["N1"], has_message=False)
    for qid in C.MESSAGE_ONLY:
        assert qid in q_msg and qid not in q_prof
    assert "purchase_intent" in q_prof and "industry" in q_prof


def test_question_shapes_follow_the_api_contract(icp):
    q = C.build_questions(icp, sentence_ids=["S1", "S2"], crm_candidates=[{"id": "acc", "name": "A", "domain": "a.de", "about": "x"}], playbook={"book_call": {"description": "x"}, "add_to_nurture": {"description": "y"}})
    for qid, qq in q.items():
        assert qq["type"] in ("noul", "choice", "score"), qid
        if qq["type"] == "choice":
            assert isinstance(qq["criteria"], dict) and 2 <= len(qq["criteria"]) <= 255
        if qq["type"] == "score":
            assert isinstance(qq["criteria"], list) and 2 <= len(qq["criteria"]) <= 10
    assert "other" in q["industry"]["criteria"] and "none" in q["same_account"]["criteria"] and "not_stated" in q["size_band_stated"]["criteria"]
    assert set(q["evidence_manual_reporting"]["criteria"]) == {"S1", "S2", "none"}
    groups = {C.group_of(qid) for qid in q}
    assert groups == set(C.GROUP_ORDER)
