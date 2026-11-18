---
title: "Revealed contact can have no address"
slug: reveal-can-be-empty
aliases: [no-address]
date: 2026-11-17
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 7
tags: [research, contact]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v1_comms-layer.md
tickets: [cl-005]
---

# Revealed contact can have no address

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-18-playbook-is-a-string]].

## Question

After Queue or HandOff, is there an email or phone to send to?

## Finding

Often no. `contactOf` is Hidden | Revealed from disposition, not from bytes (`leadqualifier/workitem.fsx` L22–L26). `_public_lead` strips `email` and `phone` from the person dict and only puts an address on `contact` when Revealed **and** the lead has one (`leadqualifier/server.py` lines 199–206).

Control: `tests/conftest.py` builds leads with `email` and `phone`. The seed does not. `rg '"email"' data/leads` over `*.json` is 0 files (measured 2026-11-17). Apollo People Search hits also omit email (`leadqualifier/apollo.py` teaching note). CSV import *can* carry email (`leadqualifier/intake.py` `ALIASES["email"]`, `tests/test_intake.py` `"email": "ada@secret.test"`).

Revealed plus empty address is a visible unknown. A send against it is `no_address`, not a fake mailbox.

## What is NOT known

When paid Apollo enrich will fill person.email. That is the previous arc's People Search / enrich door, not this outbox.
