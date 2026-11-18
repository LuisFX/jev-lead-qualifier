---
title: "Tombstones — comms layer"
slug: tombstones-comms-layer
aliases: [comms-tombstones]
date: 2026-11-18
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 16
tags: [tombstones]
---

# Tombstones — comms layer

Hub: [[HANDOFF-MEMORY|hub]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v2_comms-layer]].

| What | Lived | Replaced by | Status |
| --- | --- | --- | --- |
| Instantly as a glance destination / live-email **how** | [[ARCHITECTURE-AT-A-GLANCE_v1_comms-layer]] L27, L61 | Channel + host `Bindings` in [[ARCHITECTURE-AT-A-GLANCE_v2_comms-layer]] | 🪦 buried 2026-11-18 — host file `leadqualifier/instantly.py` is not an acceptance name |
| `InstantlyComms` as an acceptance name | [cl-007](tickets/2026-11-17-cl-007-instantly.md) | [cl-009](tickets/2026-11-18-cl-009-bindings-per-channel.md); host class `InstantlyEmail` | 🪦 buried 2026-11-18 |
| `default_comms` Instantly-or-Fake boolean | `leadqualifier/comms.py` (deleted) | `Bindings` / `default_bindings` Fake-all, Email key swappable | 🪦 buried 2026-11-18 |
| Glance v1 as SSOT | this arc's hub read order 2 | glance v2 | 🪦 v1 `status: superseded` 2026-11-18 |
| Inbound is paste as the **only** door | [[2026-11-18-inbound-is-paste]] | Two hosts of `RecordReply`: paste `/api/leads/{id}/reply` and match `/api/inbound` | 🪦 buried 2026-11-18 — paste remains a door |
