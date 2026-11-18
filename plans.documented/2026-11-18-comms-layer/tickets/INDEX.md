---
title: "Board — comms layer"
slug: board-comms-layer
aliases: [comms-board]
date: 2026-11-17
type: ticket-index
arc: 2026-11-18-comms-layer
status: live
read_order: 11
tags: [board]
---

# Board — comms layer

Hub: [[HANDOFF-MEMORY]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v3_integrations]] (v2 superseded). Design: [[ARCHITECTURE]]. Tombstones: [[TOMBSTONES]].

## Legend

| Symbol | Meaning |
| --- | --- |
| ✅ | done |
| 🟦 | code done and smoked locally, closes on the deploy smoke |
| ◑ | partly done, what is owed is named |
| ⬜ | open |
| ❓ | waits on an owner ruling |
| ⚠️ | superseded; replacement named |
| ✈ | a deploy, only on the owner's word |

## Waves

| Wave | Tickets | The smoke that closes the wave | Status |
| --- | --- | --- | --- |
| 0 · Confirm glance v1 | none | Owner executed the follow-through plan | ✅ 2026-11-17 |
| 1 · Oracle (v1 Channel) | cl-001 cl-002 cl-003 cl-004 | `dotnet fsi leadqualifier/workitem.fsx` 0 failed | ✅ 2026-11-18 |
| 2 · Host + FakeComms | cl-001 cl-002 cl-005 | Queue of Warm records FakeComms | ✅ 2026-11-18 |
| 3 · Elmish | cl-003 cl-006 | Browser FIRSTREAD_FAKE=1 Queue, reply, HandOff | ✅ 2026-11-18 |
| 4 · Instantly-named ticket | cl-007 | — | ⚠️ retired; see cl-009 |
| 5 · Channel + Offer | cl-008 cl-010 | `dotnet fsi leadqualifier/workitem.fsx` 0 failed, floor up | ✅ 2026-11-18 |
| 6 · Bindings per channel | cl-009 | Fake per channel; Email adapter does not mention Voice | ✅ 2026-11-18 |
| 7 · Inbound match | cl-011 | UnknownSender named; paste still works | ✅ 2026-11-18 |
| 8 · Catalog, mounts, Connect | cl-012 cl-013 cl-014 | Fake Connect smoke: five slots, mount Email, `plugin_unready`, unmount Fake, Voice 409 | ✅ 2026-11-18 |

## Tickets

| # | Ticket | Wave | Depends on | Status |
| --- | --- | --- | --- | --- |
| 001 | [Queue emits OutboundPending](2026-11-17-cl-001-queue-outbound.md) | 1, 2 | — | ✅ |
| 002 | [RecordReply of body](2026-11-17-cl-002-reply-body.md) | 1, 2 | — | ✅ |
| 003 | [Channel on the draft](2026-11-17-cl-003-channel.md) | 1, 3 | — | ✅ |
| 004 | [Outbound beside Relay](2026-11-17-cl-004-outbound-slot.md) | 1 | — | ✅ |
| 005 | [no_address is not a send](2026-11-17-cl-005-no-address.md) | 2 | 001 | ✅ |
| 006 | [Lead view shows outbox + reply](2026-11-17-cl-006-elmish.md) | 3 | 001, 002, 003 | ✅ |
| 007 | [InstantlyComms as acceptance — retired](2026-11-17-cl-007-instantly.md) | 4 | 001, 005 | ⚠️ cl-009 |
| 008 | [Channel includes Sms and RinglessVoicemail](2026-11-18-cl-008-channel-widen.md) | 5 | — | ✅ |
| 009 | [Bindings per channel](2026-11-18-cl-009-bindings-per-channel.md) | 6 | 008 | ✅ |
| 010 | [Draft carries Offer](2026-11-18-cl-010-offer.md) | 5 | — | ✅ |
| 011 | [InboundMatch then RecordReply](2026-11-18-cl-011-inbound-match.md) | 7 | 002 | ✅ |
| 012 | [Catalog, mounts, compose](2026-11-18-cl-012-catalog-compose.md) | 8 | 009 | ✅ |
| 013 | [Connect is the mount board](2026-11-18-cl-013-connect-board.md) | 8 | 012 | ✅ |
| 014 | [Retire INSTANTLY_SEND as the Email switch](2026-11-18-cl-014-retire-instantly-send.md) | 8 | 012 | ✅ |
