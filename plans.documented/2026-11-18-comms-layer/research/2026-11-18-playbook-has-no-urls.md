---
title: "Playbook has no URLs"
slug: playbook-has-no-urls
aliases: [no-playbook-urls]
date: 2026-11-18
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 24
tags: [research, offer, urls]
---

# Playbook has no URLs

Hub: [[HANDOFF-MEMORY|hub]]. Sibling: [[2026-11-18-offer-is-untyped]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v4_operational]].

## Question

Are there named CaseStudy or Form URLs this product may put on an Offer, or does `pick_action` stay Copy?

## Measurement (2026-11-18)

- `data/playbook.json`: every action is `label`, `tiers`, `description`, `text`. Zero `url` keys. `rg 'https?://' data/playbook.json` is empty.
- `offer_for_action` (`leadqualifier/workitem.py`) maps playbook ids to `Copy` or `QualifyingQuestion`. It does not mint a URL.
- The owner typed none when asked.

## Ruling this glance takes

`CaseStudy` and `Form` stay unrepresentable from `pick_action`. ⛔ Do not invent a URL to make those arms reachable. A later ticket wires them when the owner types named URLs.

## What is not known

The real assets, if they exist, and who publishes them. Absence here is not a blank the catalog may fill.
