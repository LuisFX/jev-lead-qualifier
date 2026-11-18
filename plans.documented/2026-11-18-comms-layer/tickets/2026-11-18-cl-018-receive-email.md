---
title: "cl-018 Receive Email"
slug: cl-018-receive-email
aliases: [cl-018]
date: 2026-11-18
type: ticket
arc: 2026-11-18-comms-layer
status: done
wave: 12
depends_on: [cl-011, cl-012]
tags: [ticket, receive]
---

# cl-018 Receive Email

Hub: [[HANDOFF-MEMORY]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v4_operational]]. Board: [INDEX](INDEX.md).

## Acceptance

Oracle integrations: `Receive of Channel`; Email receive candidates; Voice receive empty. sqlite receive occupancy (additive; do not overload Out PK). Absence = Unmounted. Host parser beside Instantly, **not** in `inbound.py` (`rg Instantly` on inbound.py stays 0): map `event_type=reply_received` → `ByEmail lead_email` + body `reply_text`. Other event types: 204 ignore (not `unknown_sender`). Empty reply: existing `empty_reply`. `POST /api/receive/email` only when Receive Email is mounted; else 404. Then `match_inbound` as today. Connect Inputs: one Email In card (Fake/unmounted vs plugin id). HubSpot still one line of copy, not a card. Tests: fixture Instantly payload → paste-equivalent fold; unknown email 409; inbound.py still vendor-blind. Live webhook is the owner's Instantly campaign pointing at a reachable URL — not this laptop smoke unless they say so. `decide` never sees vendor JSON. `Arrival` still has no `Reply` case.

## Progress and what is owed

- Wave 12: `Receive of Channel`. sqlite `comms_receive`. Parser `instantly_inbound.py`. Unmounted 404; `email_opened` 204; `reply_received` folds. `rg Instantly leadqualifier/inbound.py` → 0. Closed 2026-11-18.
