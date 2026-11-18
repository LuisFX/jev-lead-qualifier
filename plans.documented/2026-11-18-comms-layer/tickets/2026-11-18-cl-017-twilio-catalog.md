---
title: "cl-017 Twilio SMS and Voice catalog"
slug: cl-017-twilio-catalog
aliases: [cl-017]
date: 2026-11-18
type: ticket
arc: 2026-11-18-comms-layer
status: done
wave: 11
depends_on: [cl-012]
tags: [ticket, sms, voice]
---

# cl-017 Twilio SMS and Voice catalog

Hub: [[HANDOFF-MEMORY]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v4_operational]]. Cost: [[2026-11-18-twilio-is-not-rvm]]. Board: [INDEX](INDEX.md).

## Acceptance

Host files only. Email Instantly stays Email-only (`rg Voice` on `leadqualifier/instantly.py` still 0). `sms-plugin` → `{Send Sms}` via `POST https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json` (httpx + Basic). Body `offer_text`, to `person.phone`. `voice-plugin` → `{Send Voice}` via `POST …/Calls.json` with `Twiml` `<Say>` of `offer_text`. Ready = SID + token + from-number (env). Mounted + not ready → `plugin_unready`. Connect cards gain candidates. Oracle: Voice candidates nonempty for a `voice-plugin` label; Email plugin still cannot occupy Voice. Playbook still has no `sms` row. HandOff still Voice+Calendar. Queue of `book_call` still Email+Copy. Tests: compose, 409 if Email plugin on Sms, drain unready, **no live Twilio POST**. Live Twilio is the owner's word after this wave. Vendor words stay out of both `.fsx` files.

## Progress and what is owed

- Wave 11: `sms-plugin` / `voice-plugin`. Connect candidates nonempty. Email plugin on Sms 409. Twilio env absent; mocked POST only. Closed 2026-11-18.
