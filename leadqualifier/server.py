"""FastAPI app: serves the single-page UI and a small JSON API. The API key stays server-side.

TEACHING NOTE: HTTP commands become `Command`; a named refusal is 409 with the
refusal kind. Queue / HandOff drain `Bindings[draft.channel]`, never one global
adapter. Paste and inbound are two hosts of `RecordReply`. Unknown inbound is
409 `unknown_sender`; unknown paste id is 404 (unknown to the board).
Mount / Unmount occupy Channel Out; 409 `capability_mismatch` | `unknown_plugin`.
Draft POST /api/rescore does not mint an ICP version. CSV and
People Search both `Arrive`. Contact is derived, never a column.

  GET  /                            the UI
  GET  /api/status                  client, ICP summary, counts, key presence (never the key), mounts summary, cache stats
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
  POST /api/imports                 CSV Arrive (CsvRow)
  POST /api/search                  People Search → Arrive (ApolloPerson)
  GET  /api/review                  HeldForHuman queue
  POST /api/leads/{id}/command      Flag | Dismiss | Queue | HandOff | RecordReply → 409 named refusal
  POST /api/leads/{id}/reply        {text} → RecordReply of body, then rescore from the new message
  POST /api/inbound                 vendor-blind InboundHint + text → match then RecordReply
  GET  /api/integrations            Channel Out slots, occupancy, ready, candidates (never keys)
  POST /api/integrations/mount      {channel, plugin_id} → 409 capability_mismatch | unknown_plugin
  POST /api/integrations/unmount    {channel}
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import apollo, config, icp as icp_mod
from . import constants as C
from . import intake
from .jev import JevClient, JevError
from .ledger import get_ledger
from .leads import Lead, load_crm, load_gold, load_leads, load_playbook
from .metrics import compute_metrics
from .pipeline import Qualifier, run_totals
from .relay import RelayLoop
from .bindings import get_bindings, invalidate_bindings
from .comms import drain_outbound
from .integrations import ComposeErr, mounts_status, plugin_id, slot_snapshot, try_mount
from .inbound import UnknownSender, decode_hint, match_inbound
from .workitem import (
    Err,
    Nothing,
    Open,
    Unjudged,
    contact_json,
    decode_channel,
    draft_for_handoff,
    draft_for_queue,
    encode_draft,
    judgement_from_result,
    outbound_json,
    parse_command,
)

log = logging.getLogger("firstread")
FAKE_MODE = os.environ.get("FIRSTREAD_FAKE", "").strip().lower() in ("1", "true", "yes")


class AppState:
    def __init__(self) -> None:
        self.icp: dict[str, Any] | None = None
        self.leads: list[Lead] | None = None
        self.crm: list[dict[str, Any]] | None = None
        self.playbook: dict[str, Any] | None = None
        self.gold: dict[str, Any] | None = None
        self.cache: Any | None = None
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

    def get_cache(self) -> Any:
        if self.cache is None:
            self.cache = get_ledger()
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
                         client=self.get_client() if with_client else None, cache=self.get_cache(),
                         icp_version_id=icp_mod.live_version_id() if icp is None else None)


STATE = AppState()
_relay: RelayLoop | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_ledger().seed_from_lead_files(config.LEADS_DIR)
    icp_mod.load()
    global _relay
    if os.environ.get("FIRSTREAD_RELAY", "1").strip().lower() not in ("0", "false", "off"):
        _relay = RelayLoop(get_ledger())
        _relay.start()
    yield
    if _relay is not None:
        _relay.stop.set()


app = FastAPI(title="First Read", version="0.1.0", lifespan=lifespan)
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
        "icp_version_id": icp_mod.live_version_id(),
        "hubspot": {"write": config.hubspot_write_enabled(), "has_token": config.hubspot_token() is not None},
        "mounts": mounts_status(get_ledger()),
        "review": len(get_ledger().list_held()),
    }


def _public_lead(lead: Lead) -> dict[str, Any]:
    row = get_ledger().get_row(lead.id)
    state = get_ledger().snapshot_state(row) if row else Nothing()
    body = lead.to_json()
    if body.get("person"):
        body["person"] = {k: v for k, v in body["person"].items() if k not in ("email", "phone")}
    email = (lead.person or {}).get("email")
    body["contact"] = contact_json(state if isinstance(state, Open) else Nothing(), email)
    if isinstance(state, Open):
        body["disposition"] = state.disposition.kind
        body["relay"] = state.relay.kind
        body["outbound"] = outbound_json(state)
    else:
        body["disposition"] = "unreviewed"
        body["relay"] = "no_write"
        body["outbound"] = {"kind": "no_send"}
    return body


@app.get("/api/leads")
def leads() -> list[dict[str, Any]]:
    return [_public_lead(l) for l in STATE.get_leads()]


@app.get("/api/leads/{lead_id}")
def lead_detail(lead_id: str) -> dict[str, Any]:
    lead = STATE.lead(lead_id)
    q = STATE.qualifier(with_client=False)
    result = q.rescore(lead)
    questions, _ = q.questions_for(lead)
    return {"lead": _public_lead(lead), "result": result, "questions": C.describe_questions(questions), "state": lead.to_state()}


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
            "presets": icp_mod.list_presets(), "default": config.DEFAULT_PRESET, "version_id": icp_mod.live_version_id(),
            "versions": len(get_ledger().list_icp_versions())}


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


class ImportBody(BaseModel):
    csv: str
    import_id: str | None = None


@app.post("/api/imports")
def import_csv(body: ImportBody) -> dict[str, Any]:
    out = intake.arrive_csv(get_ledger(), body.csv, body.import_id)
    STATE.leads = None
    return out


class SearchBody(BaseModel):
    titles: list[str] | None = None
    locations: list[str] | None = None
    employee_ranges: list[str] | None = None
    keywords: list[str] | None = None
    page: int = 1


@app.get("/api/search/filters")
def search_filters() -> dict[str, Any]:
    return intake.filters_payload(STATE.get_icp())


@app.post("/api/search")
def people_search(body: SearchBody | None = None) -> dict[str, Any]:
    filters = intake.filters_payload(STATE.get_icp())
    if body is not None:
        if body.titles is not None:
            filters["titles"] = body.titles
        if body.locations is not None:
            filters["locations"] = body.locations
        if body.employee_ranges is not None:
            filters["employee_ranges"] = body.employee_ranges
        if body.keywords is not None:
            filters["keywords"] = body.keywords
    found = apollo.search_people(filters, page=body.page if body else 1)
    if not found.get("ok"):
        raise HTTPException(502, found.get("reason") or "People Search failed")
    landed = intake.arrive_apollo_people(get_ledger(), found.get("people") or [])
    STATE.leads = None
    return {**landed, "filters": filters, "hits": len(found.get("people") or [])}


@app.get("/api/review")
def review_queue() -> dict[str, Any]:
    q = STATE.qualifier(with_client=False)
    items = []
    for row in get_ledger().list_held():
        lead = intake.lead_from_row(row)
        items.append({"lead": _public_lead(lead), "result": q.rescore(lead)})
    return {"items": items}


class CommandBody(BaseModel):
    kind: str
    remote_id: str | None = None
    reason: str | None = None
    text: str | None = None


@app.post("/api/leads/{lead_id}/command")
def lead_command(lead_id: str, body: CommandBody) -> dict[str, Any]:
    STATE.lead(lead_id)  # 404 if unknown to the board
    lead = STATE.lead(lead_id)
    result = STATE.qualifier(with_client=False).rescore(lead)
    judgement = Unjudged() if result is None else judgement_from_result(icp_mod.live_version_id(), result)
    if body.kind == "hand_off":
        draft = draft_for_handoff(result)
    else:
        draft = draft_for_queue(result)
    extra: dict[str, Any] = {
        "remote_id": body.remote_id,
        "reason": body.reason,
        "text": body.text,
        "draft": encode_draft(draft),
    }
    try:
        cmd = parse_command(body.kind, extra)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    out = get_ledger().apply_command(lead_id, cmd, judgement)
    if isinstance(out, Err):
        raise HTTPException(409, {"refusal": out.error.kind})
    if body.kind in ("queue", "hand_off"):
        drain_outbound(get_ledger(), get_bindings())
    if body.kind == "record_reply":
        get_ledger().invalidate_item(lead_id)
        STATE.leads = None
        try:
            scored = STATE.lead(lead_id)
            STATE.qualifier(with_client=True).score(scored, use_cache=False)
        except HTTPException:
            pass
    STATE.leads = None
    return lead_detail(lead_id)


def land_reply(work_item_id: str, text: str) -> dict[str, Any]:
    """RecordReply of body, then rescore. Paste and inbound both land here."""
    return lead_command(work_item_id, CommandBody(kind="record_reply", text=text))


class ReplyBody(BaseModel):
    text: str


@app.post("/api/leads/{lead_id}/reply")
def lead_reply(lead_id: str, body: ReplyBody) -> dict[str, Any]:
    """Paste door: the URL already names the work item. Match is `/api/inbound`."""
    STATE.lead(lead_id)
    return land_reply(lead_id, body.text)


class InboundHintBody(BaseModel):
    kind: str
    id: str | None = None
    email: str | None = None
    phone: str | None = None


class InboundBody(BaseModel):
    hint: InboundHintBody
    text: str


@app.post("/api/inbound")
def inbound_reply(body: InboundBody) -> dict[str, Any]:
    """InboundMatch then RecordReply. A named vendor file may POST here later."""
    try:
        hint = decode_hint(body.hint.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    found = match_inbound(get_ledger(), hint)
    if isinstance(found, UnknownSender):
        raise HTTPException(409, {"refusal": "unknown_sender"})
    return land_reply(found.work_item_id, body.text)


class MountBody(BaseModel):
    channel: str
    plugin_id: str


class UnmountBody(BaseModel):
    channel: str


@app.get("/api/integrations")
def integrations_get() -> dict[str, Any]:
    """Channel Out slots. Occupancy and ready, never a secret value."""
    return {"slots": slot_snapshot(get_ledger())}


@app.post("/api/integrations/mount")
def integrations_mount(body: MountBody) -> dict[str, Any]:
    try:
        ch = decode_channel(body.channel)
        pid = plugin_id(body.plugin_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    out = try_mount(get_ledger(), ch, pid)
    if isinstance(out, ComposeErr):
        raise HTTPException(409, {"refusal": out.error.kind})
    get_ledger().put_mount(ch.kind, pid.value)
    invalidate_bindings()
    return {"slots": slot_snapshot(get_ledger())}


@app.post("/api/integrations/unmount")
def integrations_unmount(body: UnmountBody) -> dict[str, Any]:
    try:
        ch = decode_channel(body.channel)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    get_ledger().delete_mount(ch.kind)
    invalidate_bindings()
    return {"slots": slot_snapshot(get_ledger())}
