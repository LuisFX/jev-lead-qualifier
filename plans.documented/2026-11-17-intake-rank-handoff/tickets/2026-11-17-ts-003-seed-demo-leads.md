---
title: "ts-003 Seed the 65 demo leads into the store"
slug: ts-003-seed-demo-leads
aliases: [ts-003]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 1
depends_on: [ts-001]
tags: [ticket, ledger]
---

# ts-003 Seed the 65 demo leads into the store

Hub: [[HANDOFF-MEMORY]]. Cost: [[2026-11-17-where-leads-live]]. Tombstone T1.

## Acceptance

A one-time idempotent import writes 65 work items from `data/leads/*.json`. A re-run writes nothing. `load_leads` reads the store. The JSON files remain the demo fixture that `make_dataset.py` regenerates, not the runtime source. Count 65 with a control of one known id (`L001`).

## Progress and what is owed

- 2026-11-17: `seed_from_lead_files` Arrive CsvRow `demo-v1`. 65 rows, L001 present, re-run inserts 0. `load_leads` reads the snapshot.
