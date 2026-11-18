---
title: "Instantly was named as a destination"
slug: instantly-named-as-destination
aliases: [vendor-leak]
date: 2026-11-18
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 8
tags: [research, glance, host]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v2_comms-layer.md
tickets: [cl-007, cl-009]
---

# Instantly was named as a destination

Hub: [[HANDOFF-MEMORY|hub]]. Probe: [research/tools/2026-11-18-vendor-in-concept.sh](tools/2026-11-18-vendor-in-concept.sh). Sibling: [[2026-11-18-one-global-comms]].

## Question

Is Instantly a **channel**, a **host binding**, or a **destination** in the glance that wave 4 implemented?

## Finding

A destination, in the glance. A class, in the host. Not a type, in the oracle.

Measured 2026-11-18, `bash plans.documented/2026-11-18-comms-layer/research/tools/2026-11-18-vendor-in-concept.sh`:

| Where | What |
| --- | --- |
| `leadqualifier/workitem.fsx` | **0** `InstantlyComms` / `type Instantly` (control: the instrument sees a present name in `comms.py`) |
| Glance v1 L27 | "Instantly / a dialer / HubSpot are destinations" |
| Glance v1 L61 | Live email **how** = `Instantly POST /api/v2/leads` |
| [cl-007](../tickets/2026-11-17-cl-007-instantly.md) L20 | acceptance: "mounts `InstantlyComms`" |
| `leadqualifier/comms.py` L80 | `class InstantlyComms` |
| `leadqualifier/comms.py` L88–89 | that class raises `voice_unbound` — Instantly inspects Voice |

HubSpot is a system of record this product already relays. Instantly is one vendor that can send **Email**. Naming it beside HubSpot in the glance made a host file into an acceptance name. cl-007 copied that sentence. The executor built what the ticket said.

## What is NOT known

Which vendor the owner will name per channel once bindings are a map. That is a host choice. It is not a glance type.
