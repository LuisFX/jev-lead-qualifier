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
confirmed_glance: ARCHITECTURE-AT-A-GLANCE_v2_comms-layer.md
oracle: leadqualifier/workitem.fsx
---

# Architecture — comms layer

Hub: [[HANDOFF-MEMORY]]. Confirmed glance: [[ARCHITECTURE-AT-A-GLANCE_v2_comms-layer]] (v1 superseded). Oracle: `leadqualifier/workitem.fsx`. Board: [tickets/INDEX.md](tickets/INDEX.md). Tombstones: [[TOMBSTONES]]. Parent: [intake architecture](../2026-11-17-intake-rank-handoff/ARCHITECTURE.md).

Host Python is ported from the oracle. It is not re-derived from this prose. A vendor name is not a type.

## §0 Rules this design obeys

- F# owns the types. `leadqualifier/workitem.fsx` is the spec. `dotnet fsi` on that file is the gate (`./run.sh oracles`).
- Illegal states are unrepresentable. `Open` has four parts: arrival, disposition, HubSpot `Relay`, sequencer `Outbound`.
- Channel is a pipe. Offer is what leaves. A vendor is a host binding on `Map<Channel, Comms>`. Those three stay three words.
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
| Send | Nothing. Foreign | `OutboundPending` as a fact | Port `Comms.dispatch`. Host `Bindings` per channel. Fake default |
| HubSpot | Nothing. Foreign | — | Existing `Writer` |
| Inbound | Nothing. Foreign | A body of text | Host `InboundMatch` → `RecordReply` |

## §1b The diagram

See the glance. Refusals: `NotArrived`, `AlreadyArrived`, `NotJudged`, `NotHeld`, `NotHot`, `NotSequenceable`, `NotQueueable`, `AlreadyDismissed`, `NotDismissable`, `AlreadyHandedOff`, `NotHandoffable`, `RelayNotPending`, `EmptyReply`, `EmptyDraft`, `NotSendable`, `OutboundNotPending`. Host (not `decide`): `channel_unbound`, `UnknownSender`.

## §2 Contract (compile order)

`Channel` (Email \| LinkedIn \| Voice \| Sms \| RinglessVoicemail), `Offer`, `Draft`, `Outbound`, then existing `Arrival` / `Disposition` / `Relay`. `Command` is `Queue of Draft`, `HandOff of Draft`, `RecordReply of body`, `MarkDispatched`, `MarkDispatchFailed`. `State` is `Nothing | Open of Arrival * Disposition * Relay * Outbound`.

Host-only, not stored: `Bindings = Map<Channel, Comms>`, `InboundMatch`.

## §3 Oracle

`./run.sh oracles` reads `leadqualifier/ORACLES`. Floor moves in the commit that adds laws.

Wave 1 floor 48 covered v1 Channel / RecordReply of body / Outbound beside Relay. Wave 5 raised the floor for Sms, RinglessVoicemail, and Offer. Wave 6 raised it for `lookup` / `fakeBindings`. Wave 7 raised it for `matchInbound`. The floor is the law count, not this list's length in prose.

## §4 Host

- sqlite: `outbound_*` columns on `work_item`, one shape.
- Concept: `Comms` protocol only. Drain asks `Bindings[draft.channel]`.
- An Email adapter does not mention Voice. Fake is the default for an unbound channel.
- `POST /api/leads/{id}/reply` is paste: the URL names the work item (404 if unknown to the board). `POST /api/inbound` is match: `InboundHint` then `RecordReply` (409 `unknown_sender` if 0 or 2+ hits).
- Placement of vendor files still needs approval (AGENTS.md PART IV.7). ⛔ No vendor name in `decide`.

## §5 Elmish

Location is the URL. `#lead/{id}` shows channel, offer, outbox. Reply is a `Cmd`. Stale HTTP drops on `seq`. Queue / Hand off stay the authorize buttons.

## §6 Waves

0 glance v1 · 1 oracle v1 · 2 FakeComms · 3 Elmish · 4 (retired Instantly-named ticket) · 5 Channel + Offer · 6 Bindings per channel · 7 Inbound match.

Live send of a named vendor is operational, behind env, test address only. It is not a wave named after a vendor.

## §7 As built

Wave 7 (cl-011) is built. Glance types are in the oracle and the host. `architecture_settled` is true. Remaining glance "still open" rows are operational (named vendor, URLs, `SendDecline`).

- Oracle: `Channel`, `Offer`, `Draft`. Host-only `DispatchError`, `lookup`, `fakeBindings`, `InboundHint`, `InboundMatch`, `Directory`, `matchInbound`. Floor 68, 0 failed (`dotnet fsi leadqualifier/workitem.fsx`). `Open` still four parts (L61, L68). `Arrival` is still `ApolloPerson | CsvRow`. `rg InstantlyComms leadqualifier/workitem.fsx` → 0.
- Empty offer is exhaustive (`emptyOffer`). Nonempty `DeclineDraft` refuses `NotSendable`. `SendDecline` is not a command. `decide` has no `ChannelUnbound` or `UnknownSender` refusal; those are host 409s / `MarkDispatchFailed`.
- Host port: `leadqualifier/workitem.py` kind literals. Wire `{ channel, offer: { kind, … } }`. sqlite `outbound_offer_kind` + `outbound_offer_json`; leftover `outbound_body` / `outbound_slots_json` unused. Event log rewrite is idempotent.
- Address law (`comms.py` `address_for`): Email → `person.email`; LinkedIn → `person.linkedin` then `company.linkedin`, never email; Voice / Sms / RinglessVoicemail → `person.phone`.
- Playbook fill: `send_case_study_*` → Copy; `ask_qualifying_question_*` → QualifyingQuestion; Queue of `book_call` → Email + Copy of the CET sentence; HandOff of `book_call` → Voice + Calendar of `Tuesday 11:00 CET`, `Thursday 15:00 CET`. No URLs invented. Sms / RVM / CaseStudy / Form / DeclineDraft are unrepresentable from `pick_action`.
- Bindings: production `default_bindings` is total Fake (`leadqualifier/bindings.py` L18). A live Email vendor, if env is on, replaces only the Email key. Drain looks up `draft.channel`. An incomplete map is `channel_unbound`. `InstantlyEmail` lives in `leadqualifier/instantly.py`; `rg Voice` on that file is 0.
- Inbound: `match_inbound` (`leadqualifier/inbound.py` L99) scans `payload_json`. Identity is `ByWorkItem | ByEmail | ByPhone`. 0 or 2+ hits → `UnknownSender`. Email uniqueness is not a write invariant. `POST /api/inbound` 409 `unknown_sender`; paste unknown id is 404. `rg Instantly leadqualifier/inbound.py` → 0.
- Lead view: Channel + Offer + paste box. Fake inbound smoke 2026-11-18 (`FIRSTREAD_FAKE=1` `:8785`): paste L001 still works; unknown email 409; CSV `csv-wave7-0001` email match folds the body. No Instantly POST.
- Playbook has 0 URLs.
- HTTP: `/api/leads/…` plus `/api/inbound`.
