---
title: "ts-009 Port decide and evolve into the host"
slug: ts-009-port-decider
aliases: [ts-009]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 4
depends_on: [ts-001]
tags: [ticket, disposition]
---

# ts-009 Port decide and evolve into the host

Hub: [[HANDOFF-MEMORY]]. Oracle: `leadqualifier/workitem.fsx`. Cost: [[2026-11-17-disposition-is-a-score]].

## Acceptance

Python `decide` / `evolve` match the F# unions case for case. Host tests port L1–L33, not a subset. Changing the host so L17 would pass while the oracle fails is forbidden; change the `.fsx` first. HTTP commands map to `Command`. A refusal is a 409 with the refusal name, not a 200.

## Progress and what is owed

- 2026-11-17: `leadqualifier/workitem.py` ported case for case. `tests/test_workitem.py` all 33 laws. HTTP 409 `{refusal}`. Oracle 36 passed, 0 failed.
