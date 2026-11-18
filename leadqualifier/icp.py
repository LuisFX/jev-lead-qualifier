"""The ideal customer profile: the client's answer space, in plain English, as data.

TEACHING NOTE: `save` INSERTs an `icp_version` row. It does not replace. The live
pointer is a single `app_state` row. `data/icp.json` and `data/icp_presets/*.json`
are seeds, not the live store. An unsaved draft POST /api/rescore does not mint a
version (ts-005).

⭐ ENFORCED BY: `tests/test_icp_and_metrics.py` (two saves → two version rows).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from . import config

REQUIRED = ("id", "name", "client", "industries", "personas", "pains", "disqualifiers", "weights", "thresholds", "routes")
TIERS = ("hot", "warm", "nurture", "disqualify", "existing")


class ICPError(ValueError):
    pass


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_presets() -> list[dict[str, Any]]:
    out = []
    for p in sorted(config.ICP_PRESETS_DIR.glob("*.json")):
        d = _read(p)
        out.append({"id": d["id"], "name": d["name"], "client": d.get("client"), "summary": d.get("summary", ""),
                    "industries": list(d["industries"]), "pains": list(d["pains"]), "personas": list(d["personas"])})
    return out


def load_preset(preset_id: str) -> dict[str, Any]:
    path = config.ICP_PRESETS_DIR / f"{preset_id}.json"
    if not path.exists():
        raise ICPError(f"unknown ICP preset: {preset_id}")
    return validate(_read(path))


def load() -> dict[str, Any]:
    """The live ICP from the ledger; seeded from the file or default preset when empty."""
    from .ledger import get_ledger

    live = get_ledger().live_icp()
    if live is not None:
        return validate(live[1])
    if config.ICP_FILE.exists():
        return save(validate(_read(config.ICP_FILE)))
    return save(load_preset(config.DEFAULT_PRESET))


def live_version_id() -> str:
    from .ledger import get_ledger

    vid = get_ledger().live_icp_version_id()
    if vid is None:
        load()
        vid = get_ledger().live_icp_version_id()
    if vid is None:
        raise ICPError("no live ICP version")
    return vid


def save(icp: dict[str, Any]) -> dict[str, Any]:
    """Insert a version; point live at it. Does not replace a prior row."""
    from .ledger import get_ledger

    icp = validate(icp)
    get_ledger().insert_icp_version(icp)
    return icp


def reset() -> dict[str, Any]:
    return save(load_preset(config.DEFAULT_PRESET))


def validate(icp: dict[str, Any]) -> dict[str, Any]:
    icp = copy.deepcopy(icp)
    for key in REQUIRED:
        if key not in icp:
            raise ICPError(f"ICP is missing `{key}`")
    for group in ("industries", "disqualifiers"):
        if not isinstance(icp[group], dict) or not icp[group]:
            raise ICPError(f"`{group}` must be a non-empty object of id -> description")
        for k, v in icp[group].items():
            if not _slug(k):
                raise ICPError(f"`{group}` id `{k}` must be a slug (a-z, 0-9, _)")
            if not isinstance(v, str) or not v.strip():
                raise ICPError(f"`{group}.{k}` needs a one-line description")
    for group in ("personas", "pains"):
        if not isinstance(icp[group], dict) or not icp[group]:
            raise ICPError(f"`{group}` must be a non-empty object")
        for k, v in list(icp[group].items()):
            if not _slug(k):
                raise ICPError(f"`{group}` id `{k}` must be a slug (a-z, 0-9, _)")
            if isinstance(v, str):
                v = {"description": v, "weight": 1.0}
            if not isinstance(v, dict) or not str(v.get("description", "")).strip():
                raise ICPError(f"`{group}.{k}` needs a description")
            v["weight"] = float(v.get("weight", 1.0))
            icp[group][k] = v
    if "other" in icp["industries"] or "other" in icp["personas"]:
        raise ICPError("`other` is added automatically; do not define it")
    icp.setdefault("size_bands", ["solo", "2-10", "11-50", "51-200", "200+"])
    icp.setdefault("target_size_bands", ["2-10", "11-50"])
    icp.setdefault("revenue_bands", ["under_10k", "10k_30k", "30k_100k", "over_100k"])
    icp.setdefault("revenue_band_labels", {b: b.replace("_", " ") for b in icp["revenue_bands"]})
    icp.setdefault("min_revenue_band", icp["revenue_bands"][0])
    if icp["min_revenue_band"] not in icp["revenue_bands"]:
        raise ICPError("`min_revenue_band` must be one of `revenue_bands`")
    icp.setdefault("maturity_fit", [0.05, 0.4, 1.0, 1.0, 0.35])
    if len(icp["maturity_fit"]) != 5:
        raise ICPError("`maturity_fit` needs exactly 5 values (one per maturity level)")
    icp.setdefault("geography", "anywhere")
    icp.setdefault("intent_signals", [])
    icp.setdefault("intent_weights", {"purchase_intent": 0.5, "asks_for_meeting": 0.2, "budget_signal": 0.1, "urgency": 0.1, "timeline": 0.1})
    w = icp["weights"]
    for k in ("industry", "maturity", "persona", "pains"):
        w[k] = float(w.get(k, 0.0))
    if sum(w.values()) <= 0:
        raise ICPError("fit weights must sum to more than 0")
    t = icp["thresholds"]
    defaults = {"fit_hot": 0.62, "fit_warm": 0.42, "intent_hot": 0.6, "intent_warm": 0.25, "disqualifier_p": 0.7,
                "spam_p": 0.8, "dedupe_p": 0.6, "confidence_floor": 0.55, "pain_p": 0.6, "evidence_p": 0.35}
    for k, v in defaults.items():
        t[k] = float(t.get(k, v))
        if not 0.0 <= t[k] <= 1.0:
            raise ICPError(f"threshold `{k}` must be between 0 and 1")
    if t["fit_warm"] > t["fit_hot"] or t["intent_warm"] > t["intent_hot"]:
        raise ICPError("warm thresholds must not exceed hot thresholds")
    for tier in TIERS:
        r = icp["routes"].setdefault(tier, {})
        r.setdefault("label", tier.title())
        r.setdefault("owner", "—")
        r.setdefault("action", "")
    return icp


def _slug(s: str) -> bool:
    return bool(s) and all(c.isalnum() or c == "_" for c in s) and s == s.lower()


def summary_for_state(icp: dict[str, Any]) -> dict[str, Any]:
    """Small, stable ICP description for the UI header (not sent to Jev: criteria carry the ICP)."""
    return {"id": icp["id"], "name": icp["name"], "client": icp["client"], "n_industries": len(icp["industries"]),
            "n_personas": len(icp["personas"]), "n_pains": len(icp["pains"]), "n_disqualifiers": len(icp["disqualifiers"])}
