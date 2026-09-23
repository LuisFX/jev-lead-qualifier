"""One Jev request per lead; ~30 atomic questions; answers cached per question; tier decided in code.

    Qualifier(icp, crm, playbook, client, cache).score(lead)         -> result dict
    Qualifier.score_many(leads, workers, on_result, on_error, stop)  -> list of results (dataset order)
    Qualifier.rescore(lead)                                          -> result from cache only, never calls Jev

`client` is anything with `.system_one(state, questions) -> JevResponse`; tests inject a fake.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from . import constants as C
from .cache import ResultCache
from .dedupe import shortlist
from .jev import JevClient, JevResponse
from .leads import Lead
from .scoring import assemble, to_generic

log = logging.getLogger("firstread")

ResultHook = Callable[[dict[str, Any]], None]
ErrorHook = Callable[[Lead, Exception], None]


class Qualifier:
    def __init__(self, icp: dict[str, Any], crm: list[dict[str, Any]], playbook: dict[str, Any],
                 client: Any | None = None, cache: ResultCache | None = None):
        self.icp = icp
        self.crm = crm
        self.playbook = playbook
        self._client = client
        self.cache = cache

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = JevClient()
        return self._client

    # ------------------------------------------------------------------ questions for one lead
    def questions_for(self, lead: Lead) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        candidates = shortlist(lead, self.crm)
        sentence_ids = [s["id"] for s in lead.sentences()]
        has_message = bool(lead.message and lead.message.get("text"))
        return C.build_questions(self.icp, sentence_ids=sentence_ids, crm_candidates=candidates, playbook=self.playbook,
                                 has_message=has_message), candidates

    # ------------------------------------------------------------------ one lead
    def score(self, lead: Lead, use_cache: bool = True) -> dict[str, Any]:
        questions, candidates = self.questions_for(lead)
        fps = C.fingerprints(questions)
        cached: dict[str, dict[str, Any]] = {}
        if use_cache and self.cache is not None:
            cached = self.cache.cached_answers(lead.id, fps)
        missing = [qid for qid in fps if qid not in cached]

        fresh: dict[str, dict[str, Any]] = {}
        meta: dict[str, Any] = {"model": C.MODEL, "latency_ms": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                                "n_asked": 0, "n_questions": len(questions), "cached": not missing, "request_id": None}
        if missing:
            state = lead.to_state()
            resp: JevResponse = self.client.system_one(state, {qid: questions[qid] for qid in missing})
            for qid in missing:
                raw = resp.answers.get(qid)
                if raw is None:
                    continue
                fresh[qid] = to_generic(questions[qid], raw)
            meta.update({"model": resp.model, "latency_ms": resp.latency_ms, "input_tokens": resp.input_tokens,
                         "output_tokens": resp.output_tokens, "cost_usd": round(resp.cost_usd, 7), "n_asked": len(missing),
                         "request_id": resp.request_id})
            log.info("scored id=%s asked=%d/%d latency_ms=%s tokens=%s request_id=%s", lead.id, len(missing), len(questions),
                     resp.latency_ms, resp.input_tokens, resp.request_id)
            if self.cache is not None:
                self.cache.store(lead.id, fps, fresh, {"qids": missing, "latency_ms": resp.latency_ms, "input_tokens": resp.input_tokens,
                                                        "output_tokens": resp.output_tokens, "model": resp.model})
        elif self.cache is not None:
            reqs = self.cache.requests_for(lead.id)
            if reqs:
                meta["model"] = reqs[-1].get("model") or C.MODEL
                meta["cached_latency_ms"] = reqs[-1].get("latency_ms")

        answers = {qid: (fresh.get(qid) or cached.get(qid)) for qid in fps}
        answers = {k: v for k, v in answers.items() if v is not None}
        result = assemble(self.icp, lead, answers, candidates, self.playbook)
        result["meta"] = meta
        result["questions_asked"] = missing
        return result

    def rescore(self, lead: Lead) -> dict[str, Any] | None:
        """Re-assemble from cached answers only. Returns None when nothing is cached for this lead."""
        if self.cache is None or not self.cache.has(lead.id):
            return None
        questions, candidates = self.questions_for(lead)
        fps = C.fingerprints(questions)
        cached = self.cache.cached_answers(lead.id, fps)
        if not cached:
            return None
        result = assemble(self.icp, lead, cached, candidates, self.playbook)
        result["meta"] = {"model": C.MODEL, "latency_ms": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "n_asked": 0,
                          "n_questions": len(questions), "cached": True, "stale": [q for q in fps if q not in cached]}
        result["questions_asked"] = []
        return result

    # ------------------------------------------------------------------ many leads
    def score_many(self, leads: list[Lead], workers: int = 4, on_result: ResultHook | None = None, on_error: ErrorHook | None = None,
                   stop: threading.Event | None = None, use_cache: bool = True) -> list[dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {}
            for lead in leads:
                if stop is not None and stop.is_set():
                    break
                futures[pool.submit(self._guarded, lead, stop, use_cache)] = lead
            for fut in as_completed(futures):
                lead = futures[fut]
                res = fut.result()
                if isinstance(res, Exception):
                    if on_error:
                        on_error(lead, res)
                    else:
                        log.warning("score failed id=%s: %s", lead.id, res)
                    continue
                if res is None:
                    continue
                by_id[lead.id] = res
                if on_result:
                    on_result(res)
        if self.cache is not None:
            self.cache.save()
        return [by_id[l.id] for l in leads if l.id in by_id]

    def _guarded(self, lead: Lead, stop: threading.Event | None, use_cache: bool) -> Any:
        if stop is not None and stop.is_set():
            return None
        try:
            return self.score(lead, use_cache=use_cache)
        except Exception as exc:  # reported per lead; the run continues
            return exc

    # ------------------------------------------------------------------ cache introspection
    def stale_summary(self, leads: list[Lead]) -> dict[str, Any]:
        """For the ICP editor: how many questions a run would ask now, per lead and in total."""
        if self.cache is None:
            return {"leads": len(leads), "cached_leads": 0, "questions_to_ask": 0, "questions_total": 0}
        to_ask = total = cached_leads = 0
        stale_ids: dict[str, int] = {}
        for lead in leads:
            questions, _ = self.questions_for(lead)
            fps = C.fingerprints(questions)
            missing = self.cache.missing(lead.id, fps)
            total += len(fps)
            to_ask += len(missing)
            if self.cache.has(lead.id):
                cached_leads += 1
            for q in missing:
                stale_ids[q] = stale_ids.get(q, 0) + 1
        return {"leads": len(leads), "cached_leads": cached_leads, "questions_to_ask": to_ask, "questions_total": total,
                "stale_question_ids": sorted(stale_ids, key=lambda k: -stale_ids[k])[:40]}


def run_totals(results: list[dict[str, Any]], errors: int, elapsed_s: float) -> dict[str, Any]:
    n = len(results)
    asked = [r for r in results if r["meta"].get("n_asked")]
    tokens = sum(r["meta"].get("input_tokens", 0) for r in results)
    cost = sum(r["meta"].get("cost_usd", 0.0) for r in results)
    lat = [r["meta"]["latency_ms"] for r in asked if r["meta"].get("latency_ms")]
    tiers = {t: sum(1 for r in results if r["tier"] == t) for t in ("hot", "warm", "nurture", "disqualify", "existing")}
    review = sum(1 for r in results if r["confidence"]["needs_review"])
    return {
        "leads": n, "errors": errors, "elapsed_s": round(elapsed_s, 2), "requests": len(asked), "from_cache": n - len(asked),
        "input_tokens": tokens, "cost_usd": round(cost, 6),
        "cost_per_1000_usd": round(cost / len(asked) * 1000, 4) if asked else None,
        "latency_mean_ms": round(sum(lat) / len(lat)) if lat else None,
        "latency_p50_ms": sorted(lat)[len(lat) // 2] if lat else None,
        "tiers": tiers, "needs_review": review, "auto_routed": n - review,
        "sdr_minutes_saved": n * C.SDR_MINUTES_PER_LEAD,
        "questions_per_lead": round(sum(r["meta"].get("n_questions", 0) for r in results) / n, 1) if n else 0,
    }
