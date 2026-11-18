---
title: "RecordReply carries no text"
slug: record-reply-has-no-body
aliases: [reply-unit]
date: 2026-11-17
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 4
tags: [research, reply]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v1_comms-layer.md
tickets: [cl-002]
---

# RecordReply carries no text

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-18-queue-does-not-dispatch]].

## Question

Can a reply re-score a new message, or does Record a reply only flip disposition?

## Finding

Only disposition. `Command` is `| RecordReply` with no payload (`leadqualifier/workitem.fsx` line 88). `decide` returns `Ok [ ReplyArrived ]` (lines 151–152). `evolve` returns `Unreviewed` and keeps `Relay` (line 166, L19–L20). `encode_event` writes `reply_arrived` with `{}` (`leadqualifier/ledger.py` lines 66–67). The Lead `message` on `payload_json` is not updated. `assemble` therefore scores the original inbound text.

The UI button sends `{ kind: "record_reply" }` with no text (`web/index.html` line 171, `web/app.js` `sendCommand`). `CommandBody` has `kind`, `remote_id`, `reason` — no `text` (`leadqualifier/server.py`).

Control: `Arrive` carries `Arrival`; `MarkDelivered` carries `remoteId`. Reply is the unit command beside them.

## What is NOT known

Whether Instantly or Apollo reply webhooks will be the host of `RecordReply`. The inbound port is "host parses vendor webhook → RecordReply of body." No webhook is bound.

2026-11-18: the body is now on the event; the door is still paste — [[2026-11-18-inbound-is-paste]], cl-011. Do not name the vendor on the command.
