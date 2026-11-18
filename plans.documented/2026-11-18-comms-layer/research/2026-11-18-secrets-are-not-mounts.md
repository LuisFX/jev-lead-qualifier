---
title: "Secrets are not mounts"
slug: secrets-are-not-mounts
aliases: [secrets-vs-mounts]
date: 2026-11-18
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 20
tags: [research, secrets]
---

# Secrets are not mounts

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-18-instantly-send-is-the-email-switch]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v3_integrations]].

## Question

Where does a vendor credential live — sqlite, the JSON API, or the process environment?

## Measurement (2026-11-18)

- `leadqualifier/config.py` L74–L81: `INSTANTLY_API_KEY` and `INSTANTLY_CAMPAIGN_ID` are `os.environ.get`. The module never prints them.
- `leadqualifier/store.py` SCHEMA: `work_item`, events, answers, icp, app_state, account_snapshot. No column for a vendor key.
- `/api/status` (`leadqualifier/server.py` L207): `instantly.has_key` is a boolean. The value is not in the JSON.
- AGENTS.md PART X: a secret is read from the process environment. Never write the value into a file.

## Ruling this glance takes

A mount is a plugin id on a Channel slot. Ready is "the process has the credential." After adding a key, restart. Do not put keys in sqlite. Do not return them from `/api/integrations`.

## Ticket this earns

[cl-012](../tickets/2026-11-18-cl-012-catalog-compose.md) (ready / `plugin_unready`), [cl-013](../tickets/2026-11-18-cl-013-connect-board.md) (card copy: restart after adding a key)
