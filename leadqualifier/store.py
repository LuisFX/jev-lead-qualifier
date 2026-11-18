"""Stdlib sqlite3 provider. WAL, one file, check-constrained unions.

TEACHING NOTE: this module opens the database and applies schema. It does not
know a work item. Callers go through `ledger.py`. Unions live as CHECK columns
plus a decoder with one constructor that can fail (`workitem.decode_*`).

⭐ ENFORCED BY: `tests/test_ledger.py` (junk `arrival_kind` raises with the field
named; a second connection sees a committed row). 🔴 UNENFORCED: nothing stops a
caller from executing SQL beside the provider — the reviewer's grep is the check.
"""

from __future__ import annotations

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
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
