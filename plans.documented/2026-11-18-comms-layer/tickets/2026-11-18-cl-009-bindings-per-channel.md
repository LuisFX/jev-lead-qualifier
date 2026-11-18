---
title: "cl-009 Bindings per channel, not Instantly-or-Fake"
slug: cl-009-bindings-per-channel
aliases: [cl-009]
date: 2026-11-18
type: ticket
arc: 2026-11-18-comms-layer
status: done
wave: 6
depends_on: [cl-008]
tags: [ticket, host, ports]
---

# cl-009 Bindings per channel, not Instantly-or-Fake

Hub: [[HANDOFF-MEMORY]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v2_comms-layer]]. Cost: [[2026-11-18-one-global-comms]], [[2026-11-18-instantly-named-as-destination]]. Tombstone: [[TOMBSTONES]].

## Acceptance

The concept sees `Comms.dispatch`. The host holds `Map<Channel, Comms>`. Fake is the default for every unbound channel. A missing key is `channel_unbound`, not a vendor exception. An Email adapter does not mention Voice. A vendor class may exist as a **host file**; it is not an acceptance name and not imported by `decide`. Drain asks the map by `draft.channel`.

## Progress and what is owed

- Wave 6: oracle `lookup` / `fakeBindings` L57–L61 (`leadqualifier/workitem.fsx` L89–L101, L606–L625). Floor 61 (`leadqualifier/ORACLES`). RED L59 miss-as-Ok failed then restored. Bindings not a field of `Open` (L61).
- Host `Bindings.lookup` (`leadqualifier/comms.py` L124–L141). Drain `leadqualifier/comms.py` L163. `default_comms` deleted. `default_bindings` total Fake (`leadqualifier/bindings.py` L18); Email swap behind env. `InstantlyEmail` in `leadqualifier/instantly.py` L24. `rg Voice leadqualifier/instantly.py` → 0.
- Callers: `leadqualifier/server.py` L573, `leadqualifier/relay.py` L83.
- Tests: `tests/test_bindings.py` Fake Email/Voice/Sms; incomplete map → `channel_unbound`; `with_email` leaves Voice Fake; Voice fence with `comms.py` control. Live Instantly skipped (`test_instantly_live_posts_test_address`).
- Fake smoke `:8784` 2026-11-18: warm Queue email `fake-comms-1`; hot HandOff voice `fake-comms-2`. No Instantly POST.
- Closed 2026-11-18.
