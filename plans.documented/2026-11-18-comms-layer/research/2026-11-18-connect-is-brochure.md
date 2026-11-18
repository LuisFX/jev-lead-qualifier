---
title: "Connect is brochure copy"
slug: connect-is-brochure
aliases: [connect-brochure]
date: 2026-11-18
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 18
tags: [research, connect]
---

# Connect is brochure copy

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-18-instantly-send-is-the-email-switch]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v3_integrations]].

## Question

Does `#connect` mount a provider onto a Channel slot, or does it render static marketing copy?

## Measurement (2026-11-18, tree at wave 7)

- `web/app.js` `renderConnect` (L727–L738): `INPUTS` and `OUTPUTS` are four hardcoded triples. Pills are the literals `"webhook · CSV"` and `"API"`. No fetch of mounts. No Mount / Unmount.
- `web/index.html` L282–L297: Connect **Outputs** is "Where decisions go". The card is a brochure list, not five Channel Out slots.
- `/api/status` (`leadqualifier/server.py` L207): `instantly.send` boolean. The page reads it as a kv line (`web/app.js` L737–L738), not as a slot occupancy.
- No `/api/integrations` route (grep of `leadqualifier/server.py`).

## What is not known

Whether an operator has ever treated that page as configuration. The code cannot store a mount.

## Ticket this earns

[cl-013](../tickets/2026-11-18-cl-013-connect-board.md)
