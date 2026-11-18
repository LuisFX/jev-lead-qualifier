---
title: "Queue writes disposition, not a send"
slug: queue-does-not-dispatch
aliases: [queue-no-send]
date: 2026-11-17
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 3
tags: [research, queue, outbox]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v1_comms-layer.md
tickets: [cl-001]
---

# Queue writes disposition, not a send

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-18-relay-is-one-slot]].

## Question

When the operator presses Queue sequence, does anything leave this process?

## Finding

No. `decide` of `Queue` on Warm / Hot / Nurture from Unreviewed or HeldForHuman returns `Ok [ Queued ]` only (`leadqualifier/workitem.fsx` lines 134–135, L9–L11). `evolve` sets `QueuedForSequence` and leaves `Relay` untouched (line 164). The Python port matches (`leadqualifier/workitem.py` `Queue` → `_ok(Queued())`). HTTP `POST /api/leads/{id}/command` `{kind: queue}` applies that command and returns the lead (`leadqualifier/server.py` `lead_command`). There is no sequencer call, no outbox row, no FakeComms.

Control (a send that does exist): `HandOff` of Hot emits `RelayPending` and `leadqualifier/relay.py` `drain_once` calls `Writer.write`. Queue has no twin of that drain.

## What is NOT known

Whether an operator believed Queue already enrolled Instantly. Connect copy still says "SDR sequence A" as a pill (`web/app.js` `OUTPUTS`). That is copy, not a write.
