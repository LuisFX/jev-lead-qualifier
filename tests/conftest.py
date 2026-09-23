from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from leadqualifier import config, icp as icp_mod
from leadqualifier.fake_client import FakeClient
from leadqualifier.leads import Lead, load_crm, load_leads, load_playbook

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolate_files(tmp_path, monkeypatch):
    """Never touch data/icp.json or data/cache during unit tests."""
    monkeypatch.setattr(config, "ICP_FILE", tmp_path / "icp.json")
    monkeypatch.setattr(config, "RESULT_CACHE_FILE", tmp_path / "cache" / "answers.json")
    monkeypatch.setattr(config, "APOLLO_CACHE_DIR", tmp_path / "apollo")
    monkeypatch.delenv("APOLLO_ENRICH", raising=False)
    yield


@pytest.fixture
def icp() -> dict:
    return icp_mod.load_preset("lanternfield_agencies")


@pytest.fixture
def crm() -> list[dict]:
    return load_crm()


@pytest.fixture
def playbook() -> dict:
    return load_playbook()


@pytest.fixture
def leads() -> list[Lead]:
    return load_leads()


@pytest.fixture
def lead_by_id(leads):
    return {l.id: l for l in leads}


@pytest.fixture
def fake_client() -> FakeClient:
    return FakeClient()


# --------------------------------------------------------------------------- answer builders


def noul(p: float) -> dict:
    return {"type": "noul", "p": p}


def choice(pick: str, options: list[str], p: float = 0.9) -> dict:
    rest = (1.0 - p) / max(1, len(options) - 1)
    probs = {o: (p if o == pick else rest) for o in options}
    return {"type": "choice", "choice": pick, "confidence": p, "probabilities": probs}


def score(level: int, n: int, p: float = 0.9) -> dict:
    rest = (1.0 - p) / max(1, n - 1)
    probs = {str(i): (p if i == level else rest) for i in range(n)}
    s = sum(int(k) * v for k, v in probs.items())
    return {"type": "score", "score": s, "level": level, "confidence": p, "probabilities": probs, "n_levels": n}


def base_answers(icp: dict, **over) -> dict:
    """A confident, well-fitting founder of a marketing agency with a reporting pain, asking for a call."""
    industries = list(icp["industries"]) + ["other"]
    personas = list(icp["personas"]) + ["other"]
    a = {
        "industry": choice("marketing_agency", industries),
        "company_maturity": score(2, 5),
        "size_band_stated": choice("not_stated", icp["size_bands"] + ["not_stated"]),
        "revenue_band_stated": choice("not_stated", icp["revenue_bands"] + ["not_stated"]),
        "geo_fit": noul(0.95),
        "persona": choice("founder_owner", personas),
        "decision_authority": score(3, 4),
        "is_vendor_pitch": noul(0.05), "is_student_or_jobseeker": noul(0.02), "is_competitor": noul(0.05),
        "purchase_intent": score(3, 5),
        "timeline_stated": choice("this_month", ["this_month", "this_quarter", "later", "not_stated"]),
        "budget_signal": noul(0.1), "urgency": noul(0.8), "asks_for_meeting": noul(0.95),
        "objection_present": choice("none", ["price", "timing", "trust", "none"]),
        "is_spam_or_automated": noul(0.03), "contains_pii_request": noul(0.02),
        "next_best_action": choice("book_call", ["book_call", "send_case_study_agency", "send_case_study_coach", "ask_qualifying_question_size",
                                                 "ask_qualifying_question_pain", "add_to_nurture", "route_to_account_owner", "decline_politely"]),
    }
    for dq in icp["disqualifiers"]:
        a[f"dq_{dq}"] = noul(0.03)
    for pid in icp["pains"]:
        a[f"pain_{pid}"] = noul(0.05)
    a["pain_manual_reporting"] = noul(0.95)
    a["evidence_manual_reporting"] = choice("S2", ["S1", "S2", "S3", "none"])
    a["intent_evidence"] = choice("S3", ["S1", "S2", "S3", "none"])
    a.update(over)
    return a


@pytest.fixture
def answers(icp):
    return lambda **over: base_answers(icp, **over)


@pytest.fixture
def make_lead():
    def _mk(id="LX", message="We are drowning in reporting for 14 clients. Every month we lose a week. Could we talk this week?",
            company=None, person=None, source="website_form") -> Lead:
        company = company if company is not None else {"name": "Test Agency", "domain": "test-agency.de", "description": "Paid social agency", "location": "Hamburg, DE"}
        person = person if person is not None else {"name": "Mara Test", "title": "Founder", "company": "Test Agency", "email": "mara@test-agency.de", "phone": "+49 40 123"}
        msg = {"text": message, "from_domain": "test-agency.de"} if message else None
        return Lead(id=id, source=source, received_at="2026-09-14T09:00:00Z", person=person, company=company, message=msg)
    return _mk


@pytest.fixture
def modified_icp(icp):
    def _mod(**changes):
        d = copy.deepcopy(icp)
        for k, v in changes.items():
            if isinstance(v, dict) and isinstance(d.get(k), dict):
                d[k].update(v)
            else:
                d[k] = v
        return icp_mod.validate(d)
    return _mod
