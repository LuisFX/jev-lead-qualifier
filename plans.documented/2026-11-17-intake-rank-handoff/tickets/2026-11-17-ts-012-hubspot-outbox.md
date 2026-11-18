---
title: "ts-012 HubSpot relay as an outbox"
slug: ts-012-hubspot-outbox
aliases: [ts-012]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 5
depends_on: [ts-009]
tags: [ticket, hubspot]
---

# ts-012 HubSpot relay as an outbox

Hub: [[HANDOFF-MEMORY]]. Cost: [[2026-11-17-crm-and-hubspot-are-copy]]. Tombstone T5. Oracle L14, L15, L27, L28.

## Acceptance

`HandOff` of Hot writes `Relay = Pending`. A worker delivers, then `MarkDelivered` or `MarkFailed`. Idempotent on work item id and profile version. A second HandOff is `AlreadyHandedOff` and does not enqueue. No HubSpot call from `assemble`.

## Progress and what is owed

- 2026-11-17: Relay worker drains pending → MarkDelivered / MarkFailed. Second HandOff is already_handed_off and does not write (FakeWriter).
