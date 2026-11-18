"""ts-001 schema, ts-002 persist-on-return, ts-003 seed 65. Kill-and-restart is a new connection.

TEACHING NOTE: a second `Ledger` on the same path is the kill-and-restart smoke.
If this test passed by reading an in-memory dict, the write never hit disk.
"""

from __future__ import annotations

import sqlite3

import pytest

from leadqualifier import config
from leadqualifier.ledger import Ledger, get_ledger
from leadqualifier.store import connect
from leadqualifier.workitem import decode_arrival, decode_disposition, decode_relay


def test_junk_arrival_kind_names_the_field():
    with pytest.raises(ValueError, match="arrival.kind"):
        decode_arrival("nope", None, None, None)
    with pytest.raises(ValueError, match="disposition.kind"):
        decode_disposition("maybe")
    with pytest.raises(ValueError, match="relay.kind"):
        decode_relay("shipped", None, None)


def test_check_constraint_rejects_junk_kind(tmp_path):
    conn = connect(tmp_path / "x.sqlite")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO work_item(id, arrival_kind, person_id, import_id, import_row, disposition,
               relay_kind, relay_remote_id, relay_reason, payload_json, created_at)
               VALUES ('X', 'nope', NULL, 'demo-v1', 1, 'unreviewed', 'no_write', NULL, NULL, '{}', '2026-01-01T00:00:00Z')"""
        )


def test_store_is_visible_on_a_new_connection(tmp_path):
    path = tmp_path / "firstread.sqlite"
    a = Ledger(path)
    a.store("L001", {"q": "fp"}, {"q": {"type": "noul", "p": 0.5}}, {"qids": ["q"], "latency_ms": 10, "input_tokens": 3, "model": "jev-1.13.0"})
    a.close()
    b = Ledger(path)
    assert b.cached_answers("L001", {"q": "fp"})["q"]["p"] == 0.5
    assert b.history()["requests"] == 1


def test_seed_65_is_idempotent_and_includes_L001():
    n = get_ledger().seed_from_lead_files(config.LEADS_DIR)
    assert n == 65
    rows = get_ledger().list_rows()
    assert len(rows) == 65
    ids = {r["id"] for r in rows}
    assert "L001" in ids
    assert all(r["arrival_kind"] == "csv_row" and r["import_id"] == "demo-v1" for r in rows)
    assert get_ledger().seed_from_lead_files(config.LEADS_DIR) == 0
    from leadqualifier.leads import load_leads

    leads = load_leads()
    assert len(leads) == 65 and any(l.id == "L001" for l in leads)
