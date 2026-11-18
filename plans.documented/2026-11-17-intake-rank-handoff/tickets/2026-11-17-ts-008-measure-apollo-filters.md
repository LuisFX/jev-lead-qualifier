---
title: "ts-008 Measure the profile to Apollo filter map"
slug: ts-008-measure-apollo-filters
aliases: [ts-008]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 3
depends_on: [ts-004]
tags: [ticket, intake, apollo, research]
---

# ts-008 Measure the profile to Apollo filter map

Hub: [[HANDOFF-MEMORY]]. Design: [[ARCHITECTURE]] §1 settled list.

## Acceptance

A research file names the People Search path, the filter fields this product will send, and whether the email is present on the search hit. A probe in `research/tools/` is SELECT-equivalent (read-only against Apollo) and cites status codes, not guesses. The port type `Profile → SearchFilters` is written from that measurement. No invented industry ids.

## Progress and what is owed

- 2026-11-17: [[2026-11-17-apollo-people-search]] — POST mixed_people/api_search, x-api-key, no email on the hit. `SearchFilters` in the oracle (L34–L36). No industry tag ids.
