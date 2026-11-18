---
title: "cl-004 Outbound beside Relay"
slug: cl-004-outbound-slot
aliases: [cl-004]
date: 2026-11-17
type: ticket
arc: 2026-11-18-comms-layer
status: done
wave: 1
depends_on: []
tags: [ticket, outbox]
---

# cl-004 Outbound beside Relay

Hub: [[HANDOFF-MEMORY]]. Cost: [[2026-11-18-relay-is-one-slot]].

## Acceptance

`State` is `Open` of arrival, disposition, HubSpot `Relay`, sequencer `Outbound`. `HandOff` of Hot emits `RelayPending` **and** `OutboundPending`. `MarkDispatched` / `MarkDispatchFailed` only when Outbound is `Pending` (`outbound_not_pending` otherwise). Instantly is not stored in `relay_remote_id`.

## Progress and what is owed

- Wave 1: `Open` is a four-tuple; `MarkDispatched` only from `Outbound.Pending`. Closed 2026-11-18.
