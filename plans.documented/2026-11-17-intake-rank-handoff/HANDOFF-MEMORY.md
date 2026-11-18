---
title: "Intake, rank, handoff — hub"
slug: handoff-memory
aliases: [hub, intake-rank-handoff]
date: 2026-11-17
type: handoff
arc: 2026-11-17-intake-rank-handoff
status: live
read_order: 1
branch: { jev-lead-qualifier: main }
tags: [hub, intake, apollo, hubspot]
architecture_settled: true
tickets_cut: true
engineering_docs:
  - jev-lead-qualifier:docs/engineering/ARCHITECTURE.md
  - jev-lead-qualifier:docs/engineering/ARCHITECTURE-AT-A-GLANCE-v1.md
  - jev-lead-qualifier:docs/engineering/apollo/2026-11-17-how-first-read-uses-apollo.md
---

# Intake, rank, handoff

A saved profile names who we are hunting. Apollo people search fills the list. The existing scorer ranks each person. A hot judgement is written to HubSpot for a closer. This product does not send the email or place the call.

## TL;DR

Glance v1 is confirmed. The architecture is folded. The work-item oracle is 36 laws, 0 failed. Waves 1–6 are in the host: sqlite ledger, ICP versions, CSV + People Search Arrive, Decider port, review queue, HubSpot outbox, org snapshot.

## ⭐ RESUME HERE

2026-11-18. Phase closed on a browser smoke of `http://127.0.0.1:8781` (`FIRSTREAD_FAKE=1`). CSV Arrive, score, HandOff, second HandOff refused, Dismiss, FakeWriter `relay=delivered`. Live People Search: key authenticates (`GET /api/v1/auth/health` → 200, `is_logged_in`); `POST mixed_people/api_search` → `AUTH.AUTHORIZATION.ENDPOINT_ACCESS_DENIED` (HTTP 403) — Apollo Free plan does not include that endpoint. ICP geography is prose; `geography_for_search` omits `person_locations` so we do not send a sentence as a place.

**Next (owner, not this arc's code):** a paid Apollo plan (or a key whose team may call People Search). HubSpot write still needs `HUBSPOT_WRITE=1`, a token, and `HUBSPOT_TEST_CONTACT_ID` on a **test** contact. ts-013 stays 🟦.

**This product still does not send mail or place calls.**

## Owner rulings

🧑 2026-11-17, on people search: *"AFTER, BUT IN THE SAME ARC??? SEEMS LIKE ONE OF THE MOST VALUABLE MISSING PIECES OF THE PUZZLE... I DON'T CARE IF YOU SPEND APOLLO CREDITS!!"*

🧑 2026-11-17, on the closer's CRM: *"SO THAT HUBSPOT IS THE CRM PART OF IT?? ... WOULDN'T WE WANT TO HAVE A LEGIT HUBSPOT INTEGRATION??"* Scoped to the judgement write, not a HubSpot product.

🧑 2026-11-17: *"WE'RE GOING TO START A NEW ARC FOR ALL WE'VE TALKED ABOUT THUS FAR."*

🧑 2026-11-17: the follow-through plan was executed. That is confirmation of glance v1.

## Read order

| # | Doc |
| --- | --- |
| 1 | this hub |
| 2 | [[ARCHITECTURE-AT-A-GLANCE_v1_intake-rank-handoff]] — confirmed |
| 12 | [[ARCHITECTURE]] |
| 13 | [review r1](research/archive/2026-11-17-review-r1.md) |
| 3 | [[2026-11-17-where-leads-live]] |
| 4 | [[2026-11-17-answer-store-durability]] |
| 5 | [[2026-11-17-icp-is-one-file]] |
| 6 | [[2026-11-17-apollo-is-not-intake]] |
| 20 | [[2026-11-17-apollo-people-search]] |
| 7 | [[2026-11-17-crm-and-hubspot-are-copy]] |
| 8 | [[2026-11-17-disposition-is-a-score]] |
| 9 | [[TOMBSTONES]] |
| 10 | [[2026-11-17-journal]] |
| 11 | [the board](tickets/INDEX.md) |

Oracle, outside the vault: `leadqualifier/workitem.fsx`. Gate: `./run.sh oracles`. Demo docs remain [architecture of the scorer](../../docs/engineering/ARCHITECTURE.md) and [how First Read uses Apollo](../../docs/engineering/apollo/2026-11-17-how-first-read-uses-apollo.md).
