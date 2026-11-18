---
title: "Comms layer — hub"
slug: handoff-memory-comms-layer
aliases: [comms-hub]
date: 2026-11-17
type: handoff
arc: 2026-11-18-comms-layer
status: live
read_order: 1
branch: { jev-lead-qualifier: main }
tags: [hub, comms, outbox, elmish]
architecture_settled: true
tickets_cut: true
---

# Comms layer

Queue and Hand off already authorize. Outbound is a typed draft on the work item. Channel is a pipe. Offer is what leaves. A vendor is a host binding — never a destination, never an acceptance name.

Parent arc (intake, rank, handoff): [hub](../2026-11-17-intake-rank-handoff/HANDOFF-MEMORY.md). That glance stays SSOT for intake. This glance supersedes only "no sequencer is bound."

## TL;DR

This product still decides. It does not own Gmail, Twilio, Instantly, or a dialer. `QueuedForSequence` and `HandedToCloser` become `OutboundPending` of a `Draft`. FakeComms is the default host per channel. A reply is `RecordReply` of a non-empty body on the same work item.

Glance **v2** is the shape: `Channel`, `Offer`, `Map<Channel, Comms>`, `InboundMatch`. Glance v1 named Instantly as a destination; that ticket (cl-007) is retired.

## ⭐ RESUME HERE

2026-11-18. Wave 7 built: InboundMatch, floor 68, 409 `unknown_sender`, paste still works. cl-011 done. cl-007 ⚠️. Glance types are in the host. `architecture_settled: true`. Remaining opens are operational (named vendor, Form/CaseStudy URLs, `SendDecline`).

**Do not** reopen cl-007 to "finish Instantly." Email live send waits on a vendor the owner **names**, behind env, test address only. A named vendor file may POST `/api/inbound`; do not parse Instantly JSON in `decide`.

Previous arc: paid Apollo People Search; HubSpot test contact (ts-013).

## Owner rulings

🧑 2026-11-17: *"I WANT THE A FULL PHASE THAT ENABLES COMMUNICATIONS (AKA: DIALER, MESSAGER, EMAILER)!!"*

🧑 2026-11-17, types over platforms: the types ARE the abstraction. No scraper ABC. No NotificationService.

🧑 2026-11-18: InstantlyComms as an acceptance name is a host leak. Channel is not a vendor. Refine glance, tickets, architecture. No smoke until the machinery is right.

## Read order

| # | Doc |
| --- | --- |
| 1 | this hub |
| 2 | [[ARCHITECTURE-AT-A-GLANCE_v2_comms-layer]] — current |
| 15 | [[ARCHITECTURE-AT-A-GLANCE_v1_comms-layer]] — superseded |
| 12 | [[ARCHITECTURE]] |
| 16 | [[TOMBSTONES]] |
| 3 | [[2026-11-18-queue-does-not-dispatch]] |
| 4 | [[2026-11-18-record-reply-has-no-body]] |
| 5 | [[2026-11-18-playbook-is-a-string]] |
| 6 | [[2026-11-18-relay-is-one-slot]] |
| 7 | [[2026-11-18-reveal-can-be-empty]] |
| 8 | [[2026-11-18-instantly-named-as-destination]] |
| 9 | [[2026-11-18-one-global-comms]] |
| 13 | [[2026-11-18-offer-is-untyped]] |
| 14 | [[2026-11-18-inbound-is-paste]] |
| 10 | [[2026-11-17-journal]] |
| 11 | [the board](tickets/INDEX.md) |

Oracle, outside the vault: `leadqualifier/workitem.fsx`. Gate: `./run.sh oracles`.
