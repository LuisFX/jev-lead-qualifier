---
title: "Relay is one HubSpot slot"
slug: relay-is-one-slot
aliases: [relay-one-slot]
date: 2026-11-17
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 6
tags: [research, relay, outbox]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v1_comms-layer.md
tickets: [cl-004]
---

# Relay is one HubSpot slot

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-18-queue-does-not-dispatch]].

## Question

Can HubSpot delivery and a sequencer send share `Relay`, or is that one slot already taken?

## Finding

One slot, HubSpot. `type Relay = NoWrite | Pending | Delivered of remoteId | Failed of reason` (`leadqualifier/workitem.fsx` lines 46–50). `HandOff` of Hot emits `[ HandedOff; RelayPending ]` (L14, line 144). `MarkDelivered` / `MarkFailed` only when `Relay` is `Pending` (lines 154–157). `drain_once` in `leadqualifier/relay.py` lists `relay_kind = 'pending'` and calls `Writer.write` (HubSpot or `FakeWriter`).

A second destination cannot be `Pending` without overwriting HubSpot's remote id. Instantly's lead id is not a HubSpot contact id. Smashing them is a second spelling of one identity.

sqlite mirrors one slot: `relay_kind`, `relay_remote_id`, `relay_reason` on `work_item` (`leadqualifier/store.py` lines 27–29).

## What is NOT known

Whether an Operator ping (Slack) will need a third slot. The glance names `Destination = HubSpot | Sequencer of Channel | Operator`. This arc persists HubSpot as `Relay` and sequencer as `Outbound`. Operator is unspeakable until a ticket earns it.
