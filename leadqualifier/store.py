"""Stdlib sqlite3 provider. WAL, one file, check-constrained unions.

TEACHING NOTE: this module opens the database and applies schema. It does not
know a work item. Callers go through `ledger.py`. Unions live as CHECK columns
plus a decoder with one constructor that can fail (`workitem.decode_*`).
`comms_mount` is occupancy (plugin id on a Channel). Absence is Unmounted.
Secrets are not stored here.

⭐ ENFORCED BY: `tests/test_ledger.py` (junk `arrival_kind` raises with the field
named; a second connection sees a committed row). 🔴 UNENFORCED: nothing stops a
caller from executing SQL beside the provider — the reviewer's grep is the check.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS work_item (
  id TEXT PRIMARY KEY,
  arrival_kind TEXT NOT NULL CHECK (arrival_kind IN ('apollo_person', 'csv_row')),
  person_id TEXT,
  import_id TEXT,
  import_row INTEGER,
  disposition TEXT NOT NULL CHECK (disposition IN (
    'unreviewed', 'held_for_human', 'dismissed', 'queued_for_sequence', 'handed_to_closer'
  )),
  relay_kind TEXT NOT NULL CHECK (relay_kind IN ('no_write', 'pending', 'delivered', 'failed')),
  relay_remote_id TEXT,
  relay_reason TEXT,
  outbound_kind TEXT NOT NULL DEFAULT 'no_send' CHECK (outbound_kind IN ('no_send', 'pending', 'dispatched', 'failed')),
  outbound_channel TEXT CHECK (outbound_channel IS NULL OR outbound_channel IN (
    'email', 'linkedin', 'voice', 'sms', 'ringless_voicemail'
  )),
  outbound_offer_kind TEXT CHECK (outbound_offer_kind IS NULL OR outbound_offer_kind IN (
    'copy', 'case_study', 'qualifying_question', 'calendar', 'form', 'decline_draft'
  )),
  outbound_offer_json TEXT,
  outbound_remote_id TEXT,
  outbound_reason TEXT,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS work_item_apollo_person
  ON work_item(person_id) WHERE arrival_kind = 'apollo_person' AND person_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS work_item_csv_row
  ON work_item(import_id, import_row) WHERE arrival_kind = 'csv_row';

CREATE TABLE IF NOT EXISTS work_item_event (
  work_item_id TEXT NOT NULL REFERENCES work_item(id),
  seq INTEGER NOT NULL,
  kind TEXT NOT NULL,
  body_json TEXT NOT NULL,
  at TEXT NOT NULL,
  PRIMARY KEY (work_item_id, seq)
);

CREATE TABLE IF NOT EXISTS answer (
  work_item_id TEXT NOT NULL,
  question_id TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  body_json TEXT NOT NULL,
  at TEXT NOT NULL,
  PRIMARY KEY (work_item_id, question_id)
);

CREATE TABLE IF NOT EXISTS answer_request (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  work_item_id TEXT NOT NULL,
  at TEXT NOT NULL,
  qids_json TEXT NOT NULL,
  latency_ms INTEGER NOT NULL,
  input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  model TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS icp_version (
  id TEXT PRIMARY KEY,
  body_json TEXT NOT NULL,
  saved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account_snapshot (
  domain TEXT PRIMARY KEY,
  body_json TEXT NOT NULL,
  fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comms_mount (
  channel TEXT PRIMARY KEY CHECK (channel IN (
    'email', 'linkedin', 'voice', 'sms', 'ringless_voicemail'
  )),
  plugin_id TEXT NOT NULL CHECK (plugin_id != '')
);

CREATE TABLE IF NOT EXISTS comms_receive (
  channel TEXT PRIMARY KEY CHECK (channel IN (
    'email', 'linkedin', 'voice', 'sms', 'ringless_voicemail'
  )),
  plugin_id TEXT NOT NULL CHECK (plugin_id != '')
);
"""


_OUTBOUND_COLUMNS = (
    ("outbound_kind", "TEXT NOT NULL DEFAULT 'no_send'"),
    ("outbound_channel", "TEXT"),
    ("outbound_offer_kind", "TEXT"),
    ("outbound_offer_json", "TEXT"),
    ("outbound_remote_id", "TEXT"),
    ("outbound_reason", "TEXT"),
)


def _migrate_outbound(conn: sqlite3.Connection) -> None:
    """Add sequencer columns on a work_item table created before this arc.

    TEACHING NOTE: CREATE TABLE IF NOT EXISTS does not add columns. A laptop
    sqlite from waves 2–4 must ALTER. New files get the columns from SCHEMA.
    Leftover `outbound_body` / `outbound_slots_json` on an old file are unused
    storage (sqlite ALTER cannot drop portably). The decoder does not read them.
    SQLite cannot ALTER a CHECK; a laptop file created under the three-channel
    CHECK keeps that CHECK until the file is recreated. New files have five
    channels.
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info(work_item)").fetchall()}
    if not cols:
        return
    for name, decl in _OUTBOUND_COLUMNS:
        if name not in cols:
            conn.execute(f"ALTER TABLE work_item ADD COLUMN {name} {decl}")
    cols = {row[1] for row in conn.execute("PRAGMA table_info(work_item)").fetchall()}
    if "outbound_body" in cols and "outbound_offer_kind" in cols:
        conn.execute(
            """
            UPDATE work_item SET
              outbound_offer_kind = CASE
                WHEN outbound_channel = 'voice'
                     AND outbound_slots_json IS NOT NULL
                     AND outbound_slots_json != ''
                     AND outbound_slots_json != '[]'
                  THEN 'calendar'
                ELSE 'copy'
              END,
              outbound_offer_json = CASE
                WHEN outbound_channel = 'voice'
                     AND outbound_slots_json IS NOT NULL
                     AND outbound_slots_json != ''
                     AND outbound_slots_json != '[]'
                  THEN json_object('kind', 'calendar', 'slots', json(outbound_slots_json))
                ELSE json_object('kind', 'copy', 'text', COALESCE(outbound_body, ''))
              END
            WHERE outbound_offer_kind IS NULL AND outbound_kind = 'pending'
            """
        )
    _migrate_outbound_events(conn)


def _migrate_outbound_events(conn: sqlite3.Connection) -> None:
    """Rewrite outbound_pending event bodies to `{channel, offer}`. Idempotent.

    TEACHING NOTE: get_state folds the event log, not the snapshot columns. A
    laptop log from waves 2–4 still has `{channel, body, call_slots}`. The
    decoder reads ONE shape; this rewrite is what makes the data say it.
    Re-run writes nothing (`offer` already present).
    """
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "work_item_event" not in tables:
        return
    rows = conn.execute(
        "SELECT work_item_id, seq, body_json FROM work_item_event WHERE kind = 'outbound_pending'"
    ).fetchall()
    for r in rows:
        body = json.loads(r["body_json"])
        if not isinstance(body, dict) or "offer" in body:
            continue
        channel = str(body.get("channel") or "email")
        slots = body.get("call_slots") or []
        text = str(body.get("body") or "")
        if channel == "voice" and slots:
            offer: dict[str, object] = {"kind": "calendar", "slots": list(slots)}
        else:
            offer = {"kind": "copy", "text": text}
        conn.execute(
            "UPDATE work_item_event SET body_json = ? WHERE work_item_id = ? AND seq = ?",
            (json.dumps({"channel": channel, "offer": offer}, ensure_ascii=False), r["work_item_id"], r["seq"]),
        )


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    _migrate_outbound(conn)
    conn.commit()
    return conn
