---
title: "Inbound is an operator paste"
slug: inbound-is-paste
aliases: [inbound-match]
date: 2026-11-18
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 14
tags: [research, inbound]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v2_comms-layer.md
tickets: [cl-011]
---

# Inbound is an operator paste

Hub: [[HANDOFF-MEMORY|hub]]. Earlier cost: [[2026-11-18-record-reply-has-no-body]] (the unit command). The body is now on the event. The **door** is still a human.

## Question

How does a reply that arrived in another app become `RecordReply` on **this** work item?

## Finding

It does not, unless an operator pastes. `POST /api/leads/{id}/reply` (`leadqualifier/server.py` L588–591) is the inbound port. The docstring says vendor webhooks land here later. There is no matcher: no Instantly lead id, no email, no phone → `WorkItemId`. `Arrival` still has no `Reply` case (`workitem.fsx`). That part is still right.

A webhook without a match is an unknown sender, not a new work item and not a silent drop. That union is unwritten.

## What is NOT known

Which vendor event the first host will parse. The concept sees `RecordReply of body`. The host parses. Do not put a vendor name on the command.
