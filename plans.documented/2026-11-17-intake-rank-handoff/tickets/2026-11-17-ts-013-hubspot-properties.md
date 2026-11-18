---
title: "ts-013 Write judgement properties to HubSpot"
slug: ts-013-hubspot-properties
aliases: [ts-013]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: open
wave: 5
depends_on: [ts-012]
tags: [ticket, hubspot]
---

# ts-013 Write judgement properties to HubSpot

Hub: [[HANDOFF-MEMORY]]. Design: [[ARCHITECTURE]] journey 4.

## Acceptance

The adapter maps `tier`, `route`, `fit`, `intent`, `primary_pain`, `next_action` onto HubSpot contact properties. An `Existing` match writes a note on the company, not a new contact. A test portal contact is the smoke, never a real party's record. T4 (dedupe read from HubSpot) is not this ticket.

## Progress and what is owed

- 2026-11-17: Adapter maps tier, route, fit, intent, primary_pain, next_action. Connect copy no longer claims a write that is off. 🔴 Owed: live test-portal contact with HUBSPOT_WRITE=1.
- 2026-11-18: browser HandOff of L002 → `handed_to_closer`; FakeWriter `relay=delivered`; second HandOff `already_handed_off`. Status: no HubSpot token, write flag off, no test contact id. Still owed a live test contact.
