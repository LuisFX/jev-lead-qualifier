---
title: "The live ICP is one file"
slug: icp-is-one-file
aliases: [one-icp]
date: 2026-11-17
type: research
arc: 2026-11-17-intake-rank-handoff
status: live
read_order: 5
tags: [research, icp]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v1_intake-rank-handoff.md
tickets: []
---

# The live ICP is one file

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-17-disposition-is-a-score|disposition is a score]].

## Question

Can the product keep "plumbers" and "insurance agencies" as two saved profiles?

## Finding

No. `icp.save` validates and replaces `data/icp.json` (`leadqualifier/icp.py` lines 53–59). `POST /api/icp/presets/{id}` loads a preset and saves it over that same file (`leadqualifier/server.py` line 364). `reset` writes the default preset the same way (`leadqualifier/icp.py` lines 62–63).

The editor can already express a new target. Industries, personas, pains, and disqualifiers are the question criteria (`web/app.js` `renderICPForm`, list sections). A wording change changes a fingerprint. A weight or threshold does not, and `POST /api/rescore` re-tiers from cache (`leadqualifier/server.py` `rescore`).

Three preset files exist. See the census in [[2026-11-17-where-leads-live|where leads live]]. Loading one discards the previous live file's bytes except what git or the temp-replace crash window still holds. There is no version id on a saved profile and no version id stored beside an answer.

## What is NOT known

Whether `data/icp.json.bak` is ever written. `.gitignore` mentions it. `icp.save` as read on 2026-11-17 does not create a `.bak`.
