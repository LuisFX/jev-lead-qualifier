---
title: "ts-005 Judgement carries the profile version"
slug: ts-005-judgement-carries-version
aliases: [ts-005]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 2
depends_on: [ts-004, ts-002]
tags: [ticket, profile]
---

# ts-005 Judgement carries the profile version

Hub: [[HANDOFF-MEMORY]]. Design: [[ARCHITECTURE]] §2.

## Acceptance

A rebuilt judgement is `Judged of IcpVersionId * Tier * needsReview`. `POST /api/rescore` under a draft that has not been saved does not mint a version. Fingerprints that moved under a saved version are missing; the rest rescore from the answer rows with zero Jev calls.

## Progress and what is owed

- 2026-11-17: scored result carries `icp_version_id`. Draft POST /api/rescore does not mint a version. Fingerprints still ignore weights.
