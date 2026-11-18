---
title: "INSTANTLY_SEND is the Email switch"
slug: instantly-send-is-the-email-switch
aliases: [instantly-send-switch]
date: 2026-11-18
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 19
tags: [research, bindings]
---

# INSTANTLY_SEND is the Email switch

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-18-one-global-comms]], [[2026-11-18-connect-is-brochure]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v3_integrations]].

## Question

How does production pick the Email adapter — a mount, or an env boolean?

## Measurement (2026-11-18, tree at wave 7)

- `leadqualifier/bindings.py` L18–L24: `default_bindings()` starts Fake on every channel, then `if config.instantly_send_enabled():` replaces Email with `InstantlyEmail`. Voice is never swapped here.
- `leadqualifier/config.py` L84–L86: `instantly_send_enabled` is `INSTANTLY_SEND` in `{1,true,yes,on}` **and** key **and** campaign id.
- `get_bindings()` caches a singleton (`bindings.py` L27–L31). Nothing invalidates it after an env change. Process start is the only re-read.
- No sqlite table for a channel → plugin occupancy (grep `comms_mount` → 0).

## What is not known

Whether `INSTANTLY_SEND=1` has ever been true in a running process on this laptop. The live Instantly test remains skipped (`tests/test_comms.py`).

## Ticket this earns

[cl-012](../tickets/2026-11-18-cl-012-catalog-compose.md), [cl-014](../tickets/2026-11-18-cl-014-retire-instantly-send.md)
