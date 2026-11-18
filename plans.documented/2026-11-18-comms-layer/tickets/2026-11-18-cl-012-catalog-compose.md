---
title: "cl-012 Catalog, mounts, compose"
slug: cl-012-catalog-compose
aliases: [cl-012]
date: 2026-11-18
type: ticket
arc: 2026-11-18-comms-layer
status: done
wave: 8
depends_on: [cl-009]
tags: [ticket, integrations]
---

# cl-012 Catalog, mounts, compose

Hub: [[HANDOFF-MEMORY]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v3_integrations]]. Cost: [[2026-11-18-instantly-send-is-the-email-switch]], [[2026-11-18-secrets-are-not-mounts]]. Board: [INDEX](INDEX.md).

## Acceptance

`Catalog = Map PluginId → Set Capability`. `Capability = Send of Channel`. `Mounts = Map Channel → Unmounted | Mounted of PluginId`. `compose` is total on Channel: Unmounted → Fake; Mounted → that plugin only if `Send ch` is in its set. Unknown PluginId and capability mismatch are named errors, not silent Fake. sqlite `comms_mount` stores occupancy; absence is Unmounted; `"fake"` is not a plugin id. Keys stay in env. Mounted + not ready raises `plugin_unready` on dispatch. Vendor words are zero in both `.fsx` files. InstantlyEmail is a catalog factory for Email, not an acceptance name.

## Progress and what is owed

- Wave 8: oracle `leadqualifier/integrations.fsx` floor 6, 0 failed. RED L3 capability-mismatch. Host `leadqualifier/integrations.py`, sqlite `comms_mount`, `compose_from_ledger`. Drain `plugin_unready`. InstantlyEmail catalog-only. Closed 2026-11-18 with cl-013 and cl-014.
