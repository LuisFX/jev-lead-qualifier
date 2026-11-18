---
title: "needs_review is recomputed, not stored"
slug: disposition-is-a-score
aliases: [no-disposition]
date: 2026-11-17
type: research
arc: 2026-11-17-intake-rank-handoff
status: live
read_order: 8
tags: [research, disposition]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v1_intake-rank-handoff.md
tickets: []
---

# needs_review is recomputed, not stored

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-17-icp-is-one-file|the ICP is one file]].

## Question

Can a person accept, dismiss, or hand off a lead and have that decision still be there tomorrow?

## Finding

No. `gate` sets `needs_review` from confidence, borderline scores, a weak disqualifier, a weak CRM match, or a PII request (`leadqualifier/scoring.py` `gate`). `assemble` copies that onto the result and, when it is set, puts `hold` on the route. The result is rebuilt by `Qualifier.rescore` from cached answers. Nothing writes `accepted`, `dismissed`, or `handed_off` onto the lead. The `Lead` record has no such field (`leadqualifier/leads.py` dataclass).

The playbook fills a draft string (`data/playbook.json`, `pick_action` in `leadqualifier/scoring.py`). No sender is called.

## What is NOT known

Whether the browser keeps a click in `localStorage`. `web/app.js` keeps results in the page `state` object for the session. A reload calls `/api/results`, which re-scores from the answer file.
