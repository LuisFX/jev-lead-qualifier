---
title: "Tombstones — intake, rank, handoff"
slug: tombstones-intake-rank-handoff
aliases: [tombstones]
date: 2026-11-17
type: research
arc: 2026-11-17-intake-rank-handoff
status: live
read_order: 9
tags: [tombstones]
---

# Tombstones

Hub: [[HANDOFF-MEMORY|hub]]. The glance that names these rows: [[ARCHITECTURE-AT-A-GLANCE_v1_intake-rank-handoff|v1 glance]].

Nothing is buried. Each row is planned. A burial flips ⚰️ to 🪦 with the commit and a zero-reference count that has a control.

| Id | ⚰️ planned | Where it lives now | What replaces it |
| --- | --- | --- | --- |
| T1 | The 65 JSON files as the lead store | `data/leads/*.json`, loaded by `leadqualifier/leads.py` | A work-item row whose birth is an Apollo person or a CSV row. A reply is `ReplyArrived` on that item |
| T2 | One live ICP file, replaced on every save | `data/icp.json` via `icp.save` | Named profile versions. An answer keeps the version id it was judged under |
| T3 | Answer file flushed after the batch | `data/cache/answers.json`, `ResultCache.save` at the end of `score_many` | One answer row written when Jev returns, keyed by lead, question id, and fingerprint |
| T4 | Twelve fictional accounts as the CRM read | `data/crm.json` | The closer's HubSpot companies, read for dedupe. Buried only when that read is the one the scorer uses |
| T5 | Connect output card that claims an API write | `web/app.js` `OUTPUTS` | A HubSpot outbox item: properties on the contact, or a note when the account already exists |
| T6 | Enrichment filed only by domain hash | `data/cache/apollo/*.json` | The organisation snapshot stored on the account, with the time it was fetched |

Left standing on purpose: `leadqualifier/scoring.py`, `data/gold.json`, `data/playbook.json`, and the demo page. Gold is a fixture. The playbook still only drafts a sentence. This arc does not send it.
