---
title: "Board — intake, rank, handoff"
slug: board-intake-rank-handoff
aliases: [board]
date: 2026-11-17
type: ticket-index
arc: 2026-11-17-intake-rank-handoff
status: live
read_order: 11
tags: [board]
---

# Board — intake, rank, handoff

Hub: [[HANDOFF-MEMORY]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v1_intake-rank-handoff]]. Design: [[ARCHITECTURE]].

## Legend

| Symbol | Meaning |
| --- | --- |
| ✅ | done |
| 🟦 | code done and smoked locally, closes on the deploy smoke |
| ◑ | partly done, what is owed is named |
| ⬜ | open |
| ❓ | waits on an owner ruling |
| ✈ | a deploy, only on the owner's word |

## Waves

| Wave | Tickets | The smoke that closes the wave | Status |
| --- | --- | --- | --- |
| 0 · Confirm the glance | none | Owner confirmed v1, 2026-11-17 | ✅ 2026-11-17 |
| 1 · Ledger | ts-001 ts-002 ts-003 | Kill a run after ten leads. Restart. Those ten still have answers | ✅ new connection sees committed answers; seed 65 |
| 2 · Profile | ts-004 ts-005 | Two saved versions. Rescore of the old one still matches | ✅ |
| 3 · Intake | ts-006 ts-007 ts-008 | CSV insert plus a measured search insert | ✅ CSV in the browser; live People Search 403 on this Apollo Free plan |
| 4 · Disposition | ts-009 ts-010 ts-011 | Host refusals match the oracle. Dismissed email absent | ✅ |
| 5 · Handoff | ts-012 ts-013 | Test-portal contact shows tier. Second HandOff does not write | 🟦 FakeWriter + second HandOff refused; live test contact owed |
| 6 · Decorate | ts-014 | Enrich stores fetched_at on the account | ✅ |

## Tickets

| # | Ticket | Wave | Depends on | Status |
| --- | --- | --- | --- | --- |
| 001 | [sqlite ledger](2026-11-17-ts-001-sqlite-ledger.md) | 1 | — | ✅ |
| 002 | [write answer on return](2026-11-17-ts-002-write-answer-on-return.md) | 1 | 001 | ✅ |
| 003 | [seed 65 leads](2026-11-17-ts-003-seed-demo-leads.md) | 1 | 001 | ✅ |
| 004 | [profile versions](2026-11-17-ts-004-profile-versions.md) | 2 | 001 | ✅ |
| 005 | [judgement carries version](2026-11-17-ts-005-judgement-carries-version.md) | 2 | 004, 002 | ✅ |
| 006 | [CSV birth](2026-11-17-ts-006-csv-birth.md) | 3 | 001 | ✅ |
| 007 | [Apollo people search](2026-11-17-ts-007-apollo-people-search.md) | 3 | 001, 008 | ✅ |
| 008 | [measure Apollo filters](2026-11-17-ts-008-measure-apollo-filters.md) | 3 | 004 | ✅ |
| 009 | [port the Decider](2026-11-17-ts-009-port-decider.md) | 4 | 001 | ✅ |
| 010 | [review queue](2026-11-17-ts-010-review-queue.md) | 4 | 009, 005 | ✅ |
| 011 | [contact reveal](2026-11-17-ts-011-contact-reveal.md) | 4 | 009 | ✅ |
| 012 | [HubSpot outbox](2026-11-17-ts-012-hubspot-outbox.md) | 5 | 009 | ✅ |
| 013 | [HubSpot properties](2026-11-17-ts-013-hubspot-properties.md) | 5 | 012 | 🟦 live test contact owed |
| 014 | [org snapshot](2026-11-17-ts-014-org-snapshot.md) | 6 | 001 | ✅ |
