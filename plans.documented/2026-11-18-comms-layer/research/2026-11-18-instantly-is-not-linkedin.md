---
title: "Instantly is not LinkedIn Out"
slug: instantly-is-not-linkedin
aliases: [instantly-not-linkedin]
date: 2026-11-18
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 22
tags: [research, linkedin, instantly]
---

# Instantly is not LinkedIn Out

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-18-twilio-is-not-rvm]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v4_operational]]. Ticket: [cl-019](../tickets/2026-11-18-cl-019-linkedin-stays-fake.md).

## Question

Does Instantly expose a LinkedIn send route this product can mount onto Channel `LinkedIn`?

## Measurement (2026-11-18)

- Instantly [Create lead](https://developer.instantly.ai/api-reference/lead/create-lead) `POST /api/v2/leads`: **when using `campaign`, the `email` field is required.** A list may omit email if `first_name` or `last_name` is present. That is a list row, not a LinkedIn send.
- The host Email factory (`leadqualifier/instantly.py`) posts `email` + `campaign`. It does not name Voice or LinkedIn. `rg Voice leadqualifier/instantly.py` is the Email-only fence.
- No Instantly path in that file is a LinkedIn DM, connection request, or profile send.

## Ruling this glance takes

LinkedIn Out stays Fake. Do not mount `email-plugin` on LinkedIn (capability mismatch). Do not invent a second Instantly adapter that posts email and calls it LinkedIn. Channel `LinkedIn` remains an arm so a later named API can occupy it.

## What is not known

Whether Instantly later ships a LinkedIn send route. Re-measure against Instantly's own docs; do not guess from a campaign UI.
