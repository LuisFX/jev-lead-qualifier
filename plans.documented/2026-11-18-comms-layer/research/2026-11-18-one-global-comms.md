---
title: "One global Comms, Instantly or Fake"
slug: one-global-comms
aliases: [comms-map]
date: 2026-11-18
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 9
tags: [research, host, ports]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v2_comms-layer.md
tickets: [cl-009]
---

# One global Comms, Instantly or Fake

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-18-instantly-named-as-destination]].

## Question

Can the host bind Email to one vendor and Voice to another without editing Instantly's class?

## Finding

No. `default_comms` is a boolean (`leadqualifier/comms.py` L133–136): Instantly send enabled → InstantlyComms, else FakeComms. One value serves every channel.

`InstantlyComms.dispatch` L88–89 raises `voice_unbound` if the channel is Voice. The email adapter knows Voice exists. A Twilio SMS adapter cannot be mounted beside Instantly without changing that function.

`address_for` (`comms.py` L44–50): Voice → `person.phone`, else `person.email`. Sms and RinglessVoicemail are not channels, so they cannot have a typed address. LinkedIn uses email today, which is a guess, not a law.

The port itself is domain-shaped: `Comms.dispatch(work_item_id, channel, draft, payload) -> remote id`. The leak is the **composition**, not the Protocol.

## What is NOT known

The host package layout for binding files (one module per vendor vs one module per channel). Placement still needs approval (AGENTS.md PART IV.7). The type is `Map<Channel, Comms>` either way.
