---
title: "HubSpot is a sentence on the Connect page"
slug: crm-and-hubspot-are-copy
aliases: [hubspot-copy]
date: 2026-11-17
type: research
arc: 2026-11-17-intake-rank-handoff
status: live
read_order: 7
tags: [research, crm, hubspot]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v1_intake-rank-handoff.md
tickets: []
---

# HubSpot is a sentence on the Connect page

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-17-apollo-is-not-intake|Apollo is not intake]].

## Question

Is there a CRM write, and is `data/crm.json` that CRM?

## Finding

Two different things wear the word CRM.

**Read, local, used.** `data/crm.json` has 12 accounts (census in [[2026-11-17-where-leads-live|where leads live]]). `dedupe.shortlist` scores them against a lead (`leadqualifier/dedupe.py`). `same_account` is a Jev Choice over that shortlist. `existing_account` in `leadqualifier/scoring.py` promotes a tier only when the chosen probability clears `dedupe_p`.

**Write, described, unused.** `web/app.js` lines 670–671 build the Connect cards from two constant arrays. The output card "HubSpot · Pipedrive · Attio" says tier, route, fit, intent, primary pain, reasons, and next action are written as properties, and an existing account gets a note. The pill text is the literal `API`. No Python module imports a HubSpot client. A search for `HubSpot` on 2026-11-17 hits `web/app.js`, `README.md`, the Apollo engineering note, and the word "HubSpot" inside one fictional lead's services list (`data/leads/L002.json`, `scripts/make_dataset.py`). It hits no client.

## What is NOT known

Which HubSpot account, portal, or property names a real closer would use. None are configured here.
