"""FastAPI app: serves the single-page UI and a small JSON API. The API key stays server-side.

  GET  /                            the UI
  GET  /api/status                  client, ICP summary, counts, key presence (never the key), cache stats
  GET  /api/leads                   all leads (inputs only)
  GET  /api/leads/{id}              one lead + its result from cache (zero Jev calls)
  GET  /api/results                 every cached result re-scored under the live ICP (zero Jev calls) + totals + metrics
  GET  /api/run/stream              ?force=1&ids=a,b   SSE: start, result*, progress*, failed*, done | fatal
  POST /api/run/{job_id}/cancel
  POST /api/score/{id}              score one lead now (one Jev request unless fully cached)
  POST /api/rescore                 {icp} -> results under an unsaved ICP, cache only; reports what a run would re-ask
  GET  /api/icp  PUT /api/icp       the live ICP; PUT validates, saves, reports stale questions
  POST /api/icp/reset               back to the default preset
  GET  /api/icp/presets             the presets;  POST /api/icp/presets/{id} loads one as the live ICP
  GET  /api/questions               the question set for a sample lead (read-only)
  GET  /api/playbook  /api/crm      the fixed playbook, the CRM accounts
  GET  /api/metrics                 accuracy vs gold from cached results (default ICP only)
  POST /api/apollo/enrich           {domain} -> optional Apollo organization (flagged, cached)
  GET  /api/jev/test                one tiny request proves the key works
  DELETE /api/cache                 forget every cached answer
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import apollo, config, icp as icp_mod
from . import constants as C
from .cache import ResultCache
from .jev import JevClient, JevError
from .leads import Lead, load_crm, load_gold, load_leads, load_playbook
from .metrics import compute_metrics
from .pipeline import Qualifier, run_totals

log = logging.getLogger("firstread")
FAKE_MODE = os.environ.get("FIRSTREAD_FAKE", "").strip().lower() in ("1", "true", "yes")


class AppState:
    def __init__(self) -> None:
        self.icp: dict[str, Any] | None = None
        self.leads: list[Lead] | None = None
        self.crm: list[dict[str, Any]] | None = None
        self.playbook: dict[str, Any] | None = None
        self.gold: dict[str, Any] | None = None
        self.cache: ResultCache | None = None
        self.client: Any | None = None
        self.jobs: dict[str, "RunJob"] = {}
        self.lock = threading.Lock()

    def reset(self) -> None:
        self.__init__()

    def get_icp(self) -> dict[str, Any]:
        if self.icp is None:
            self.icp = icp_mod.load()
        return self.icp

    def get_leads(self) -> list[Lead]:
        if self.leads is None:
            self.leads = load_leads()
        return self.leads

    def lead(self, lead_id: str) -> Lead:
        for l in self.get_leads():
            if l.id == lead_id:
                return l
        raise HTTPException(404, f"unknown lead {lead_id}")

    def get_crm(self) -> list[dict[str, Any]]:
        if self.crm is None:
            self.crm = load_crm()
        return self.crm

    def get_playbook(self) -> dict[str, Any]:
        if self.playbook is None:
            self.playbook = load_playbook()
        return self.playbook

    def get_gold(self) -> dict[str, Any]:
        if self.gold is None:
            self.gold = load_gold()
        return self.gold

    def get_cache(self) -> ResultCache:
        if self.cache is None:
            self.cache = ResultCache(config.RESULT_CACHE_FILE)
        return self.cache

    def get_client(self) -> Any:
        if self.client is None:
            if FAKE_MODE:
                from .fake_client import FakeClient
                self.client = FakeClient(latency_s=0.15)
            else:
                if config.typesafe_api_key() is None:
                    raise HTTPException(503, config.MISSING_KEY_MESSAGE)
                try:
                    self.client = JevClient()
                except JevError as exc:
                    raise HTTPException(503, str(exc))
        return self.client

    def qualifier(self, icp: dict[str, Any] | None = None, with_client: bool = True) -> Qualifier:
        return Qualifier(icp or self.get_icp(), self.get_crm(), self.get_playbook(),
                         client=self.get_client() if with_client else None, cache=self.get_cache())


STATE = AppState()
app = FastAPI(title="First Read", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(config.WEB_DIR)), name="static")


def set_client(client: Any | None) -> None:
    """Test hook: inject a fake Jev client and drop all cached state."""
    STATE.reset()
    STATE.client = client


# --------------------------------------------------------------------------- pages


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(config.WEB_DIR / "index.html"))


# --------------------------------------------------------------------------- status & data


@app.get("/api/status")
def status() -> dict[str, Any]:
    icp = STATE.get_icp()
    leads = STATE.get_leads()
    cache = STATE.get_cache()
    return {
        "app": "First Read", "model": C.MODEL, "price_per_m": C.PRICE_PER_M_INPUT_TOKENS, "sdr_minutes_per_lead": C.SDR_MINUTES_PER_LEAD,
        "jev_key": config.typesafe_api_key() is not None or FAKE_MODE or STATE.client is not None, "fake": FAKE_MODE,
        "icp": icp_mod.summary_for_state(icp), "default_icp": config.DEFAULT_PRESET, "leads": len(leads),
        "shapes": {s: sum(1 for l in leads if l.shape == s) for s in ("message", "profile", "bio")},
        "crm_accounts": len(STATE.get_crm()), "has_gold": bool(STATE.get_gold()) and icp["id"] == config.DEFAULT_PRESET,
        "cache": {"leads": len(cache), **cache.history()}, "apollo": apollo.status(), "workers": config.workers(),
    }


@app.get("/api/leads")
def leads() -> list[dict[str, Any]]:
    return [l.to_json() for l in STATE.get_leads()]


@app.get("/api/leads/{lead_id}")
def lead_detail(lead_id: str) -> dict[str, Any]:
    lead = STATE.lead(lead_id)
    q = STATE.qualifier(with_client=False)
    result = q.rescore(lead)
    questions, _ = q.questions_for(lead)
    return {"lead": lead.to_json(), "result": result, "questions": C.describe_questions(questions), "state": lead.to_state()}


def _results_under(icp: dict[str, Any]) -> list[dict[str, Any]]:
    q = STATE.qualifier(icp, with_client=False)
    out = []
    for lead in STATE.get_leads():
        r = q.rescore(lead)
        if r is not None:
            out.append(r)
    return out


def _metrics(results: list[dict[str, Any]], icp: dict[str, Any]) -> dict[str, Any] | None:
    if icp["id"] != config.DEFAULT_PRESET or not STATE.get_gold():
        return None
    return compute_metrics(results, STATE.get_gold())


@app.get("/api/results")
def results() -> dict[str, Any]:
    icp = STATE.get_icp()
    res = _results_under(icp)
    return {"results": res, "totals": run_totals(res, 0, 0.0), "metrics": _metrics(res, icp), "icp": icp_mod.summary_for_state(icp),
            "stale": STATE.qualifier(with_client=False).stale_summary(STATE.get_leads())}


@app.get("/api/metrics")
def metrics() -> dict[str, Any]:
    icp = STATE.get_icp()
    m = _metrics(_results_under(icp), icp)
    if m is None:
        raise HTTPException(404, "no gold labels for this ICP")
    return m


# --------------------------------------------------------------------------- run (SSE)


class RunJob:
    def __init__(self, force: bool, ids: list[str] | None):
        self.id = uuid.uuid4().hex[:10]
        self.force, self.ids = force, ids
        self.queue: "queue.Queue[tuple[str, dict[str, Any]]]" = queue.Queue()
        self.stop = threading.Event()
        self.finished = threading.Event()
        self.results: list[dict[str, Any]] = []
        self.errors = 0
        self.started = time.perf_counter()
        self.thread = threading.Thread(target=self._run, name=f"run-{self.id}", daemon=True)

    def start(self) -> "RunJob":
        self.thread.start()
        return self

    def _emit(self, kind: str, payload: dict[str, Any]) -> None:
        self.queue.put((kind, payload))

    def _run(self) -> None:
        try:
            icp = STATE.get_icp()
            leads = STATE.get_leads()
            if self.ids:
                leads = [l for l in leads if l.id in set(self.ids)]
            qual = STATE.qualifier()
            total = len(leads)
            self._emit("start", {"job_id": self.id, "total": total, "model": C.MODEL, "workers": config.workers(), "force": self.force,
                                 "icp": icp_mod.summary_for_state(icp)})
            done = 0
            lock = threading.Lock()

            def on_result(result: dict[str, Any]) -> None:
                nonlocal done
                with lock:
                    done += 1
                    self.results.append(result)
                    self._emit("result", result)
                    self._emit("progress", {"done": done, "errors": self.errors, "total": total, "elapsed_s": round(time.perf_counter() - self.started, 3)})

            def on_error(lead: Lead, exc: Exception) -> None:
                nonlocal done
                with lock:
                    self.errors += 1
                    done += 1
                    self._emit("failed", {"lead_id": lead.id, "message": f"{type(exc).__name__}: {exc}"[:300]})
                    self._emit("progress", {"done": done, "errors": self.errors, "total": total, "elapsed_s": round(time.perf_counter() - self.started, 3)})

            qual.score_many(leads, workers=config.workers(), on_result=on_result, on_error=on_error, stop=self.stop, use_cache=not self.force)
            elapsed = time.perf_counter() - self.started
            all_results = _results_under(icp) if self.ids else self.results
            self._emit("done", {"job_id": self.id, "cancelled": self.stop.is_set(), "totals": run_totals(self.results, self.errors, elapsed),
                                "metrics": _metrics(all_results, icp)})
        except Exception as exc:
            self._emit("fatal", {"message": f"{type(exc).__name__}: {exc}"[:400]})
        finally:
            self.finished.set()

    def events(self) -> Iterator[str]:
        try:
            while True:
                try:
                    kind, payload = self.queue.get(timeout=0.5)
                except queue.Empty:
                    if self.finished.is_set() and self.queue.empty():
                        break
                    yield ": keepalive\n\n"
                    continue
                yield f"event: {kind}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if kind in ("done", "fatal"):
                    break
        finally:
            self.stop.set()
            STATE.jobs.pop(self.id, None)


@app.get("/api/run/stream")
def run_stream(force: bool = Query(False), ids: str | None = Query(None)) -> StreamingResponse:
    STATE.get_client()  # 503 early when no key
    job = RunJob(force=force, ids=[i for i in (ids or "").split(",") if i] or None).start()
    STATE.jobs[job.id] = job
    return StreamingResponse(job.events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/run/{job_id}/cancel")
def cancel(job_id: str) -> dict[str, Any]:
    job = STATE.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "no such job")
    job.stop.set()
    return {"ok": True}


@app.post("/api/score/{lead_id}")
def score_one(lead_id: str, force: bool = Query(False)) -> dict[str, Any]:
    lead = STATE.lead(lead_id)
    q = STATE.qualifier()
    try:
        result = q.score(lead, use_cache=not force)
    except JevError as exc:
        raise HTTPException(502, str(exc))
    STATE.get_cache().save()
    return result


# --------------------------------------------------------------------------- ICP


class ICPBody(BaseModel):
    icp: dict[str, Any]


@app.get("/api/icp")
def get_icp() -> dict[str, Any]:
    return {"icp": STATE.get_icp(), "stale": STATE.qualifier(with_client=False).stale_summary(STATE.get_leads()),
            "presets": icp_mod.list_presets(), "default": config.DEFAULT_PRESET}


@app.put("/api/icp")
def put_icp(body: ICPBody) -> dict[str, Any]:
    try:
        saved = icp_mod.save(body.icp)
    except icp_mod.ICPError as exc:
        raise HTTPException(422, str(exc))
    STATE.icp = saved
    stale = STATE.qualifier(with_client=False).stale_summary(STATE.get_leads())
    return {"icp": saved, "stale": stale}


@app.post("/api/rescore")
def rescore(body: ICPBody) -> dict[str, Any]:
    try:
        icp = icp_mod.validate(body.icp)
    except icp_mod.ICPError as exc:
        raise HTTPException(422, str(exc))
    res = _results_under(icp)
    return {"results": res, "totals": run_totals(res, 0, 0.0), "metrics": _metrics(res, icp),
            "stale": STATE.qualifier(icp, with_client=False).stale_summary(STATE.get_leads())}


@app.post("/api/icp/reset")
def reset_icp() -> dict[str, Any]:
    STATE.icp = icp_mod.reset()
    return get_icp()


@app.get("/api/icp/presets")
def presets() -> list[dict[str, Any]]:
    return icp_mod.list_presets()


@app.post("/api/icp/presets/{preset_id}")
def load_preset(preset_id: str) -> dict[str, Any]:
    try:
        STATE.icp = icp_mod.save(icp_mod.load_preset(preset_id))
    except icp_mod.ICPError as exc:
        raise HTTPException(404, str(exc))
    return get_icp()


# --------------------------------------------------------------------------- reference data


@app.get("/api/questions")
def questions(lead_id: str | None = Query(None)) -> dict[str, Any]:
    leads = STATE.get_leads()
    lead = STATE.lead(lead_id) if lead_id else next((l for l in leads if l.shape == "message"), leads[0])
    q, candidates = STATE.qualifier(with_client=False).questions_for(lead)
    return {"lead_id": lead.id, "questions": C.describe_questions(q), "raw": q, "n": len(q), "crm_candidates": candidates,
            "state": lead.to_state(), "groups": C.GROUP_ORDER}


@app.get("/api/playbook")
def playbook() -> dict[str, Any]:
    return STATE.get_playbook()


@app.get("/api/crm")
def crm() -> list[dict[str, Any]]:
    return STATE.get_crm()


class DomainBody(BaseModel):
    domain: str


@app.post("/api/apollo/enrich")
def apollo_enrich(body: DomainBody) -> dict[str, Any]:
    return apollo.enrich(body.domain)


@app.get("/api/jev/test")
def jev_test() -> dict[str, Any]:
    client = STATE.get_client()
    try:
        return client.ping() if hasattr(client, "ping") else {"ok": True, "model": "fake"}
    except JevError as exc:
        raise HTTPException(502, str(exc))


@app.delete("/api/cache")
def clear_cache() -> dict[str, Any]:
    cache = STATE.get_cache()
    cache.clear()
    cache.save()
    return {"ok": True}
