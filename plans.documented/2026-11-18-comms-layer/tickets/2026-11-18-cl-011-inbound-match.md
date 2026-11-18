---
title: "cl-011 InboundMatch then RecordReply"
slug: cl-011-inbound-match
aliases: [cl-011]
date: 2026-11-18
type: ticket
arc: 2026-11-18-comms-layer
status: done
wave: 7
depends_on: [cl-002]
tags: [ticket, inbound]
---

# cl-011 InboundMatch then RecordReply

Hub: [[HANDOFF-MEMORY]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v2_comms-layer]]. Cost: [[2026-11-18-inbound-is-paste]].

## Acceptance

Host parses a vendor event → `InboundMatch = Matched of WorkItemId | UnknownSender`. `Matched` applies `RecordReply` of the body. `UnknownSender` is a named refusal, not a new Arrival and not a silent drop. Operator paste remains a valid host of the same command (the body still goes through `RecordReply`). The concept never sees a vendor webhook type. Identity used to match is named (work item id the vendor already stored, or email / phone the payload already has) — one spelling, no `externalId`.

## Progress and what is owed

- Wave 7: oracle `matchInbound` L62–L68 (`leadqualifier/workitem.fsx` L106–L130, L662–L691). Floor 68. RED L63 miss-as-Matched failed then restored. `Open` still four parts. `Arrival` has no `Reply` case.
- Host `match_inbound` (`leadqualifier/inbound.py` L99). Scan of `payload_json`. Duplicate email → `UnknownSender`. `POST /api/inbound` (`leadqualifier/server.py` L618) 409 `unknown_sender`. Paste `POST /api/leads/{id}/reply` still 404 unknown id / 409 `empty_reply`. `rg Instantly` / `externalId` on `inbound.py` → 0.
- Fake smoke `:8785` 2026-11-18: unknown_sender named; paste L001 still works; CSV email match folds the body. Closed 2026-11-18.
