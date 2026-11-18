---
title: "Playbook is an untyped string"
slug: playbook-is-a-string
aliases: [playbook-string]
date: 2026-11-17
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 5
tags: [research, playbook, channel]
feeds:
  - ARCHITECTURE-AT-A-GLANCE_v1_comms-layer.md
  - ARCHITECTURE-AT-A-GLANCE_v2_comms-layer.md
tickets: [cl-003, cl-010]
---

# Playbook is an untyped string

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-18-queue-does-not-dispatch]].

## Question

Does the next action know its channel (email, LinkedIn, voice), or is it a sentence?

## Finding

A sentence. `data/playbook.json` is keyed by action id (`book_call`, `send_case_study_agency`, `decline_politely`, …). Each entry has `label`, `tiers`, `description`, `text` with `{first_name}` slots. `pick_action` in `leadqualifier/scoring.py` lines 261–278 fills `text` and returns `{id, label, text, source, …}`. There is no `channel` field.

Channel is implied by id, not typed:

| id | implied channel | this arc |
| --- | --- | --- |
| `book_call` | Voice (slots in the sentence, not a list) | HandOff draft |
| `send_case_study_*`, `ask_qualifying_question_*` | Email | Queue draft |
| `add_to_nurture` | none | Queue of Nurture, `NoSend` |
| `decline_politely` | draft only | not a send |
| `route_to_account_owner` | HubSpot note path | existing, not sequencer |

The lead page renders `a.text` (`web/app.js` `renderAction`). Queue / Hand off do not receive that string.

## What is NOT known

Whether LinkedIn as a Channel will have a vendor in this product. The union includes `LinkedIn`. No host binds it in this arc.

2026-11-18: the sentence has no URL either — [[2026-11-18-offer-is-untyped]], cl-010.
