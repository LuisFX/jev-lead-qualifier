---
title: "ts-007 Apollo people search arrives as ApolloPerson"
slug: ts-007-apollo-people-search
aliases: [ts-007]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 3
depends_on: [ts-001, ts-008]
tags: [ticket, intake, apollo]
---

# ts-007 Apollo people search arrives as ApolloPerson

Hub: [[HANDOFF-MEMORY]]. Cost: [[2026-11-17-apollo-is-not-intake]]. Owner ruling: people search is in this arc.

## Acceptance

A search using `SearchFilters` from the live profile inserts work items with `Arrival = ApolloPerson personId`. The person id is Apollo's. A second search that returns the same person is `AlreadyArrived`. Organisation enrich is not this ticket. Email may still be hidden until disposition reveals contact.

## Progress and what is owed

- 2026-11-17: POST /api/search Arrive ApolloPerson. Email omitted from payload. Same person id → already_arrived. Live search skipped without APOLLO_API_KEY.
- 2026-11-18: browser Search Apollo with a key. `auth/health` 200; People Search 403 `AUTH.AUTHORIZATION.ENDPOINT_ACCESS_DENIED` (Free plan). Arrive path unchanged. The toast keys on `error_details.code`.
