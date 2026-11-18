---
title: "Draft body is a sentence, not an Offer"
slug: offer-is-untyped
aliases: [offer-gap]
date: 2026-11-18
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 13
tags: [research, playbook, offer]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v2_comms-layer.md
tickets: [cl-010]
---

# Draft body is a sentence, not an Offer

Hub: [[HANDOFF-MEMORY|hub]]. Cost already measured: [[2026-11-18-playbook-is-a-string]]. That note asked "channel or sentence?" This one asks "what leaves the building?"

## Question

Does the draft carry a case-study URL, a form, a calendar, or only filled copy?

## Finding

Only filled copy. `data/playbook.json` has `label`, `tiers`, `description`, `text` with `{first_name}` slots. Measured 2026-11-18: `rg 'https?://' data/playbook.json` → **0**. Control: the same `rg` on this file's own URL in the frontmatter is not the playbook; the playbook file is the subject.

`Draft` in `leadqualifier/workitem.fsx` L64–67 is `{ Channel; Body: string; CallSlots: string list }`. Call slots are string literals (`"Tuesday 11:00 CET"`), not a booking URL. `draft_from_result` in `workitem.py` L356–363 copies `next_action.text`.

There is no form. There is no website CTA as a value. A vendor that "sends the draft" sends a blob of prose.

## What is NOT known

Whether the owner wants a form, a calendar URL, or only copy plus a case-study URL. `Offer` must make a missing URL unspeakable for `CaseStudy` / `Form`, and keep `Copy of text` for a sentence with no asset. Do not invent URLs to make the happy path appear.
