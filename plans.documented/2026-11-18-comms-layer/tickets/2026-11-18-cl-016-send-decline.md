---
title: "cl-016 SendDecline"
slug: cl-016-send-decline
aliases: [cl-016]
date: 2026-11-18
type: ticket
arc: 2026-11-18-comms-layer
status: done
wave: 10
depends_on: [cl-010]
tags: [ticket, send-decline]
---

# cl-016 SendDecline

Hub: [[HANDOFF-MEMORY]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v4_operational]]. Board: [INDEX](INDEX.md).

## Acceptance

Oracle `leadqualifier/workitem.fsx`: `Command.SendDecline of Draft`. RED: Disqualify + nonempty DeclineDraft currently has no command that emits `OutboundPending`. Floor up in the same commit as the laws. Host + HTTP `POST /api/leads/{id}/command` `{kind: send_decline}` fills `decline_draft()` from playbook `decline_politely`. Elmish: one button on a Disqualify lead; `seq` drops stale. Drain uses whatever Email slot is mounted (Fake or plugin). Empty DeclineDraft is `EmptyDraft`. Any other Offer is `NotSendable`. Not Disqualify is `NotSequenceable`. Contact stays Hidden on Dismissed. Nurture stays `NoSend`. Vendor words stay out of the oracle.

## Progress and what is owed

- Wave 10: oracle RED then floor 75. Host + HTTP `send_decline` + Elmish button. Fake smoke disqualify → `dismissed` + `fake-comms-1` + contact Hidden. Closed 2026-11-18.
