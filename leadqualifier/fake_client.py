"""A deterministic stand-in for Jev used by unit tests and `FIRSTREAD_FAKE=1`.

It answers every question with the right *shape* (noul / choice / score) from crude keyword
heuristics over the state. It is not meant to be accurate; it is meant to be offline, fast and
stable so tests can exercise scoring, caching, routing and the API surface.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .jev import JevResponse


def _text(state: Any) -> str:
    return json.dumps(state, ensure_ascii=False).lower()


def _h(seed: str) -> float:
    return int(hashlib.sha1(seed.encode()).hexdigest()[:6], 16) / 0xFFFFFF


class FakeClient:
    def __init__(self, latency_s: float = 0.0, responder: Any | None = None):
        self.latency_s = latency_s
        self.responder = responder
        self.calls: list[dict[str, Any]] = []

    def system_one(self, state: Any, questions: dict[str, dict[str, Any]]) -> JevResponse:
        self.calls.append({"state": state, "qids": list(questions)})
        if self.latency_s:
            time.sleep(self.latency_s)
        text = _text(state)
        answers = {}
        for qid, q in questions.items():
            if self.responder:
                custom = self.responder(qid, q, state)
                if custom is not None:
                    answers[qid] = custom
                    continue
            answers[qid] = self._answer(qid, q, text)
        tokens = max(200, len(json.dumps(state)) // 4 + 40 * len(questions))
        return JevResponse(answers=answers, model="fake-jev", input_tokens=tokens, output_tokens=len(questions) * 2,
                           latency_ms=int(self.latency_s * 1000) or 120, request_id="fake", n_questions=len(questions))

    # ------------------------------------------------------------------ heuristics
    def _answer(self, qid: str, q: dict[str, Any], text: str) -> dict[str, Any]:
        t = q["type"]
        if t == "noul":
            return {"type": "noul", "noul": self._noul(qid, text)}
        if t == "choice":
            return self._choice(qid, list(q["criteria"]), text)
        return self._score(qid, len(q["criteria"]), text)

    def _noul(self, qid: str, text: str) -> float:
        kw = {
            "asks_for_meeting": ["call", "talk", "meeting", "demo", "chat"],
            "urgency": ["asap", "drowning", "urgent", "cannot keep up", "deadline"],
            "budget_signal": ["budget", "€", "eur", "spend"],
            "is_vendor_pitch": ["we help", "our platform", "partnership", "guest post", "white-label", "we offer"],
            "is_student_or_jobseeker": ["student", "thesis", "internship", "interview you", "job"],
            "is_competitor": ["we build ai", "automation agency", "ai agents for", "we also build"],
            "is_spam_or_automated": ["unsubscribe", "out of office", "click here", "winner"],
            "contains_pii_request": ["password", "bank details", "client list", "send us your"],
            "geo_fit": [],
        }
        if qid == "geo_fit":
            return 0.1 if any(k in text for k in ["texas", "usa", "california", "australia", "singapore"]) else 0.9
        if qid.startswith("dq_"):
            m = {"too_small": ["no clients yet", "just starting", "side project", "tight"], "enterprise": ["3,000", "corporate", "listed", "enterprise"],
                 "competitor": ["we build ai", "automation agency", "white-label"], "student": ["student", "thesis", "internship"]}
            for key, words in m.items():
                if key in qid:
                    return 0.9 if any(w in text for w in words) else 0.05
            return 0.05
        if qid.startswith("pain_"):
            m = {"reporting": ["report", "deck", "dashboard"], "freelancer": ["freelancer", "capacity", "handover"], "followup": ["follow-up", "follow up", "leads fall", "unanswered"],
                 "onboarding": ["onboard"], "content": ["content", "posts", "repurpos"], "churn": ["churn", "leaving", "retention"]}
            for key, words in m.items():
                if key in qid:
                    return 0.85 if any(w in text for w in words) else 0.08
            return 0.1
        words = kw.get(qid, [])
        if words and any(w in text for w in words):
            return 0.85
        return 0.08 if words else round(0.2 + 0.6 * _h(qid + text[:40]), 3)

    def _choice(self, qid: str, options: list[str], text: str) -> dict[str, Any]:
        pick = options[-1]  # `other` / `none` / `not_stated` are last by construction
        if qid == "industry":
            for o in options:
                if o != "other" and (o.split("_")[0] in text or (o == "marketing_agency" and "agency" in text) or (o == "coaching_business" and "coach" in text)):
                    pick = o
                    break
        elif qid == "persona":
            for o in options:
                if o == "founder_owner" and ("founder" in text or "owner" in text or "ceo" in text or "managing director" in text):
                    pick = o
                    break
                if o == "head_of_operations" and ("operations" in text or "coo" in text):
                    pick = o
                    break
                if o == "head_of_delivery" and ("client services" in text or "account director" in text or "delivery" in text):
                    pick = o
                    break
                if o == "marketing_lead" and "head of marketing" in text:
                    pick = o
                    break
        elif qid == "size_band_stated":
            for o, words in (("solo", ["just me", "solo"]), ("2-10", ["team of 5", "team of six", "team of 8", "eight of us", "six people", "team of four"]),
                             ("11-50", ["12 people", "14 people", "20 people", "25 people", "30 people", "35 people"]), ("200+", ["3,000", "2,000 employees"])):
                if any(w in text for w in words) and o in options:
                    pick = o
                    break
        elif qid == "revenue_band_stated":
            for o, words in (("under_10k", ["€6k", "8k a month", "under 10k"]), ("10k_30k", ["€18k", "€15k", "€22k", "25k a month", "20k per month"]),
                             ("30k_100k", ["€60k", "€45k", "80k a month", "€70k"]), ("over_100k", ["€150k", "200k a month"])):
                if any(w in text for w in words) and o in options:
                    pick = o
                    break
        elif qid == "timeline_stated":
            pick = "this_month" if any(w in text for w in ["this month", "this week", "asap"]) else "this_quarter" if any(w in text for w in ["quarter", "q4", "autumn"]) else "not_stated"
        elif qid == "objection_present":
            pick = "price" if "expensive" in text or "tight" in text else "trust" if "not sure ai" in text or "skeptical" in text else "none"
        elif qid == "same_account":
            pick = options[0] if "hafenblick" in text or "kontor" in text or len(options) == 2 and _h(text[:30]) > 0.7 else "none"
            if pick != "none" and options[0] == "none":
                pick = "none"
        elif qid.startswith("evidence_") or qid == "intent_evidence":
            pick = options[0] if len(options) > 1 and _h(qid + text[:20]) > 0.4 else "none"
        elif qid == "next_best_action":
            pick = "book_call" if "call" in text else "send_case_study_agency" if "agency" in text else "add_to_nurture"
            if pick not in options:
                pick = options[0]
        probs = {o: 0.04 for o in options}
        probs[pick] = 1.0 - 0.04 * (len(options) - 1)
        if probs[pick] < 0.5:
            probs = {o: (0.6 if o == pick else 0.4 / (len(options) - 1)) for o in options}
        return {"type": "choice", "choice": pick, "probabilities": probs, "confidence": round(max(probs.values()), 3)}

    def _score(self, qid: str, n: int, text: str) -> dict[str, Any]:
        if qid == "company_maturity":
            lvl = 0 if any(w in text for w in ["no clients yet", "just starting", "student"]) else 4 if any(w in text for w in ["3,000", "corporate", "enterprise"]) else \
                3 if any(w in text for w in ["12 people", "14 people", "20 people", "25 people", "30 people", "35 people", "11-50"]) else 1 if "solo" in text or "just me" in text else 2
        elif qid == "decision_authority":
            lvl = 3 if any(w in text for w in ["founder", "owner", "ceo", "managing director"]) else 2 if any(w in text for w in ["head of", "director", "coo"]) else 0 if "student" in text else 1
        elif qid == "purchase_intent":
            lvl = 0 if any(w in text for w in ["we help", "thesis", "our platform"]) else 4 if ("call" in text and ("budget" in text or "this month" in text)) else \
                3 if any(w in text for w in ["call", "proposal", "pricing", "demo"]) else 2 if any(w in text for w in ["drowning", "problem", "struggle"]) else 1 if "message" in text and '"message": null' not in text else 0
        else:
            lvl = n // 2
        lvl = max(0, min(n - 1, lvl))
        probs = {str(i): 0.05 for i in range(n)}
        probs[str(lvl)] = 1.0 - 0.05 * (n - 1)
        return {"type": "score", "score": sum(int(k) * v for k, v in probs.items()), "probabilities": probs,
                "legend": {str(i): "" for i in range(n)}, "confidence": round(probs[str(lvl)], 3)}
