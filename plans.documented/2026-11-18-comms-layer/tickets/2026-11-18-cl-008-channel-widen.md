---
title: "cl-008 Channel includes Sms and RinglessVoicemail"
slug: cl-008-channel-widen
aliases: [cl-008]
date: 2026-11-18
type: ticket
arc: 2026-11-18-comms-layer
status: done
wave: 5
depends_on: []
tags: [ticket, channel]
---

# cl-008 Channel includes Sms and RinglessVoicemail

Hub: [[HANDOFF-MEMORY]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v2_comms-layer]]. Cost: [[2026-11-18-one-global-comms]].

## Acceptance

Oracle `Channel = Email | LinkedIn | Voice | Sms | RinglessVoicemail`. A host may bind each. `decide` still does not send. Address law: Email → email; Sms / Voice / RinglessVoicemail → phone; LinkedIn is not email-by-default (a typed address or `no_address`). Floor moves in the same commit. No vendor name in the oracle.

## Progress and what is owed

- Wave 5: oracle L48 LinkedIn Copy; L49 Sms Queue Warm; L50 RinglessVoicemail Queue Warm. Floor 56 (`leadqualifier/ORACLES`). Host `decode_channel` five arms. `address_for` (`leadqualifier/comms.py`): Email → email; LinkedIn → linkedin fields never email; Voice/Sms/RVM → phone. Tests `tests/test_comms.py` `test_address_for_is_exhaustive`. Closed 2026-11-18.
