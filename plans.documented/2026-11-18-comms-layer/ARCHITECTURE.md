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
confirmed_glance: ARCHITECTURE-AT-A-GLANCE_v3_integrations.md
oracle: leadqualifier/workitem.fsx
---

# Architecture — comms layer

Hub: [[HANDOFF-MEMORY]]. Confirmed glance: [[ARCHITECTURE-AT-A-GLANCE_v3_integrations]] (v2 superseded). Oracles: `leadqualifier/workitem.fsx`, `leadqualifier/integrations.fsx`. Board: [tickets/INDEX.md](tickets/INDEX.md). Tombstones: [[TOMBSTONES]]. Parent: [intake architecture](../2026-11-17-intake-rank-handoff/ARCHITECTURE.md).

Host Python is ported from the oracle. It is not re-derived from this prose. A vendor name is not a type.

## §0 Rules this design obeys

- F# owns the types. `leadqualifier/workitem.fsx` and `leadqualifier/integrations.fsx` are the spec. `dotnet fsi` on those files is the gate (`./run.sh oracles`).
- Illegal states are unrepresentable. `Open` has four parts: arrival, disposition, HubSpot `Relay`, sequencer `Outbound`.
- Channel is a pipe. Offer is what leaves. A vendor is a catalog file the operator mounts onto a slot. Those stay separate words.
- Disposition is authorization. A new `Pending` is born only from `Queue` (Warm/Hot) or `HandOff` (Hot).
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

Host-only, not stored on `Open`: `Bindings = Map<Channel, Comms>`, `Catalog`, `Mounts`, `compose`, `InboundMatch`. Catalog is not a fifth part of `Open`.

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

0 glance v1 · 1 oracle v1 · 2 FakeComms · 3 Elmish · 4 (retired Instantly-named ticket) · 5 Channel + Offer · 6 Bindings per channel · 7 Inbound match · 8 Catalog, mounts, Connect.

Live send of a named vendor is operational, after the machine exists, test address only. It is not a wave named after a vendor.

## §7 As built

Wave 8 (cl-012, cl-013, cl-014) is built together. Glance v3 is live; v2 is superseded. `architecture_settled` is true after Fake Connect smoke `:8786`. Remaining glance "still open" rows are operational (live Email POST, Voice/SMS catalog rows, URLs, `SendDecline`, Receive plugins).

- Work-item oracle: `Channel`, `Offer`, `Draft`. Host-only `DispatchError`, `lookup`, `fakeBindings`, `InboundHint`, `InboundMatch`, `Directory`, `matchInbound`. Floor 68, 0 failed. `Open` still four parts. `Arrival` is still `ApolloPerson | CsvRow`. `rg Instantly leadqualifier/workitem.fsx` → 0.
- Integrations oracle: `Catalog`, `Capability`, `Mounts`, `compose`, `ComposeError`. Loads 0. Floor 6, 0 failed. RED L3: Email plugin on Voice allowed → `FAIL exception: L3: expected Error CapabilityMismatch, got Ok`. Restored `when Set.contains (Send ch)`. `rg Instantly leadqualifier/integrations.fsx` → 0. `ORACLES` `EXPECTED 2`.
- Host compose: `leadqualifier/integrations.py`. sqlite `comms_mount`. `default_bindings` is `compose(catalog, load_mounts())`. `rg INSTANTLY_SEND leadqualifier/bindings.py` → 0. InstantlyEmail is the Email factory when mounted and ready. Mounted + not ready → `UnreadyComms` / `plugin_unready`. `Bindings.with_channel`. Drain catches `PluginUnready` like `ChannelUnbound`.
- Connect: five Channel Out cards on `#connect`. Email candidates `[email-plugin]`; Voice `[]`. `GET/POST /api/integrations`. `/api/status` `mounts` summary; `instantly.send` gone.
- Inbound paste and match still work (smoke `:8786`).
- Playbook has 0 URLs.
- Fake Connect smoke 2026-11-18 (`FIRSTREAD_FAKE=1` `:8786`, `FIRSTREAD_SQLITE=/tmp/firstread-wave8.sqlite`, Instantly keys unset, `FIRSTREAD_RELAY=0`; did not restart 8781–8785). Five Fake slots; Email mount `needs_credential`; Queue `csv-wave8d-0001` → `plugin_unready`; unmount then Queue `csv-wave8d-0002` → `fake-comms-1`; Voice mount 409 `capability_mismatch`; paste L001 and inbound email still work. No Instantly POST.

