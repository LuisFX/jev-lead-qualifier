---
title: "Where the 65 leads live"
slug: where-leads-live
aliases: [lead-census]
date: 2026-11-17
type: research
arc: 2026-11-17-intake-rank-handoff
status: live
read_order: 3
tags: [research, leads, census]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v1_intake-rank-handoff.md
tickets: []
---

# Where the 65 leads live

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-17-apollo-is-not-intake|Apollo is not intake]].

## Question

Are the leads a store a user can add to, or a fixed demo folder?

## Finding

They are 65 JSON files in `data/leads/`, loaded by `load_leads` (`leadqualifier/leads.py`). A `Lead` is `id`, `source`, `received_at`, `person`, `company`, `message`, `tags` (`leadqualifier/leads.py` around the dataclass). There is no insert route. `rg` for `sqlite` / `SQLite` across `*.py`, `*.toml`, `*.md`, `*.js` on 2026-11-17 returned no matches. The control is `pyproject.toml`, which depends on `fastapi`, `uvicorn`, and `httpx` only.

Counted 2026-11-17 by [2026-11-17-count-lead-sources.py](tools/2026-11-17-count-lead-sources.py) from the repo root:

| source | n |
| --- | ---: |
| website_form | 18 |
| email_reply | 15 |
| apollo_export | 12 |
| linkedin_export | 9 |
| linkedin_dm | 6 |
| instantly_reply | 4 |
| referral | 1 |
| **total** | **65** |

`data/crm.json` has 12 accounts. Presets on disk: `b2b_saas_founders`, `ecommerce_brands`, `lanternfield_agencies`.

`apollo_export` is a string on those 12 files. Nothing in `leadqualifier/` fetches them.

## What is NOT known

Whether a running server has written any lead file since clone. This count is the tree on disk, not a request log.
