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

Hub: [[HANDOFF-MEMORY|hub]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v4_operational]].

| What | Lived | Replaced by | Status |
| --- | --- | --- | --- |
| Instantly as a glance destination / live-email **how** | [[ARCHITECTURE-AT-A-GLANCE_v1_comms-layer]] L27, L61 | Channel + host `Bindings` in [[ARCHITECTURE-AT-A-GLANCE_v2_comms-layer]] | 🪦 buried 2026-11-18 — host file `leadqualifier/instantly.py` is not an acceptance name |
| `InstantlyComms` as an acceptance name | [cl-007](tickets/2026-11-17-cl-007-instantly.md) | [cl-009](tickets/2026-11-18-cl-009-bindings-per-channel.md); host class `InstantlyEmail` | 🪦 buried 2026-11-18 |
| `default_comms` Instantly-or-Fake boolean | `leadqualifier/comms.py` (deleted) | `Bindings` / `default_bindings` Fake-all, Email key swappable | 🪦 buried 2026-11-18 |
| Glance v1 as SSOT | this arc's hub read order 2 | glance v2 | 🪦 v1 `status: superseded` 2026-11-18 |
| Inbound is paste as the **only** door | [[2026-11-18-inbound-is-paste]] | Two hosts of `RecordReply`: paste `/api/leads/{id}/reply` and match `/api/inbound` | 🪦 buried 2026-11-18 — paste remains a door |
| `INSTANTLY_SEND` as the Email switch | `leadqualifier/bindings.py` `default_bindings`; `config.instantly_send_enabled` | sqlite `comms_mount` + `compose`; ready is key + campaign id | 🪦 buried 2026-11-18 — `rg INSTANTLY_SEND leadqualifier/bindings.py` → 0. `instantly_send_enabled` deleted 2026-11-18 |
| `default_bindings` Instantly-or-Fake boolean | `leadqualifier/bindings.py` L18–L24 (wave 6) | `compose(catalog, load_mounts())`; Fake fills Unmounted | 🪦 buried 2026-11-18 |
| Connect brochure as the integrations UX | `web/app.js` `renderConnect` INPUTS/OUTPUTS literals | five Channel Out cards; Mount / Unmount; HubSpot is one line of copy | 🪦 buried 2026-11-18 |
| Glance v2 as SSOT | this arc's hub read order 2 | glance v3 | 🪦 v2 `status: superseded` 2026-11-18 |
| Glance v3 as SSOT | this arc's hub read order 2 | glance v4 | 🪦 v3 `status: superseded` 2026-11-18 |
| `INSTANTLY_SEND` as the live Instantly skip | `tests/test_comms.py` skipif | skip unless key + campaign + `INSTANTLY_TEST_EMAIL` | 🪦 buried 2026-11-18 — `rg INSTANTLY_SEND tests/test_comms.py` → 0 |
| Instantly as LinkedIn Out | temptation to reuse create-lead | Channel `LinkedIn` stays Fake | 🪦 STOP cl-019 — create-lead with `campaign` requires `email` |
| Twilio as RinglessVoicemail | temptation to reuse Calls.json | Channel `RinglessVoicemail` stays Fake | 🪦 STOP cl-020 — Twilio ToS forbids RVM |
| Invented CaseStudy / Form URLs | empty `data/playbook.json` | `offer_for_action` stays Copy | 🪦 wait — [[2026-11-18-playbook-has-no-urls]] |
