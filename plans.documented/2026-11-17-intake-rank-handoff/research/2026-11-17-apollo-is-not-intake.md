---
title: "Apollo in this repo is one enrich call"
slug: apollo-is-not-intake
aliases: [apollo-intake]
date: 2026-11-17
type: research
arc: 2026-11-17-intake-rank-handoff
status: live
read_order: 6
tags: [research, apollo]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v1_intake-rank-handoff.md
tickets: []
---

# Apollo in this repo is one enrich call

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-17-where-leads-live|where leads live]]. Longer mechanism note, outside the vault: [how First Read uses Apollo](../../../docs/engineering/apollo/2026-11-17-how-first-read-uses-apollo.md).

## Question

Does this process search Apollo for people?

## Finding

No. The only Apollo URL in `leadqualifier/` is `GET https://api.apollo.io/api/v1/organizations/enrich` (`leadqualifier/apollo.py` line 18). `POST /api/apollo/enrich` returns `apollo.enrich` (`leadqualifier/server.py` lines 396–398). The call is off unless `APOLLO_ENRICH` is on and `APOLLO_API_KEY` is set (`leadqualifier/config.py` `apollo_enabled`).

A search of `mixed_people` and `people.search` across `*.py`, `*.js`, `*.json`, `*.md` on 2026-11-17 hit no API route. The control is the organization-enrich URL above, which the same search family would have caught if it had been a people-search URL.

Success is written under `data/cache/apollo/{sha1(domain)[:16]}.json` with no lead id (`leadqualifier/apollo.py` `enrich`). Failures are not written. `DELETE /api/cache` clears `answers.json` only (`leadqualifier/server.py` `clear_cache`).

The 12 `apollo_export` leads are files. Count in [[2026-11-17-where-leads-live|where leads live]].

## What is NOT known

The current Apollo people-search path and whether its response includes an email. This session's doc lookup was blocked before a second pass. The product fact that stands without it: this repo does not call a people search.
