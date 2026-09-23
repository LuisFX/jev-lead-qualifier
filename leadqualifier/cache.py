"""Per-question answer cache keyed by lead id and question fingerprint.

Every stored answer carries the fingerprint of the question that produced it. When the ICP
changes, only the questions whose text changed get a new fingerprint, so the next run asks
Jev *just those* for each lead and merges them with the cached answers. Weights and
thresholds are not part of any question, so re-scoring after a threshold change is free.

File layout (``data/cache/answers.json``)::

    {"version": 1, "entries": {"<lead_id>": {"answers": {"<qid>": {"fp": "...", "answer": {...}}},
                                             "requests": [{"qids": [...], "latency_ms": 310, "input_tokens": 2900,
                                                           "output_tokens": 60, "model": "jev-1.13.0", "at": 1726000000.0}]}}}
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

VERSION = 1


class ResultCache:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, Any]] = {}
        self._dirty = False
        if self.path and self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if data.get("version") == VERSION:
                    self._entries = data.get("entries", {})
            except (OSError, ValueError):
                self._entries = {}

    # ------------------------------------------------------------------ reads
    def cached_answers(self, lead_id: str, fingerprints: dict[str, str]) -> dict[str, dict[str, Any]]:
        entry = self._entries.get(lead_id)
        if not entry:
            return {}
        out: dict[str, dict[str, Any]] = {}
        for qid, fp in fingerprints.items():
            stored = entry.get("answers", {}).get(qid)
            if stored and stored.get("fp") == fp:
                out[qid] = stored["answer"]
        return out

    def missing(self, lead_id: str, fingerprints: dict[str, str]) -> list[str]:
        have = self.cached_answers(lead_id, fingerprints)
        return [qid for qid in fingerprints if qid not in have]

    def requests_for(self, lead_id: str) -> list[dict[str, Any]]:
        return list(self._entries.get(lead_id, {}).get("requests", []))

    def has(self, lead_id: str) -> bool:
        return lead_id in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------ writes
    def store(self, lead_id: str, fingerprints: dict[str, str], answers: dict[str, dict[str, Any]],
              request: dict[str, Any] | None = None) -> None:
        with self._lock:
            entry = self._entries.setdefault(lead_id, {"answers": {}, "requests": []})
            for qid, answer in answers.items():
                if qid in fingerprints:
                    entry["answers"][qid] = {"fp": fingerprints[qid], "answer": answer}
            if request:
                entry["requests"].append({**request, "at": request.get("at", time.time())})
                entry["requests"] = entry["requests"][-30:]
            self._dirty = True

    def invalidate(self, question_ids: list[str] | None = None) -> int:
        removed = 0
        with self._lock:
            if question_ids is None:
                removed = sum(len(e.get("answers", {})) for e in self._entries.values())
                self._entries = {}
            else:
                for entry in self._entries.values():
                    for qid in question_ids:
                        if qid in entry.get("answers", {}):
                            del entry["answers"][qid]
                            removed += 1
            self._dirty = True
        return removed

    def clear(self) -> None:
        self.invalidate(None)

    def save(self) -> None:
        if not self.path:
            return
        with self._lock:
            if not self._dirty:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"version": VERSION, "entries": self._entries}, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)
            self._dirty = False

    # ------------------------------------------------------------------ stats
    def stale_report(self, lead_id: str, fingerprints: dict[str, str]) -> dict[str, Any]:
        """How many questions a run would ask for this lead right now."""
        missing = self.missing(lead_id, fingerprints)
        return {"total": len(fingerprints), "cached": len(fingerprints) - len(missing), "missing": missing}

    def history(self, lead_ids: list[str] | None = None) -> dict[str, Any]:
        ids = lead_ids if lead_ids is not None else list(self._entries)
        requests = [r for i in ids for r in self._entries.get(i, {}).get("requests", [])]
        latencies = [float(r.get("latency_ms") or 0.0) for r in requests if r.get("latency_ms")]
        tokens_in = sum(int(r.get("input_tokens") or 0) for r in requests)
        return {"requests": len(requests), "leads": sum(1 for i in ids if i in self._entries), "tokens_in": tokens_in,
                "latency_mean_ms": (sum(latencies) / len(latencies)) if latencies else None}
