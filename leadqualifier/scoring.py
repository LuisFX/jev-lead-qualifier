"""Turn one lead's answers into fit, intent, tier, route and a next action. Pure code.

Jev answers the atomic questions; this module owns every weight, threshold and rule:

* `fit`     = weighted mean of industry fit, maturity fit, persona fit and pain fit (0..1)
* `intent`  = weighted mean of purchase-intent level, meeting ask, budget, urgency, timeline
* tier      = matrix over (fit band, intent band), overridden by disqualifiers, spam and CRM matches
* gating    = low confidence or a borderline score marks the lead `needs_review`
* route     = the ICP's route for the tier (+ the CRM owner for existing accounts)
* action    = Jev's playbook Choice, constrained to the actions allowed for the tier

Changing any number here (or in `icp.json`) re-scores every cached lead with zero API calls.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .leads import Lead

TIER_ORDER = ["hot", "warm", "nurture", "disqualify", "existing"]
TIMELINE_VALUE = {"this_month": 1.0, "this_quarter": 0.6, "later": 0.2, "not_stated": 0.0}
TIER_MATRIX = {
    ("high", "high"): "hot",
    ("high", "mid"): "warm",
    ("high", "low"): "nurture",
    ("mid", "high"): "warm",
    ("mid", "mid"): "warm",
    ("mid", "low"): "nurture",
    ("low", "high"): "warm",  # strong intent, weak fit: a human decides, flagged
    ("low", "mid"): "nurture",
    ("low", "low"): "nurture",
}
BORDERLINE = 0.03  # a score this close to a tier threshold is flagged for a human
FALLBACK_ACTION = {"hot": "book_call", "warm": "ask_qualifying_question_pain", "nurture": "add_to_nurture",
                   "disqualify": "decline_politely", "existing": "route_to_account_owner"}
DQ_LABELS = {"is_vendor_pitch": "vendor pitch", "is_student_or_jobseeker": "student or job seeker",
             "is_competitor": "competitor", "is_spam_or_automated": "spam or automated"}


# --------------------------------------------------------------------------- answer accessors


def noul(answers: dict[str, Any], qid: str, default: float = 0.0) -> float:
    a = answers.get(qid)
    if not a:
        return default
    return float(a.get("p", a.get("noul", default)))


def choice(answers: dict[str, Any], qid: str) -> tuple[str | None, float, dict[str, float]]:
    a = answers.get(qid)
    if not a:
        return None, 0.0, {}
    probs = {str(k): float(v) for k, v in (a.get("probabilities") or {}).items()}
    return a.get("choice"), float(a.get("confidence", 0.0)), probs


def score(answers: dict[str, Any], qid: str, n_levels: int) -> tuple[float, float, list[float]]:
    a = answers.get(qid)
    if not a:
        return 0.0, 0.0, [0.0] * n_levels
    probs = a.get("probabilities") or {}
    dist = [float(probs.get(str(i), probs.get(i, 0.0))) for i in range(n_levels)]
    return float(a.get("score", 0.0)), float(a.get("confidence", 0.0)), dist


def to_generic(question: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    """Raw API answer -> compact JSON-safe dict the scorer and UI consume."""
    t = question["type"]
    if t == "noul":
        return {"type": "noul", "p": round(float(answer.get("noul", 0.0)), 4)}
    probs = {str(k): round(float(v), 4) for k, v in (answer.get("probabilities") or {}).items()}
    if t == "choice":
        return {"type": "choice", "choice": str(answer.get("choice")), "confidence": round(float(answer.get("confidence", 0.0)), 4), "probabilities": probs}
    s = float(answer.get("score", 0.0))
    return {"type": "score", "score": round(s, 4), "level": int(round(s)), "confidence": round(float(answer.get("confidence", 0.0)), 4),
            "probabilities": probs, "n_levels": len(question.get("criteria") or [])}


# --------------------------------------------------------------------------- components


def fit_components(icp: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    ind_choice, ind_conf, ind_probs = choice(answers, "industry")
    industry_fit = 1.0 - ind_probs.get("other", 0.0) if ind_probs else 0.0

    _, mat_conf, mat_dist = score(answers, "company_maturity", 5)
    mat_fit_vec = icp.get("maturity_fit", [0.05, 0.4, 1.0, 1.0, 0.35])
    maturity_fit = sum(p * f for p, f in zip(mat_dist, mat_fit_vec)) if any(mat_dist) else 0.0
    maturity_level = max(range(5), key=lambda i: mat_dist[i]) if any(mat_dist) else None

    per_choice, per_conf, per_probs = choice(answers, "persona")
    persona_fit = sum(per_probs.get(k, 0.0) * float(v.get("weight", 1.0)) for k, v in icp["personas"].items())
    auth_score, auth_conf, _ = score(answers, "decision_authority", 4)

    pains: dict[str, float] = {pid: noul(answers, f"pain_{pid}") for pid in icp["pains"]}
    weighted = {pid: p * float(icp["pains"][pid].get("weight", 1.0)) for pid, p in pains.items()}
    if weighted:
        top = max(weighted.values())
        rest = sum(weighted.values()) - top
        pain_fit = min(1.0, top + 0.2 * rest)
    else:
        pain_fit = 0.0
    primary_pain = max(pains, key=pains.get) if pains else None
    if primary_pain is not None and pains[primary_pain] < icp["thresholds"]["pain_p"]:
        primary_pain = None

    return {
        "industry": {"choice": ind_choice, "confidence": round(ind_conf, 3), "fit": round(industry_fit, 3), "probabilities": ind_probs},
        "maturity": {"level": maturity_level, "confidence": round(mat_conf, 3), "fit": round(maturity_fit, 3), "distribution": [round(x, 3) for x in mat_dist]},
        "persona": {"choice": per_choice, "confidence": round(per_conf, 3), "fit": round(persona_fit, 3), "probabilities": per_probs,
                    "authority": round(auth_score, 2), "authority_confidence": round(auth_conf, 3)},
        "pains": {"scores": {k: round(v, 3) for k, v in pains.items()}, "fit": round(pain_fit, 3), "primary": primary_pain},
    }


def composite_fit(icp: dict[str, Any], comps: dict[str, Any], answers: dict[str, Any]) -> tuple[float, list[str], dict[str, float]]:
    w = icp["weights"]
    total_w = sum(w.values()) or 1.0
    contrib = {
        "industry": w["industry"] * comps["industry"]["fit"] / total_w,
        "maturity": w["maturity"] * comps["maturity"]["fit"] / total_w,
        "persona": w["persona"] * comps["persona"]["fit"] / total_w,
        "pains": w["pains"] * comps["pains"]["fit"] / total_w,
    }
    fit = sum(contrib.values())
    penalties: list[str] = []
    floor = icp["thresholds"]["confidence_floor"]
    band, band_conf, _ = choice(answers, "size_band_stated")
    if band and band != "not_stated" and band_conf >= floor and band not in icp["target_size_bands"]:
        fit *= 0.8
        penalties.append(f"stated size {band} is outside the target bands")
    if noul(answers, "geo_fit", 1.0) < 0.3:
        fit *= 0.85
        penalties.append("stated location is outside the ICP region")
    return max(0.0, min(1.0, fit)), penalties, {k: round(v, 3) for k, v in contrib.items()}


def composite_intent(icp: dict[str, Any], answers: dict[str, Any], has_message: bool) -> tuple[float, dict[str, float]]:
    iw = icp.get("intent_weights", {})
    total_w = sum(iw.values()) or 1.0
    pi_score, _, _ = score(answers, "purchase_intent", 5)
    _, _, tl_probs = choice(answers, "timeline_stated")
    timeline = sum(tl_probs.get(k, 0.0) * v for k, v in TIMELINE_VALUE.items())
    parts = {
        "purchase_intent": pi_score / 4.0,
        "asks_for_meeting": noul(answers, "asks_for_meeting"),
        "budget_signal": noul(answers, "budget_signal"),
        "urgency": noul(answers, "urgency"),
        "timeline": timeline,
    }
    if not has_message:  # a profile cannot ask for a meeting: only the intent level and news-derived signals count
        parts["asks_for_meeting"] = 0.0
        parts["urgency"] = 0.0
    contrib = {k: float(iw.get(k, 0.0)) * v / total_w for k, v in parts.items()}
    return max(0.0, min(1.0, sum(contrib.values()))), {k: round(v, 3) for k, v in contrib.items()}


# --------------------------------------------------------------------------- overrides


def disqualifiers(icp: dict[str, Any], answers: dict[str, Any]) -> list[dict[str, Any]]:
    t = icp["thresholds"]
    out: list[dict[str, Any]] = []
    for dq_id, desc in icp["disqualifiers"].items():
        p = noul(answers, f"dq_{dq_id}")
        if p >= t["disqualifier_p"]:
            out.append({"id": dq_id, "p": round(p, 3), "label": dq_id.replace("_", " "), "detail": desc})
    fired_words = " ".join(d["id"] for d in out)
    for qid, word in (("is_vendor_pitch", "vendor"), ("is_student_or_jobseeker", "student"), ("is_competitor", "competitor")):
        p = noul(answers, qid)
        if p >= t["disqualifier_p"] and word not in fired_words:  # an ICP disqualifier about the same thing already fired
            out.append({"id": qid, "p": round(p, 3), "label": DQ_LABELS[qid], "detail": f"P({DQ_LABELS[qid]}) = {p:.2f}"})
    p_spam = noul(answers, "is_spam_or_automated")
    if p_spam >= t["spam_p"]:
        out.append({"id": "is_spam_or_automated", "p": round(p_spam, 3), "label": "spam or automated", "detail": f"P(spam) = {p_spam:.2f}"})
    rev, rev_conf, _ = choice(answers, "revenue_band_stated")
    bands = icp["revenue_bands"]
    if rev in bands and rev_conf >= t["confidence_floor"] and bands.index(rev) < bands.index(icp["min_revenue_band"]):
        out.append({"id": "revenue_below_minimum", "p": round(rev_conf, 3), "label": "below minimum revenue band",
                    "detail": f"stated {icp['revenue_band_labels'].get(rev, rev)}; minimum is {icp['revenue_band_labels'].get(icp['min_revenue_band'])}"})
    # dedupe: keep unique ids
    seen: set[str] = set()
    uniq = []
    for d in out:
        if d["id"] not in seen:
            seen.add(d["id"])
            uniq.append(d)
    return uniq


def existing_account(icp: dict[str, Any], answers: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates or "same_account" not in answers:
        return None
    ch, conf, probs = choice(answers, "same_account")
    if not ch or ch == "none":
        return None
    p = probs.get(ch, 0.0)
    if p < icp["thresholds"]["dedupe_p"]:
        return None
    cand = next((c for c in candidates if c["id"] == ch), None)
    if not cand:
        return None
    return {**cand, "p": round(p, 3), "confidence": round(conf, 3)}


# --------------------------------------------------------------------------- tier, gating, route


def band(value: float, hot: float, warm: float) -> str:
    return "high" if value >= hot else "mid" if value >= warm else "low"


def tier_from_matrix(icp: dict[str, Any], fit: float, intent: float) -> str:
    t = icp["thresholds"]
    return TIER_MATRIX[(band(fit, t["fit_hot"], t["fit_warm"]), band(intent, t["intent_hot"], t["intent_warm"]))]


def next_slots(now: datetime | None = None) -> list[str]:
    """Two founder call slots: next Tuesday 11:00 and Thursday 15:00 (CET). Deterministic given `now`."""
    now = now or datetime.now()
    out = []
    for weekday, hour in ((1, 11), (3, 15)):
        days = (weekday - now.weekday()) % 7 or 7
        d = (now + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
        out.append(d.strftime("%a %d %b · %H:%M CET"))
    return out


def gate(icp: dict[str, Any], tier: str, fit: float, intent: float, comps: dict[str, Any], answers: dict[str, Any],
         dq: list[dict[str, Any]], account: dict[str, Any] | None) -> dict[str, Any]:
    t = icp["thresholds"]
    reasons: list[str] = []
    floor = t["confidence_floor"]
    _, pi_conf, _ = score(answers, "purchase_intent", 5)
    confs = {"industry": comps["industry"]["confidence"], "purchase_intent": pi_conf}
    if tier in ("hot", "warm", "nurture"):
        for k, v in confs.items():
            if v < floor:
                reasons.append(f"{k.replace('_', ' ')} confidence {v:.2f} below floor {floor:.2f}")
        for name, value, hot_t, warm_t in (("fit", fit, t["fit_hot"], t["fit_warm"]), ("intent", intent, t["intent_hot"], t["intent_warm"])):
            for thr in (hot_t, warm_t):
                if abs(value - thr) < BORDERLINE:
                    reasons.append(f"{name} {value:.2f} is within {BORDERLINE:.2f} of the {thr:.2f} threshold")
        if band(fit, t["fit_hot"], t["fit_warm"]) == "low" and band(intent, t["intent_hot"], t["intent_warm"]) == "high":
            reasons.append("strong intent but weak ICP fit: a human should decide")
    if tier == "disqualify" and dq and max(d["p"] for d in dq) < 0.85:
        reasons.append(f"strongest disqualifier only {max(d['p'] for d in dq):.2f}: confirm before declining")
    if tier == "existing" and account and account["p"] < 0.8:
        reasons.append(f"CRM match probability {account['p']:.2f}: confirm the account")
    if noul(answers, "contains_pii_request") >= 0.7:
        reasons.append("message asks for personal data or credentials: security review before any reply")
    needs_review = bool(reasons)
    min_conf = min(confs.values()) if confs else 0.0
    label = "low" if needs_review else "high" if min_conf >= 0.75 else "medium"
    return {"label": label, "needs_review": needs_review, "reasons": reasons, "min_confidence": round(min_conf, 3)}


def pick_action(icp: dict[str, Any], tier: str, answers: dict[str, Any], playbook: dict[str, Any], lead: Lead,
                comps: dict[str, Any], account: dict[str, Any] | None) -> dict[str, Any]:
    ch, conf, probs = choice(answers, "next_best_action")
    allowed = [k for k, v in playbook.items() if tier in v.get("tiers", [])]
    if tier in ("disqualify", "existing") or not allowed:
        action_id = FALLBACK_ACTION[tier]
        source = "rule"
    else:
        ranked = sorted(((probs.get(k, 0.0), k) for k in allowed), reverse=True)
        action_id = ranked[0][1] if ranked and ranked[0][0] > 0 else FALLBACK_ACTION[tier]
        source = "jev" if action_id == ch else "jev-constrained"
    entry = playbook.get(action_id, {"label": action_id, "text": ""})
    first_name = (lead.person_name or "there").split()[0]
    industry_label = (comps["industry"]["choice"] or "your").replace("_", " ")
    text = entry.get("text", "").format(first_name=first_name, company_name=lead.company_name, industry_label=industry_label,
                                        account_name=(account or {}).get("name", ""), account_owner=(account or {}).get("owner", ""))
    return {"id": action_id, "label": entry.get("label", action_id), "text": text, "source": source,
            "jev_choice": ch, "jev_confidence": round(conf, 3), "probabilities": probs}


def move_up(icp: dict[str, Any], tier: str, fit: float, intent: float, comps: dict[str, Any], intent_parts: dict[str, float],
            dq: list[dict[str, Any]], answers: dict[str, Any]) -> str:
    t, w, iw = icp["thresholds"], icp["weights"], icp.get("intent_weights", {})
    if tier == "hot":
        return "Already the top tier. Keep the founder slot warm; nothing else to unlock."
    if tier == "existing":
        return "Not a new lead: the account owner takes it from here."
    if tier == "disqualify":
        rev = next((d for d in dq if d["id"] == "revenue_below_minimum"), None)
        if rev and len(dq) == 1:
            return f"Only the revenue gate blocks this lead ({rev['detail']}). A stated revenue at or above the minimum band would re-open it."
        return "Disqualified by " + ", ".join(d["label"] for d in dq) + ". A different sender or company would be needed, not a better message."
    total_w = sum(w.values()) or 1.0
    total_iw = sum(iw.values()) or 1.0
    levers: list[str] = []
    fit_target = t["fit_hot"] if tier == "warm" else t["fit_warm"]
    intent_target = t["intent_hot"] if tier == "warm" else t["intent_warm"]
    fit_gap = max(0.0, fit_target - fit)
    intent_gap = max(0.0, intent_target - intent)
    if intent_gap > 0:
        gain_meet = iw.get("asks_for_meeting", 0) * (1 - intent_parts.get("asks_for_meeting", 0) * total_iw / max(iw.get("asks_for_meeting", 1e-9), 1e-9)) / total_iw
        if noul(answers, "asks_for_meeting") < 0.5:
            levers.append(f"a reply that asks for a call adds up to +{gain_meet:.2f} intent")
        tl, _, _ = choice(answers, "timeline_stated")
        if tl in (None, "not_stated", "later"):
            levers.append(f"a stated timeline ('this quarter') adds up to +{iw.get('timeline', 0) * 0.6 / total_iw:.2f}")
        if noul(answers, "budget_signal") < 0.5:
            levers.append(f"a budget signal adds +{iw.get('budget_signal', 0) / total_iw:.2f}")
    if fit_gap > 0:
        if comps["persona"]["fit"] < 0.6:
            levers.append(f"reaching a decision-maker adds up to +{w['persona'] * (1 - comps['persona']['fit']) / total_w:.2f} fit (persona is '{comps['persona']['choice']}')")
        if comps["pains"]["fit"] < 0.6:
            levers.append(f"a stated qualifying pain adds up to +{w['pains'] * (1 - comps['pains']['fit']) / total_w:.2f} fit")
        if comps["industry"]["fit"] < 0.6:
            levers.append("the industry reads as outside the ICP; only a different company profile changes that")
    nxt = "Hot" if tier == "warm" else "Warm"
    need = []
    if fit_gap > 0:
        need.append(f"fit {fit:.2f} → {fit_target:.2f}")
    if intent_gap > 0:
        need.append(f"intent {intent:.2f} → {intent_target:.2f}")
    head = f"To reach {nxt}: " + (" and ".join(need) if need else "one of the two scores must cross its threshold") + "."
    return head + (" " + "; ".join(levers[:3]) + "." if levers else "")


def checklist(icp: dict[str, Any], comps: dict[str, Any], answers: dict[str, Any], dq: list[dict[str, Any]]) -> list[dict[str, Any]]:
    t = icp["thresholds"]
    items: list[dict[str, Any]] = []
    ind = comps["industry"]
    items.append({"label": "Industry in ICP", "state": "ok" if ind["choice"] != "other" and ind["fit"] >= 0.6 else "fail" if ind["fit"] < 0.35 else "warn",
                  "detail": f"{(ind['choice'] or '—').replace('_', ' ')} · confidence {ind['confidence']:.2f}"})
    band_c, band_conf, _ = choice(answers, "size_band_stated")
    if band_c in (None, "not_stated") or band_conf < t["confidence_floor"]:
        items.append({"label": "Team size", "state": "unknown", "detail": "not stated — never guessed"})
    else:
        items.append({"label": "Team size", "state": "ok" if band_c in icp["target_size_bands"] else "warn", "detail": f"stated {band_c}"})
    rev, rev_conf, _ = choice(answers, "revenue_band_stated")
    if rev in (None, "not_stated") or rev_conf < t["confidence_floor"]:
        items.append({"label": "Revenue band", "state": "unknown", "detail": "not stated — never guessed"})
    else:
        below = icp["revenue_bands"].index(rev) < icp["revenue_bands"].index(icp["min_revenue_band"])
        items.append({"label": "Revenue band", "state": "fail" if below else "ok", "detail": f"stated {icp['revenue_band_labels'].get(rev, rev)}"})
    geo = noul(answers, "geo_fit", 1.0)
    items.append({"label": "Geography", "state": "ok" if geo >= 0.5 else "fail", "detail": f"P(in region) {geo:.2f}"})
    per = comps["persona"]
    items.append({"label": "Buyer persona", "state": "ok" if per["fit"] >= 0.6 else "warn" if per["fit"] >= 0.3 else "fail",
                  "detail": f"{(per['choice'] or '—').replace('_', ' ')} · authority {per['authority']:.1f}/3"})
    lvl = comps["maturity"]["level"]
    items.append({"label": "Company maturity", "state": "ok" if comps["maturity"]["fit"] >= 0.6 else "warn",
                  "detail": f"level {lvl if lvl is not None else '—'} · fit {comps['maturity']['fit']:.2f}"})
    pains = comps["pains"]
    n_pains = sum(1 for p in pains["scores"].values() if p >= t["pain_p"])
    items.append({"label": "Qualifying pain", "state": "ok" if n_pains else "warn",
                  "detail": f"{n_pains} detected" + (f" · primary {pains['primary'].replace('_', ' ')}" if pains["primary"] else "")})
    items.append({"label": "No disqualifier", "state": "fail" if dq else "ok", "detail": ", ".join(d["label"] for d in dq) or "none fired"})
    return items


def evidence(icp: dict[str, Any], answers: dict[str, Any], pains: dict[str, float]) -> dict[str, Any]:
    t = icp["thresholds"]
    out: dict[str, Any] = {"pains": {}, "intent": None}
    for pid, p in pains.items():
        ch, conf, probs = choice(answers, f"evidence_{pid}")
        if ch and ch != "none" and probs.get(ch, 0.0) >= t["evidence_p"] and p >= t["pain_p"]:
            out["pains"][pid] = {"sentence": ch, "p": round(probs.get(ch, 0.0), 3), "pain_p": round(p, 3)}
    ch, conf, probs = choice(answers, "intent_evidence")
    if ch and ch != "none" and probs.get(ch, 0.0) >= t["evidence_p"]:
        out["intent"] = {"sentence": ch, "p": round(probs.get(ch, 0.0), 3)}
    return out


# --------------------------------------------------------------------------- assemble


def assemble(icp: dict[str, Any], lead: Lead, answers: dict[str, Any], candidates: list[dict[str, Any]],
             playbook: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    comps = fit_components(icp, answers)
    fit, penalties, fit_contrib = composite_fit(icp, comps, answers)
    has_message = bool(lead.message and lead.message.get("text"))
    intent, intent_contrib = composite_intent(icp, answers, has_message)
    dq = disqualifiers(icp, answers)
    account = existing_account(icp, answers, candidates)
    spam = any(d["id"] == "is_spam_or_automated" for d in dq)

    if spam:
        tier, why = "disqualify", ["spam or automated message"]
    elif account:
        tier, why = "existing", [f"matches CRM account {account['name']} (P {account['p']:.2f}) · status {account.get('status', '—')}"]
    elif dq:
        tier, why = "disqualify", [f"{d['label']} ({d['p']:.2f})" for d in dq]
    else:
        tier = tier_from_matrix(icp, fit, intent)
        t = icp["thresholds"]
        why = [f"fit {fit:.2f} ({band(fit, t['fit_hot'], t['fit_warm'])}) × intent {intent:.2f} ({band(intent, t['intent_hot'], t['intent_warm'])})"]
        why += penalties
        obj_c, obj_p, _ = choice(answers, "objection_present")
        if tier == "warm" and obj_c == "timing" and obj_p >= 0.6:
            tier = "nurture"
            why.append(f"timing objection ({obj_p:.2f}): parked on the nurture track until they come back")

    conf = gate(icp, tier, fit, intent, comps, answers, dq, account)
    route = dict(icp["routes"].get(tier, {}))
    route["tier"] = tier
    if tier == "existing" and account:
        route["owner"] = account.get("owner") or route.get("owner")
        route["label"] = f"Account owner · {account.get('status', 'account')}"
    if tier == "hot":
        route["slots"] = next_slots(now)
    if conf["needs_review"]:
        route["hold"] = True
        route["hold_reason"] = "confirm before routing: " + conf["reasons"][0]
    action = pick_action(icp, tier, answers, playbook, lead, comps, account)
    obj, obj_conf, _ = choice(answers, "objection_present")
    tl, tl_conf, _ = choice(answers, "timeline_stated")
    flags: list[dict[str, str]] = []
    if noul(answers, "contains_pii_request") >= 0.7:
        flags.append({"id": "pii_request", "severity": "warn", "text": "Asks for personal data or credentials — security review, no automatic reply."})
    if obj and obj != "none" and obj_conf >= 0.5:
        flags.append({"id": f"objection_{obj}", "severity": "info", "text": f"Objection raised: {obj}. The sequence should address it first."})
    if not has_message:
        flags.append({"id": "no_message", "severity": "info", "text": "No message: intent comes from news and bio only; the lead is scored on fit."})
    for p in penalties:
        flags.append({"id": "fit_penalty", "severity": "info", "text": p[0].upper() + p[1:] + "."})

    return {
        "lead_id": lead.id,
        "tier": tier,
        "why": why,
        "fit": round(fit, 3),
        "intent": round(intent, 3),
        "fit_contrib": fit_contrib,
        "intent_contrib": intent_contrib,
        "components": comps,
        "primary_pain": comps["pains"]["primary"],
        "disqualifiers": dq,
        "existing_account": account,
        "dedupe": {"candidates": candidates, "verdict": account["id"] if account else ("none" if candidates else None)},
        "confidence": conf,
        "route": route,
        "next_action": action,
        "timeline": {"choice": tl, "confidence": round(tl_conf, 3)},
        "objection": {"choice": obj, "confidence": round(obj_conf, 3)},
        "evidence": evidence(icp, answers, comps["pains"]["scores"]),
        "checklist": checklist(icp, comps, answers, dq),
        "move_up": move_up(icp, tier, fit, intent, comps, intent_contrib, dq, answers),
        "flags": flags,
        "answers": answers,
    }
