---
title: "cl-001 Queue emits OutboundPending"
slug: cl-001-queue-outbound
aliases: [cl-001]
date: 2026-11-17
type: ticket
arc: 2026-11-18-comms-layer
status: done
wave: 1
depends_on: []
tags: [ticket, queue]
---

# cl-001 Queue emits OutboundPending

Hub: [[HANDOFF-MEMORY]]. Cost: [[2026-11-18-queue-does-not-dispatch]].

## Acceptance

`Queue` of Warm or Hot from Unreviewed or HeldForHuman emits `Queued` then `OutboundPending` of the command's `Draft`. Nurture emits `Queued` only (`NoSend`). Disqualify / Existing stay `not_sequenceable` with `NoSend`. FakeComms records one dispatch on drain. A second Queue is still `not_queueable` and does not enqueue again.

## Progress and what is owed

- Wave 1: oracle laws Queue Warm → OutboundPending Email; Nurture NoSend; second Queue `not_queueable`. Floor 48.
- Wave 2: `draft_for_queue`, FakeComms drain, sqlite `outbound_*`. Closed 2026-11-18.
