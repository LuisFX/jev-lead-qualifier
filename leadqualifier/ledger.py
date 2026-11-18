"""The answer ledger and work-item log. All sqlite access goes through here.

TEACHING NOTE: this replaces `ResultCache`. There is no dual reader of JSON cache
and SQLite — `cache.py` is gone. `store` COMMITS; a new connection must see the
row. The snapshot on `work_item` is a fold of `work_item_event`, written in the
same transaction as the append.

What this does not do: talk to Jev, HubSpot, Apollo, or a sequencer vendor. Ports
sit in their modules and call `apply_command` / `put_answer`. Sequencer state lives
in `outbound_*` columns, not `relay_*`. Pending drafts store `outbound_offer_kind`
+ `outbound_offer_json`. The decoder does not read leftover `outbound_body`.

⭐ ENFORCED BY: `tests/test_ledger.py` (persist-then-reconnect; seed 65 idempotent).
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from . import store
from .workitem import (
    ApplyOk,
    Arrival,
    Arrived,
    Awaiting,
    Command,
    Dispatched,
    Err,
    Event,
    Flagged,
    HandedOff,
    Nothing,
    Open,
    OutboundDispatched,
    OutboundFailed,
    OutboundPending,
    PersonDismissed,
    Queued,
    RelayDelivered,
    RelayFailed,
    RelayPending,
    ReplyArrived,
    SendFailed,
    State,
    apply,
    decode_arrival,
    decode_disposition,
    decode_draft,
    decode_outbound,
    decode_relay,
    encode_draft,
    encode_offer,
    fold,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def encode_event(event: Event) -> tuple[str, dict[str, Any]]:
    match event:
        case Arrived(arrival=arrival):
            return "arrived", {"arrival": _arrival_body(arrival)}
        case Flagged():
            return "flagged", {}
        case PersonDismissed():
            return "person_dismissed", {}
        case Queued():
            return "queued", {}
        case HandedOff():
            return "handed_off", {}
        case ReplyArrived(body=body):
            return "reply_arrived", {"body": body}
        case RelayPending():
            return "relay_pending", {}
        case RelayDelivered(remote_id=remote_id):
            return "relay_delivered", {"remote_id": remote_id}
        case RelayFailed(reason=reason):
            return "relay_failed", {"reason": reason}
        case OutboundPending(draft=draft):
            return "outbound_pending", encode_draft(draft)
        case OutboundDispatched(remote_id=remote_id):
            return "outbound_dispatched", {"remote_id": remote_id}
        case OutboundFailed(reason=reason):
            return "outbound_failed", {"reason": reason}
        case _:
            raise AssertionError(f"unhandled event {event!r}")


def decode_event(kind: str, body: dict[str, Any]) -> Event:
    if kind == "arrived":
        a = body["arrival"]
        return Arrived(decode_arrival(a["kind"], a.get("person_id"), a.get("import_id"), a.get("row")))
    if kind == "flagged":
        return Flagged()
    if kind == "person_dismissed":
        return PersonDismissed()
    if kind == "queued":
        return Queued()
    if kind == "handed_off":
        return HandedOff()
    if kind == "reply_arrived":
        return ReplyArrived(str(body.get("body") or ""))
    if kind == "relay_pending":
        return RelayPending()
    if kind == "relay_delivered":
        return RelayDelivered(body["remote_id"])
    if kind == "relay_failed":
        return RelayFailed(body["reason"])
    if kind == "outbound_pending":
        return OutboundPending(decode_draft(body))
    if kind == "outbound_dispatched":
        return OutboundDispatched(body["remote_id"])
    if kind == "outbound_failed":
        return OutboundFailed(body["reason"])
    raise ValueError(f"event.kind={kind!r}")


def _arrival_body(arrival: Arrival) -> dict[str, Any]:
    if arrival.kind == "apollo_person":
        return {"kind": "apollo_person", "person_id": arrival.person_id.value}
    return {"kind": "csv_row", "import_id": arrival.import_id.value, "row": arrival.row}


def _arrival_cols(arrival: Arrival) -> dict[str, Any]:
    if arrival.kind == "apollo_person":
        return {"arrival_kind": "apollo_person", "person_id": arrival.person_id.value, "import_id": None, "import_row": None}
    return {"arrival_kind": "csv_row", "person_id": None, "import_id": arrival.import_id.value, "import_row": arrival.row}


def _relay_cols(state: State) -> dict[str, Any]:
    r = state.relay
    return {
        "relay_kind": r.kind,
        "relay_remote_id": getattr(r, "remote_id", None),
        "relay_reason": getattr(r, "reason", None),
    }


def _outbound_cols(state: State) -> dict[str, Any]:
    o = state.outbound
    draft = o.draft if isinstance(o, Awaiting) else None
    return {
        "outbound_kind": o.kind,
        "outbound_channel": draft.channel.kind if draft else None,
        "outbound_offer_kind": draft.offer.kind if draft else None,
        "outbound_offer_json": json.dumps(encode_offer(draft.offer), ensure_ascii=False) if draft else None,
        "outbound_remote_id": getattr(o, "remote_id", None) if isinstance(o, Dispatched) else None,
        "outbound_reason": getattr(o, "reason", None) if isinstance(o, SendFailed) else None,
    }


def _fold_reply_payload(payload: dict[str, Any], body: str) -> dict[str, Any]:
    """The inbound text becomes the message the rank scores. Prior text is kept."""
    prior = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    prior_text = prior.get("text") if isinstance(prior, dict) else None
    message = dict(prior) if isinstance(prior, dict) else {}
    message["text"] = body
    if prior_text:
        message["prior"] = prior_text
    out = dict(payload)
    out["message"] = message
    return out


class Ledger:
    """Answer + work-item store. Thread-safe; one connection, WAL."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._conn = store.connect(self.path)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- answers (was ResultCache) -------------------------------------------

    def cached_answers(self, lead_id: str, fingerprints: dict[str, str]) -> dict[str, dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT question_id, fingerprint, body_json FROM answer WHERE work_item_id = ?", (lead_id,)
            ).fetchall()
        out: dict[str, dict[str, Any]] = {}
        for r in rows:
            qid = r["question_id"]
            if fingerprints.get(qid) == r["fingerprint"]:
                out[qid] = json.loads(r["body_json"])
        return out

    def missing(self, lead_id: str, fingerprints: dict[str, str]) -> list[str]:
        have = self.cached_answers(lead_id, fingerprints)
        return [qid for qid in fingerprints if qid not in have]

    def has(self, lead_id: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM answer WHERE work_item_id = ? LIMIT 1", (lead_id,)
            ).fetchone()
        return row is not None

    def store(
        self,
        lead_id: str,
        fingerprints: dict[str, str],
        answers: dict[str, dict[str, Any]],
        request: dict[str, Any] | None = None,
    ) -> None:
        """Commit each answer as Jev returns. A new connection must see the rows (ts-002)."""
        at = _now()
        with self._lock:
            for qid, answer in answers.items():
                if qid not in fingerprints:
                    continue
                self._conn.execute(
                    """INSERT INTO answer(work_item_id, question_id, fingerprint, body_json, at)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(work_item_id, question_id) DO UPDATE SET
                         fingerprint=excluded.fingerprint, body_json=excluded.body_json, at=excluded.at""",
                    (lead_id, qid, fingerprints[qid], json.dumps(answer, ensure_ascii=False), at),
                )
            if request:
                self._conn.execute(
                    """INSERT INTO answer_request(work_item_id, at, qids_json, latency_ms, input_tokens, output_tokens, model)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        lead_id,
                        at,
                        json.dumps(request.get("qids") or list(answers)),
                        int(request.get("latency_ms") or 0),
                        int(request.get("input_tokens") or 0),
                        int(request.get("output_tokens") or 0),
                        str(request.get("model") or ""),
                    ),
                )
            self._conn.commit()

    def requests_for(self, lead_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT at, qids_json, latency_ms, input_tokens, output_tokens, model FROM answer_request WHERE work_item_id = ? ORDER BY id",
                (lead_id,),
            ).fetchall()
        return [
            {
                "at": r["at"],
                "qids": json.loads(r["qids_json"]),
                "latency_ms": r["latency_ms"],
                "input_tokens": r["input_tokens"],
                "output_tokens": r["output_tokens"],
                "model": r["model"],
            }
            for r in rows
        ]

    def history(self, lead_ids: list[str] | None = None) -> dict[str, Any]:
        with self._lock:
            if lead_ids is None:
                rows = self._conn.execute(
                    "SELECT work_item_id, latency_ms, input_tokens FROM answer_request"
                ).fetchall()
                n_leads = self._conn.execute("SELECT COUNT(DISTINCT work_item_id) AS n FROM answer").fetchone()["n"]
            else:
                placeholders = ",".join("?" * len(lead_ids)) or "NULL"
                rows = self._conn.execute(
                    f"SELECT work_item_id, latency_ms, input_tokens FROM answer_request WHERE work_item_id IN ({placeholders})",
                    lead_ids,
                ).fetchall() if lead_ids else []
                n_leads = self._conn.execute(
                    f"SELECT COUNT(DISTINCT work_item_id) AS n FROM answer WHERE work_item_id IN ({placeholders})",
                    lead_ids,
                ).fetchone()["n"] if lead_ids else 0
        latencies = [float(r["latency_ms"] or 0.0) for r in rows if r["latency_ms"]]
        tokens_in = sum(int(r["input_tokens"] or 0) for r in rows)
        return {
            "requests": len(rows),
            "leads": int(n_leads or 0),
            "tokens_in": tokens_in,
            "latency_mean_ms": (sum(latencies) / len(latencies)) if latencies else None,
        }

    def invalidate_item(self, work_item_id: str) -> int:
        """Drop cached answers for one work item so a new message is scored fresh."""
        with self._lock:
            cur = self._conn.execute("DELETE FROM answer WHERE work_item_id = ?", (work_item_id,))
            removed = cur.rowcount
            self._conn.commit()
        return removed

    def invalidate(self, question_ids: list[str] | None = None) -> int:
        with self._lock:
            if question_ids is None:
                row = self._conn.execute("SELECT COUNT(*) AS n FROM answer").fetchone()
                removed = int(row["n"])
                self._conn.execute("DELETE FROM answer")
                self._conn.execute("DELETE FROM answer_request")
            else:
                removed = 0
                for qid in question_ids:
                    cur = self._conn.execute("DELETE FROM answer WHERE question_id = ?", (qid,))
                    removed += cur.rowcount
            self._conn.commit()
        return removed

    def clear(self) -> None:
        self.invalidate(None)

    def __len__(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(DISTINCT work_item_id) AS n FROM answer").fetchone()
        return int(row["n"] if row else 0)

    def save(self) -> None:
        """No-op: `store` already committed. Kept so `score_many` can still call it."""
        return None

    # --- work items -----------------------------------------------------------

    def get_state(self, work_item_id: str) -> State:
        events = self.events_for(work_item_id)
        folded = fold(Nothing(), events)
        if isinstance(folded, Err):
            raise ValueError(f"work_item_event fold failed for {work_item_id}: {folded.error.kind}")
        return folded.state

    def events_for(self, work_item_id: str) -> list[Event]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT kind, body_json FROM work_item_event WHERE work_item_id = ? ORDER BY seq",
                (work_item_id,),
            ).fetchall()
        return [decode_event(r["kind"], json.loads(r["body_json"])) for r in rows]

    def get_row(self, work_item_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM work_item WHERE id = ?", (work_item_id,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def find_by_arrival(self, arrival: Arrival) -> str | None:
        with self._lock:
            if arrival.kind == "apollo_person":
                row = self._conn.execute(
                    "SELECT id FROM work_item WHERE arrival_kind = 'apollo_person' AND person_id = ?",
                    (arrival.person_id.value,),
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT id FROM work_item WHERE arrival_kind = 'csv_row' AND import_id = ? AND import_row = ?",
                    (arrival.import_id.value, arrival.row),
                ).fetchone()
        return None if row is None else str(row["id"])

    def list_rows(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM work_item ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def list_held(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM work_item WHERE disposition = 'held_for_human' ORDER BY id"
            ).fetchall()
        return [dict(r) for r in rows]

    def list_pending_relay(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM work_item WHERE relay_kind = 'pending' ORDER BY id"
            ).fetchall()
        return [dict(r) for r in rows]

    def list_pending_outbound(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM work_item WHERE outbound_kind = 'pending' ORDER BY id"
            ).fetchall()
        return [dict(r) for r in rows]

    def apply_command(
        self,
        work_item_id: str,
        cmd: Command,
        judgement,
        payload: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> ApplyOk | Err:
        """Append events and fold the snapshot in one transaction."""
        state = self.get_state(work_item_id)
        decided = apply(cmd, state, judgement)
        if isinstance(decided, Err):
            return decided
        at = created_at or _now()
        new_state = decided.state
        assert isinstance(new_state, Open)
        arrival_cols = _arrival_cols(new_state.arrival)
        relay_cols = _relay_cols(new_state)
        outbound_cols = _outbound_cols(new_state)
        reply_body = next((e.body for e in decided.events if isinstance(e, ReplyArrived)), None)
        with self._lock:
            existing = self._conn.execute("SELECT payload_json, created_at, id FROM work_item WHERE id = ?", (work_item_id,)).fetchone()
            if existing is None:
                body = json.dumps(payload or {"id": work_item_id}, ensure_ascii=False)
                self._conn.execute(
                    """INSERT INTO work_item(id, arrival_kind, person_id, import_id, import_row, disposition,
                       relay_kind, relay_remote_id, relay_reason,
                       outbound_kind, outbound_channel, outbound_offer_kind, outbound_offer_json, outbound_remote_id, outbound_reason,
                       payload_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        work_item_id,
                        arrival_cols["arrival_kind"],
                        arrival_cols["person_id"],
                        arrival_cols["import_id"],
                        arrival_cols["import_row"],
                        new_state.disposition.kind,
                        relay_cols["relay_kind"],
                        relay_cols["relay_remote_id"],
                        relay_cols["relay_reason"],
                        outbound_cols["outbound_kind"],
                        outbound_cols["outbound_channel"],
                        outbound_cols["outbound_offer_kind"],
                        outbound_cols["outbound_offer_json"],
                        outbound_cols["outbound_remote_id"],
                        outbound_cols["outbound_reason"],
                        body,
                        at,
                    ),
                )
                seq0 = 0
            else:
                seq0 = self._conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) AS n FROM work_item_event WHERE work_item_id = ?",
                    (work_item_id,),
                ).fetchone()["n"]
                payload_json = existing["payload_json"]
                if reply_body is not None:
                    payload_json = json.dumps(
                        _fold_reply_payload(json.loads(payload_json), reply_body),
                        ensure_ascii=False,
                    )
                self._conn.execute(
                    """UPDATE work_item SET disposition=?, relay_kind=?, relay_remote_id=?, relay_reason=?,
                       outbound_kind=?, outbound_channel=?, outbound_offer_kind=?, outbound_offer_json=?,
                       outbound_remote_id=?, outbound_reason=?, payload_json=?
                       WHERE id=?""",
                    (
                        new_state.disposition.kind,
                        relay_cols["relay_kind"],
                        relay_cols["relay_remote_id"],
                        relay_cols["relay_reason"],
                        outbound_cols["outbound_kind"],
                        outbound_cols["outbound_channel"],
                        outbound_cols["outbound_offer_kind"],
                        outbound_cols["outbound_offer_json"],
                        outbound_cols["outbound_remote_id"],
                        outbound_cols["outbound_reason"],
                        payload_json,
                        work_item_id,
                    ),
                )
            for i, event in enumerate(decided.events, start=1):
                kind, body = encode_event(event)
                self._conn.execute(
                    "INSERT INTO work_item_event(work_item_id, seq, kind, body_json, at) VALUES (?, ?, ?, ?, ?)",
                    (work_item_id, seq0 + i, kind, json.dumps(body, ensure_ascii=False), at),
                )
            self._conn.commit()
        return decided

    def seed_from_lead_files(self, leads_dir: Path, import_id: str = "demo-v1") -> int:
        """Idempotent: each `data/leads/*.json` becomes Arrive (CsvRow demo-v1, row). Re-run inserts 0."""
        from .workitem import Arrive, CsvRow, ImportId, Unjudged

        files = sorted(leads_dir.glob("*.json"))
        inserted = 0
        for i, path in enumerate(files, start=1):
            raw = json.loads(path.read_text(encoding="utf-8"))
            wid = str(raw["id"])
            if self.get_row(wid) is not None:
                continue
            arrival = CsvRow(ImportId(import_id), i)
            result = self.apply_command(wid, Arrive(arrival), Unjudged(), payload=raw, created_at=str(raw.get("received_at") or _now()))
            if isinstance(result, ApplyOk):
                inserted += 1
        return inserted

    def snapshot_state(self, row: dict[str, Any]) -> Open:
        arrival = decode_arrival(row["arrival_kind"], row["person_id"], row["import_id"], row["import_row"])
        return Open(
            arrival=arrival,
            disposition=decode_disposition(row["disposition"]),
            relay=decode_relay(row["relay_kind"], row["relay_remote_id"], row["relay_reason"]),
            outbound=decode_outbound(
                row.get("outbound_kind") or "no_send",
                row.get("outbound_channel"),
                row.get("outbound_offer_kind"),
                row.get("outbound_offer_json"),
                row.get("outbound_remote_id"),
                row.get("outbound_reason"),
            ),
        )

    # --- ICP versions ---------------------------------------------------------

    def insert_icp_version(self, body: dict[str, Any]) -> str:
        vid = str(uuid4())
        with self._lock:
            self._conn.execute(
                "INSERT INTO icp_version(id, body_json, saved_at) VALUES (?, ?, ?)",
                (vid, json.dumps(body, ensure_ascii=False), _now()),
            )
            self._conn.execute(
                "INSERT INTO app_state(key, value) VALUES ('live_icp_version_id', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (vid,),
            )
            self._conn.commit()
        return vid

    def live_icp_version_id(self) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM app_state WHERE key = 'live_icp_version_id'").fetchone()
        return None if row is None else str(row["value"])

    def get_icp_version(self, version_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT body_json FROM icp_version WHERE id = ?", (version_id,)).fetchone()
        return None if row is None else json.loads(row["body_json"])

    def live_icp(self) -> tuple[str, dict[str, Any]] | None:
        vid = self.live_icp_version_id()
        if vid is None:
            return None
        body = self.get_icp_version(vid)
        if body is None:
            return None
        return vid, body

    def list_icp_versions(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT id, saved_at FROM icp_version ORDER BY saved_at").fetchall()
        return [{"id": r["id"], "saved_at": r["saved_at"]} for r in rows]

    # --- account snapshot (wave 6) -------------------------------------------

    def put_account_snapshot(self, domain: str, body: dict[str, Any], fetched_at: str | None = None) -> None:
        at = fetched_at or _now()
        payload = dict(body)
        payload["fetched_at"] = at
        with self._lock:
            self._conn.execute(
                """INSERT INTO account_snapshot(domain, body_json, fetched_at) VALUES (?, ?, ?)
                   ON CONFLICT(domain) DO UPDATE SET body_json=excluded.body_json, fetched_at=excluded.fetched_at""",
                (domain, json.dumps(payload, ensure_ascii=False), at),
            )
            self._conn.commit()

    def get_account_snapshot(self, domain: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT body_json, fetched_at FROM account_snapshot WHERE domain = ?", (domain,)
            ).fetchone()
        if row is None:
            return None
        body = json.loads(row["body_json"])
        body["fetched_at"] = row["fetched_at"]
        return body


_lock = threading.Lock()
_ledger: Ledger | None = None


def get_ledger() -> Ledger:
    global _ledger
    from . import config

    with _lock:
        if _ledger is None:
            _ledger = Ledger(config.SQLITE_PATH)
        return _ledger


def reset_ledger_for_tests(path: Path) -> Ledger:
    global _ledger
    with _lock:
        if _ledger is not None:
            try:
                _ledger.close()
            except Exception:
                pass
        _ledger = Ledger(path)
        return _ledger
