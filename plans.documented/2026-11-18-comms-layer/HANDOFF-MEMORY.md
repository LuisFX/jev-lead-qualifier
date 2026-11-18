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

Queue and Hand off already authorize. Outbound is a typed draft on the work item. Channel is a pipe. Offer is what leaves. An operator mounts a plugin onto a slot. A vendor is a catalog file — never a destination, never an acceptance name.

Parent arc (intake, rank, handoff): [hub](../2026-11-17-intake-rank-handoff/HANDOFF-MEMORY.md). That glance stays SSOT for intake. This glance supersedes only "no sequencer is bound."

## TL;DR

This product still decides. It does not own Gmail, Twilio, Instantly, or a dialer. `QueuedForSequence` and `HandedToCloser` become `OutboundPending` of a `Draft`. Unmounted is Fake. Mounted is a plugin that declares `Send` of that channel. A reply is `RecordReply` of a non-empty body on the same work item.

Glance **v4** is the shape: `Channel`, `Offer`, `SendDecline`, `Capability = Send | Receive`, catalog files, `InboundMatch`. Glance v3 left SendDecline, Receive, Twilio, and live Email open. Glance v2 left composition as `INSTANTLY_SEND`. Glance v1 named Instantly as a destination; that ticket (cl-007) is retired.

## ⭐ RESUME HERE

2026-11-18. Waves 9–12 built. Glance v4 live. Live Instantly POST skipped: campaign id absent (key and test email present; lengths only). Live Twilio skipped: SID/token/from absent. LinkedIn Instantly absent; Twilio RVM forbidden; playbook 0 URLs. `architecture_settled: true`. cl-007 ⚠️.

**Do not** reopen cl-007 to "finish Instantly." HubSpot stays Relay/env, not the Connect board. Do not parse Instantly JSON in `decide` or in `inbound.py`. Do not invent LinkedIn, RVM, or CaseStudy/Form URLs.

Previous arc: paid Apollo People Search; HubSpot test contact (ts-013).

## Owner rulings

🧑 2026-11-17: *"I WANT THE A FULL PHASE THAT ENABLES COMMUNICATIONS (AKA: DIALER, MESSAGER, EMAILER)!!"*

🧑 2026-11-17, types over platforms: the types ARE the abstraction. No scraper ABC. No NotificationService.

🧑 2026-11-18: InstantlyComms as an acceptance name is a host leak. Channel is not a vendor. Refine glance, tickets, architecture. No smoke until the machinery is right.

🧑 2026-11-18: live senders are any, some, or all channels; configuration is admin-driven plugins; code-complete before live smoke; HubSpot stays Relay/env, not this board.

## Read order

| # | Doc |
| --- | --- |
| 1 | this hub |
| 2 | [[ARCHITECTURE-AT-A-GLANCE_v4_operational]] — current |
| 21 | [[ARCHITECTURE-AT-A-GLANCE_v3_integrations]] — superseded |
| 17 | [[ARCHITECTURE-AT-A-GLANCE_v2_comms-layer]] — superseded |
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
| 18 | [[2026-11-18-connect-is-brochure]] |
| 19 | [[2026-11-18-instantly-send-is-the-email-switch]] |
| 20 | [[2026-11-18-secrets-are-not-mounts]] |
| 22 | [[2026-11-18-instantly-is-not-linkedin]] |
| 23 | [[2026-11-18-twilio-is-not-rvm]] |
| 24 | [[2026-11-18-playbook-has-no-urls]] |
| 10 | [[2026-11-17-journal]] |
| 11 | [the board](tickets/INDEX.md) |

Oracles, outside the vault: `leadqualifier/workitem.fsx`, `leadqualifier/integrations.fsx`. Gate: `./run.sh oracles`.
