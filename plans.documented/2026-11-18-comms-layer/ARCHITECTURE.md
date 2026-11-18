---
title: "Architecture — comms layer"
slug: architecture-comms-layer
aliases: [architecture-comms]
date: 2026-11-17
type: research
arc: 2026-11-18-comms-layer
status: live
read_order: 12
tags: [architecture]
confirmed_glance: ARCHITECTURE-AT-A-GLANCE_v4_operational.md
oracle: leadqualifier/workitem.fsx
---

# Architecture — comms layer

Hub: [[HANDOFF-MEMORY]]. Confirmed glance: [[ARCHITECTURE-AT-A-GLANCE_v4_operational]] (v3 superseded). Oracles: `leadqualifier/workitem.fsx`, `leadqualifier/integrations.fsx`. Board: [tickets/INDEX.md](tickets/INDEX.md). Tombstones: [[TOMBSTONES]]. Parent: [intake architecture](../2026-11-17-intake-rank-handoff/ARCHITECTURE.md).

Host Python is ported from the oracle. It is not re-derived from this prose. A vendor name is not a type.

## §0 Rules this design obeys

- F# owns the types. `leadqualifier/workitem.fsx` and `leadqualifier/integrations.fsx` are the spec. `dotnet fsi` on those files is the gate (`./run.sh oracles`).
- Illegal states are unrepresentable. `Open` has four parts: arrival, disposition, HubSpot `Relay`, sequencer `Outbound`.
- Channel is a pipe. Offer is what leaves. A vendor is a catalog file the operator mounts onto a slot. Those stay separate words.
- Disposition is authorization. A new `Pending` is born from `Queue` (Warm/Hot), `HandOff` (Hot), or `SendDecline` (Disqualify + nonempty DeclineDraft).
- `contactOf` is unchanged (Hidden on Unreviewed and Dismissed).
- `scoring.py` `assemble` stays the rank. It does not send.
- One operator. No tenant id.
- A reply reopens the same item. `Arrival` has no `Reply` case. Inbound match is a host concern.

## §1 Bounded contexts

| Context | Owns | Reads | Writes through |
| --- | --- | --- | --- |
| Work item | Birth, disposition, HubSpot relay, outbound | Judgement from the rank | `decide` / `evolve` |
| Rank | Nothing new | Answer rows, live profile | Zero. It is a fold |
| Send | Nothing. Foreign | `OutboundPending` as a fact | Port `Comms.dispatch`. Host `compose(catalog, mounts)`. Fake on Unmounted |
| HubSpot | Nothing. Foreign | — | Existing `Writer` |
| Inbound | Nothing. Foreign | A body of text | Host `InboundMatch` → `RecordReply` |

## §1b The diagram

See the glance. Refusals: `NotArrived`, `AlreadyArrived`, `NotJudged`, `NotHeld`, `NotHot`, `NotSequenceable`, `NotQueueable`, `AlreadyDismissed`, `NotDismissable`, `AlreadyHandedOff`, `NotHandoffable`, `RelayNotPending`, `EmptyReply`, `EmptyDraft`, `NotSendable`, `OutboundNotPending`. Host (not `decide`): `channel_unbound`, `plugin_unready`, `UnknownSender`, `capability_mismatch`, `unknown_plugin`.

## §2 Contract (compile order)

`Channel` (Email \| LinkedIn \| Voice \| Sms \| RinglessVoicemail), `Offer`, `Draft`, `Outbound`, then existing `Arrival` / `Disposition` / `Relay`. `Command` is `Queue of Draft`, `HandOff of Draft`, `RecordReply of body`, `MarkDispatched`, `MarkDispatchFailed`. `State` is `Nothing | Open of Arrival * Disposition * Relay * Outbound`.

`Command` also has `SendDecline of Draft`. Host-only, not stored on `Open`: `Bindings = Map<Channel, Comms>`, `Catalog`, `Mounts`, `ReceiveMounts`, `compose`, `InboundMatch`. Catalog is not a fifth part of `Open`. Receive is not an Out slot.

## §3 Oracle

`./run.sh oracles` reads `leadqualifier/ORACLES` (`EXPECTED 2`). Floor moves in the commit that adds laws.

Wave 1 floor 48 covered v1 Channel / RecordReply of body / Outbound beside Relay. Wave 5 raised the floor for Sms, RinglessVoicemail, and Offer. Wave 6 raised it for `lookup` / `fakeBindings`. Wave 7 raised it for `matchInbound`. Wave 8 added `leadqualifier/integrations.fsx` (loads 0). The floor is the law count, not this list's length in prose.

## §4 Host

- sqlite: `outbound_*` columns on `work_item`, one shape. `comms_mount` (channel PK, plugin_id NOT NULL). Absence is Unmounted. Do not store `"fake"`. Secrets are not in sqlite.
- Concept: `Comms` protocol only. Drain asks `Bindings[draft.channel]`. `compose` is total on Channel. Unmounted is Fake. Mounted + not ready is `plugin_unready`.
- An Email adapter does not mention Voice. InstantlyEmail is a catalog factory for `email-plugin`, not an acceptance name.
- `POST /api/leads/{id}/reply` is paste: the URL names the work item (404 if unknown to the board). `POST /api/inbound` is match: `InboundHint` then `RecordReply` (409 `unknown_sender` if 0 or 2+ hits).
- `GET/POST /api/integrations` occupy slots. 409 `capability_mismatch` | `unknown_plugin`. Never keys.
- Placement of vendor files still needs approval (AGENTS.md PART IV.7). ⛔ No vendor name in `decide`.

## §5 Elmish

Location is the URL. `#lead/{id}` shows channel, offer, outbox. `#connect` is five Channel Out cards. Reply / Mount / Unmount are `Cmd`s. Stale HTTP drops on `seq`. Queue / Hand off stay the authorize buttons. HubSpot write is Relay, env, not this board.

## §6 Waves

0 glance v1 · 1 oracle v1 · 2 FakeComms · 3 Elmish · 4 (retired Instantly-named ticket) · 5 Channel + Offer · 6 Bindings per channel · 7 Inbound match · 8 Catalog, mounts, Connect · 9 live Email skip · 10 SendDecline · 11 Twilio catalog · 12 Receive Email.

Live Twilio POST and a reachable Instantly webhook are the owner's later word. LinkedIn / RVM / invented URLs are STOPs (cl-019, cl-020).

## §7 As built

Waves 9–12 (cl-015–020) close glance v3's operational opens. Glance v4 is live; v3 is superseded. LinkedIn Instantly absent; Twilio RVM forbidden; playbook 0 URLs.

- Work-item oracle: `SendDecline of Draft`. RED: Command without decide → `FS0025` + `FAIL exception: The match cases were incomplete` (`68 passed, 1 failed`). Decide added → `75 passed, 0 failed`. Floor 75. `rg Instantly leadqualifier/workitem.fsx` → 0.
- Integrations oracle: `Capability = Send of Channel | Receive of Channel`. Catalog: `email-plugin` Send+Receive Email, `sms-plugin` Send Sms, `voice-plugin` Send Voice. Floor 10, 0 failed. `rg Instantly leadqualifier/integrations.fsx` → 0. `ORACLES` `EXPECTED 2`.
- Host: `twilio_sms.py` / `twilio_voice.py` httpx named URLs. `instantly_inbound.py` beside Instantly. sqlite `comms_receive`. `rg Voice leadqualifier/instantly.py` → 0. `rg Instantly leadqualifier/inbound.py` → 0. `rg INSTANTLY_SEND tests/test_comms.py` → 0.
- Live Email skip: key present (len 92), test email present (len 19), campaign absent (len 0). No Instantly POST. Live Twilio: SID/token/from all absent. No Twilio POST.
- Fake smoke 2026-11-18 (`FIRSTREAD_FAKE=1` `:8787`, `FIRSTREAD_SQLITE=/tmp/firstread-wave9.sqlite`, `FIRSTREAD_RELAY=0`). Email mount `needs_credential`. Email on Sms 409. Voice/Sms candidates nonempty; LinkedIn/RVM `[]`. Queue hot `csv-wave9-hot-0001` → `fake-comms-2`. SendDecline disqualify → `dismissed` + `fake-comms-1` + contact Hidden. Receive unmounted 404; mount; `email_opened` 204; `reply_received` folds. Voice-plugin on RVM 409. Port killed.
- Playbook has 0 URLs. `offer_for_action` stays Copy.

