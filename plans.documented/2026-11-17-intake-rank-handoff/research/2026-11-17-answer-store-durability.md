---
title: "When a Jev answer hits disk"
slug: answer-store-durability
aliases: [answer-ledger]
date: 2026-11-17
type: research
arc: 2026-11-17-intake-rank-handoff
status: live
read_order: 4
tags: [research, cache, durability]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v1_intake-rank-handoff.md
tickets: []
---

# When a Jev answer hits disk

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-17-where-leads-live|where leads live]].

## Question

Is `data/cache/answers.json` a durable ledger of judgements, or a file written at the end of a run?

## Finding

`ResultCache.store` updates the in-memory dict and sets `_dirty` (`leadqualifier/cache.py` `store`, lines 66–76). It does not write the file. `save` writes only when `_dirty` is set (lines 96–104), by replacing a temp file.

Call sites of `save` in `leadqualifier/`:

| Call | When |
| --- | --- |
| `leadqualifier/pipeline.py` line 135 | after `score_many` has finished every lead |
| `leadqualifier/server.py` line 311 | after one `POST /api/score/{id}` |
| `leadqualifier/server.py` line 414 | after `DELETE /api/cache` |

A batch run that dies before line 135 leaves the new answers in the process only. The fingerprint rule is already the right key: `cached_answers` returns a stored answer only when `stored["fp"]` equals the current question fingerprint (`leadqualifier/cache.py` lines 41–49). Weights are not inside that fingerprint (`leadqualifier/constants.py` `fingerprint`).

`.gitignore` line 13 ignores `data/cache/`. The comment above it calls the directory API response caches.

## What is NOT known

How often a real run has been killed mid-batch on this machine. The gap is the code path, not a counted incident.
