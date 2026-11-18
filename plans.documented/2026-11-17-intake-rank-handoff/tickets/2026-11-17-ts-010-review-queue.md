---
title: "ts-010 Review queue and disposition commands"
slug: ts-010-review-queue
aliases: [ts-010]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 4
depends_on: [ts-009, ts-005]
tags: [ticket, disposition]
---

# ts-010 Review queue and disposition commands

Hub: [[HANDOFF-MEMORY]]. Design: [[ARCHITECTURE]] §5 Elmish.

## Acceptance

`#review` lists `HeldForHuman`. The lead page offers Flag, Dismiss, Queue, HandOff as commands. `needs_review` from `assemble` may emit `Flag` after a judgement. It is not the stored disposition. Reload keeps the disposition.

## Progress and what is owed

- 2026-11-17: GET /api/review lists HeldForHuman. After assemble, Flag when needs_review. Lead commands + `#review`. Reload keeps disposition.
