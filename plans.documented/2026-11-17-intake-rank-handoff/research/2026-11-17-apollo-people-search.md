---
title: Apollo People Search — measured contract
slug: 2026-11-17-apollo-people-search
aliases: [apollo-people-search]
date: 2026-11-17
type: research
arc: 2026-11-17-intake-rank-handoff
status: live
read_order: 20
tags: [apollo, intake, ts-008]
---

# Apollo People Search (ts-008)

Hub: [[HANDOFF-MEMORY]]

Measured from Apollo's REST reference (`/websites/apollo_io_reference`, People API Search) on 2026-11-17. This is the contract the host ports. We do **not** invent industry tag ids.

## Path

`POST https://api.apollo.io/api/v1/mixed_people/api_search`

## Auth

Header `x-api-key` (same as organisation enrich). `Content-Type: application/json`. `Cache-Control: no-cache`.

## Filters we send (from the live ICP, `SearchFilters`)

| ICP | Apollo field | Notes |
|---|---|---|
| persona titles (slug → words, or `title` if present) | `person_titles` | Match-one; similar titles included unless we later set `include_similar_titles: false` |
| geography, unless `anywhere` | `person_locations` | Cities / countries / postcodes. Empty list → omit the field |
| (none yet) | `organization_num_employees_ranges` | Record field exists; we send it only when the host fills it |
| (none yet) | `q_keywords` | Same |

We do **not** send `organization_industry_tag_ids`. Those ids are Apollo's, not ours.

## Email on the hit?

**No.** The documented contract: this endpoint does not return email addresses or phone numbers. `Arrive (ApolloPerson personId)` stores the person without email. `contactOf` stays Hidden until a later reveal.

## Status

A successful search is HTTP 200 with a `people` (or `contacts`) array. 422 when title-filter cardinality exceeds Apollo's cap (~100 unique titles). Failures are not cached.

Measured 2026-11-18 against this workspace's key (length only: 22; value never logged). The key's endpoint checkboxes match these statuses.

| path | this key | HTTP | what it searches | this workspace |
| --- | --- | --- | --- | --- |
| `GET /api/v1/auth/health` | — | 200 | auth | `is_logged_in` |
| `POST /api/v1/mixed_people/api_search` | off | 403 `ENDPOINT_ACCESS_DENIED` | net-new **people** in Apollo's database | unreachable on Free |
| `POST /api/v1/mixed_companies/search` | off | 403 same | net-new **companies** in Apollo's database (docs name) | unreachable on Free |
| `POST /api/v1/organizations/search` | on | 200 | companies in Apollo's database (older path) | `total_entries` 48411 for keyword `marketing agency`; a company row, not a person |
| `POST /api/v1/contacts/search` | on | 200 | people **already saved** in this Apollo account | `total_entries` **0** |
| `POST /api/v1/accounts/search` | on | 200 | companies **already saved** in this Apollo account | `total_entries` **0** |
| `GET /api/v1/organizations/enrich` | — | 200 | one company by domain | already wired, behind `APOLLO_ENRICH=1` |

Apollo's message on the two 403s: those endpoints are not on the Free plan, even with a master key. The host surfaces `error_details.code` on the 502 toast. We did not switch People Search to contacts/search: that is a different database (your saved contacts), and it is empty here.

Live ICP `geography` is a DACH/UK sentence. `geography_for_search` treats that as `anywhere` so `person_locations` is omitted.

## What this is not

Organisation enrich (`/api/v1/organizations/enrich`) is a different call, behind `APOLLO_ENRICH=1`, and writes `account_snapshot` (ts-014). People Search is intake (ts-007).
