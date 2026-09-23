"""Accuracy against the hidden gold labels (tier, persona, primary pain), split by confidence."""

from __future__ import annotations

from typing import Any

TIERS = ["hot", "warm", "nurture", "disqualify", "existing"]


def compute_metrics(results: list[dict[str, Any]], gold: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for r in results:
        g = gold.get(r["lead_id"])
        if not g:
            continue
        rows.append((r, g))
    n = len(rows)
    if not n:
        return {"n": 0}

    tier_ok = [(r["tier"] == g["tier"]) for r, g in rows]
    # persona / pain are judged only where gold defines them (not for disqualified or existing accounts)
    persona_rows = [(r, g) for r, g in rows if g.get("persona")]
    pain_rows = [(r, g) for r, g in rows if "primary_pain" in g]
    persona_ok = [r["components"]["persona"]["choice"] == g["persona"] for r, g in persona_rows]
    pain_ok = [(r["primary_pain"] == g["primary_pain"]) for r, g in pain_rows]

    cm = {t: {u: 0 for u in TIERS} for t in TIERS}
    for r, g in rows:
        cm[g["tier"]][r["tier"]] += 1
    per_tier = {}
    for t in TIERS:
        tp = cm[t][t]
        gold_n = sum(cm[t].values())
        pred_n = sum(cm[u][t] for u in TIERS)
        per_tier[t] = {"gold": gold_n, "predicted": pred_n, "correct": tp,
                       "precision": round(tp / pred_n, 3) if pred_n else None, "recall": round(tp / gold_n, 3) if gold_n else None}

    def split(pred: str) -> dict[str, Any]:
        sub = [(r, g) for r, g in rows if (r["confidence"]["needs_review"]) == (pred == "review")]
        return {"n": len(sub), "tier_accuracy": round(sum(r["tier"] == g["tier"] for r, g in sub) / len(sub), 3) if sub else None}

    errors = []
    for r, g in rows:
        if r["tier"] != g["tier"]:
            errors.append({"lead_id": r["lead_id"], "gold": g["tier"], "predicted": r["tier"], "fit": r["fit"], "intent": r["intent"],
                           "needs_review": r["confidence"]["needs_review"], "why": r["why"][:2], "note": g.get("note", "")})
    off_by_one = sum(1 for r, g in rows if r["tier"] != g["tier"] and {r["tier"], g["tier"]} in ({"hot", "warm"}, {"warm", "nurture"}))
    return {
        "n": n,
        "tier_accuracy": round(sum(tier_ok) / n, 3),
        "tier_accuracy_adjacent": round((sum(tier_ok) + off_by_one) / n, 3),
        "persona_accuracy": round(sum(persona_ok) / len(persona_ok), 3) if persona_ok else None,
        "persona_n": len(persona_ok),
        "pain_accuracy": round(sum(pain_ok) / len(pain_ok), 3) if pain_ok else None,
        "pain_n": len(pain_ok),
        "confusion": cm,
        "per_tier": per_tier,
        "by_confidence": {"auto": split("auto"), "review": split("review")},
        "errors": errors,
    }


def format_table(m: dict[str, Any]) -> str:
    if not m.get("n"):
        return "no gold rows"
    lines = [f"tier accuracy {m['tier_accuracy']:.3f} (adjacent {m['tier_accuracy_adjacent']:.3f}) over {m['n']} leads",
             f"persona {m['persona_accuracy']} (n={m['persona_n']})  pain {m['pain_accuracy']} (n={m['pain_n']})",
             f"auto-routed: n={m['by_confidence']['auto']['n']} acc={m['by_confidence']['auto']['tier_accuracy']}  "
             f"review: n={m['by_confidence']['review']['n']} acc={m['by_confidence']['review']['tier_accuracy']}",
             "gold\\pred  " + "  ".join(f"{t[:5]:>5}" for t in TIERS)]
    for t in TIERS:
        lines.append(f"{t[:9]:<10} " + "  ".join(f"{m['confusion'][t][u]:>5}" for u in TIERS))
    for e in m["errors"]:
        lines.append(f"  {e['lead_id']}: gold {e['gold']} → {e['predicted']}  fit {e['fit']} intent {e['intent']}  {'REVIEW' if e['needs_review'] else ''}  {e['why'][0] if e['why'] else ''}")
    return "\n".join(lines)
