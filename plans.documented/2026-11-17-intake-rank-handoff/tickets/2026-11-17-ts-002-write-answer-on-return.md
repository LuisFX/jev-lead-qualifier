---
title: "ts-002 Write each Jev answer when it returns"
slug: ts-002-write-answer-on-return
aliases: [ts-002]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 1
depends_on: [ts-001]
tags: [ticket, ledger]
---

# ts-002 Write each Jev answer when it returns

Hub: [[HANDOFF-MEMORY]]. Cost: [[2026-11-17-answer-store-durability]]. Tombstone T3.

## Acceptance

`Qualifier.score` persists each new answer inside `store`, not only in `score_many`'s final `save`. Kill the process after a lead returns. Restart. That lead's fingerprints are present. Fingerprint mismatch still asks again.

## Progress and what is owed

- 2026-11-17: `Ledger.store` commits inside `Qualifier.score`. `score_many` save is a no-op. New connection sees the row.
