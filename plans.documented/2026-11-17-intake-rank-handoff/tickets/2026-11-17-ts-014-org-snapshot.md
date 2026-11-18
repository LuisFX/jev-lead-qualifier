---
title: "ts-014 Organisation snapshot on the account"
slug: ts-014-org-snapshot
aliases: [ts-014]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 6
depends_on: [ts-001]
tags: [ticket, apollo]
---

# ts-014 Organisation snapshot on the account

Hub: [[HANDOFF-MEMORY]]. Cost: [[2026-11-17-apollo-is-not-intake]]. Tombstone T6.

## Acceptance

A successful enrich stores the trimmed organisation on the account with `fetched_at`. The hashed file under `data/cache/apollo/` is no longer the only copy. Failures stay uncached. Jev still does not receive this payload unless it is copied onto the work item's company text by a later act this ticket does not add.

## Progress and what is owed

- 2026-11-17: `account_snapshot(domain, body_json, fetched_at)`. Enrich success writes it. Failures uncached. Hashed files remain a duplicate.
