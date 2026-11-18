---
title: "ts-001 SQLite work items and answer rows"
slug: ts-001-sqlite-ledger
aliases: [ts-001]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 1
depends_on: []
tags: [ticket, ledger]
---

# ts-001 SQLite work items and answer rows

Hub: [[HANDOFF-MEMORY]]. Design: [[ARCHITECTURE]]. Cost: [[2026-11-17-where-leads-live]], [[2026-11-17-answer-store-durability]]. Tombstones T1, T3.

## Acceptance

A SQLite file holds `work_item` (id, arrival kind and foreign ids, disposition, relay) and `answer` (work_item_id, question_id, fingerprint, body, at). The decoder reads one shape. `./run.sh test` still green. No Python dual-reader of JSON cache plus SQLite.

## Progress and what is owed

- 2026-11-17: `leadqualifier/store.py` WAL schema; `ledger.py` is the only sqlite door. `ResultCache` deleted. `tests/test_ledger.py` junk kind names the field; a new connection sees a committed answer.
