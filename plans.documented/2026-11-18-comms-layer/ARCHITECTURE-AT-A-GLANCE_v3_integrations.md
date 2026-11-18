---
title: "At a glance v3 — an operator mounts a provider onto a slot"
slug: architecture-at-a-glance-v3-integrations
aliases: [glance-v3-comms]
date: 2026-11-18
type: research
arc: 2026-11-18-comms-layer
status: superseded
read_order: 21
supersedes: ARCHITECTURE-AT-A-GLANCE_v2_comms-layer.md
superseded_by: ARCHITECTURE-AT-A-GLANCE_v4_operational.md
confirmed: 2026-11-18
tags: [architecture, glance, comms, integrations]
---

# At a glance v3 — an operator mounts a provider onto a slot

**Superseded 2026-11-18 by [[ARCHITECTURE-AT-A-GLANCE_v4_operational]].** Keep as evidence of what wave 8 built against. The hole: SendDecline, Receive, Twilio catalog files, and live Email on a test address were still open.

Hub: [[HANDOFF-MEMORY|hub]]. Supersedes [[ARCHITECTURE-AT-A-GLANCE_v2_comms-layer]]. Parent glance (intake): [intake v1](../2026-11-17-intake-rank-handoff/ARCHITECTURE-AT-A-GLANCE_v1_intake-rank-handoff.md).

**Confirmed 2026-11-18 (then superseded).** Owner ruling: live senders are any, some, or all channels; configuration is admin-driven plugins; code-complete before live smoke; HubSpot stays Relay/env, not this board. The match that is law is `leadqualifier/workitem.fsx` (Open, Channel, Offer) and `leadqualifier/integrations.fsx` (Catalog, Mounts, compose). Census: the research notes under Evidence.

## The story

A person scores a lead. Queue on a warm or hot judgement means "this draft may leave the building." Hand off on a hot judgement means "offer the founder slots, and write HubSpot." **Another app still sends.** This product does not own the mailbox, the number, or the dialer.

The pipe is a **channel**. The sentence or link that leaves is an **offer**. The company that actually delivers is a **plugin** the operator mounts onto a slot. Unmounted is Fake. A plugin that only sends Email cannot occupy Voice. Two plugins on Email Out is unspeakable.

`decide` still does not send. A vendor is a catalog file, not an acceptance name.

## The shape

This product owns the work item and its outboxes. HubSpot is the CRM this product already relays — not a Comms plugin, not a Connect card. Email, SMS, voice, LinkedIn, ringless voicemail are Channel Out slots. Direction is Out. One slot per Channel.

```fsharp
type Channel =
    | Email
    | LinkedIn
    | Voice
    | Sms
    | RinglessVoicemail

type Offer =
    | Copy of text: string
    | CaseStudy of url: string
    | QualifyingQuestion of text: string
    | Calendar of slots: string list
    | Form of url: string
    | DeclineDraft of text: string

type Draft = { Channel: Channel; Offer: Offer }

type Outbound =
    | NoSend
    | Pending of Draft
    | Dispatched of remoteId: string
    | Failed of reason: string

type Comms = {
    dispatch: WorkItemId * Channel * Draft -> Result<RemoteId, DispatchError>
}

// HOST only. The concept never stores this map.
type Bindings = Map<Channel, Comms>

type Direction = Out

type Capability = Send of Channel

type PluginId = PluginId of string   // opaque label; never a vendor word in the oracle

type Catalog = Map<PluginId, Set<Capability>>

type Mount =
    | Unmounted
    | Mounted of PluginId

type Mounts = Map<Channel, Mount>

type ComposeError =
    | UnknownPlugin
    | CapabilityMismatch

type InboundHint =
    | ByWorkItem of WorkItemId
    | ByEmail of string
    | ByPhone of string

type InboundMatch =
    | Matched of WorkItemId
    | UnknownSender
```

`compose catalog mounts` is total on Channel: Unmounted → Fake; Mounted → that plugin's adapter **only if** `Send ch` is in its set. A missing Bindings key remains `channel_unbound` (mis-compose). Unmounted is **not** `channel_unbound`. Mounted and the process lacks the credential is `plugin_unready` on dispatch — Fake is not silently kept while sqlite says Mounted.

`Relay` stays HubSpot. Secrets stay in the process environment. The UI stores mounts (a plugin id on a slot). Status may say `ready` / `needs_credential`. Never the value. Env is resolved at process start — after adding a key, restart.

Inbound paste stays. Receive plugins are a later catalog row, not this glance.

Disposition is authorization. Unreviewed and Dismissed never grow a new `Pending`. HeldForHuman is revealed and still `NoSend` until Queue or HandOff. Nurture Queue is a decision with `NoSend`. Disqualify stays `not_sequenceable`. `DeclineDraft` is glanced, not sent, until a later `SendDecline` ticket.

A reply is `RecordReply` of a non-empty body. The host turns a vendor event into `InboundMatch`, then `RecordReply`. `Arrival` has no `Reply` case. `UnknownSender` is loud; it is not a new work item.

## What it replaces, and how

| Flow | Target | Replaces | How |
| --- | --- | --- | --- |
| Queue a warm lead | `Queued` then `OutboundPending` of an Email draft | Queue as disposition-only ([[2026-11-18-queue-does-not-dispatch]]) | Drain `Bindings[Email]`, then `MarkDispatched` |
| Hand off a hot lead | HubSpot `RelayPending` **and** `OutboundPending` of Voice | HandOff as HubSpot-only ([[2026-11-18-relay-is-one-slot]]) | Two destinations, two drains. Voice adapter is not the Email adapter |
| Record a reply | `ReplyArrived` of body, Unreviewed, rescore | operator paste only ([[2026-11-18-inbound-is-paste]]) | Host `InboundMatch` then `RecordReply`. Empty text refuses |
| Show the draft | Channel + Offer + outbox on `#lead/{id}` | playbook sentence ([[2026-11-18-offer-is-untyped]]) | Queue / Hand off stay the authorize buttons |
| Occupy a slot | operator Mount / Unmount on `#connect` | brochure Connect ([[2026-11-18-connect-is-brochure]]); `INSTANTLY_SEND` Email swap ([[2026-11-18-instantly-send-is-the-email-switch]]) | sqlite `comms_mount`; compose; Fake fills Unmounted |
| Live credential | env key present → `ready`; absent → `needs_credential` / `plugin_unready` | keys imagined in sqlite ([[2026-11-18-secrets-are-not-mounts]]) | Never the value on the wire. Restart after adding a key |
| Live send | owner's named vendor file, after the machine exists, test address only | glance v1 "Live email = Instantly POST" ([[2026-11-18-instantly-named-as-destination]]) | Operational. Not a type. Not an acceptance name |

## The Decider

Drawn from the target match. Refusals are notes because a refusal is not a new case.

```mermaid
stateDiagram-v2
  [*] --> Nothing
  Nothing --> Unreviewed: Arrived
  Unreviewed --> HeldForHuman: Flagged
  Unreviewed --> Dismissed: PersonDismissed
  Unreviewed --> QueuedForSequence: Queued
  Unreviewed --> HandedToCloser: HandedOff
  HeldForHuman --> Dismissed: PersonDismissed
  HeldForHuman --> QueuedForSequence: Queued
  HeldForHuman --> HandedToCloser: HandedOff
  Dismissed --> Unreviewed: ReplyArrived
  QueuedForSequence --> Unreviewed: ReplyArrived
  HandedToCloser --> Unreviewed: ReplyArrived
  HeldForHuman --> Unreviewed: ReplyArrived
  Unreviewed --> Unreviewed: ReplyArrived
```

Outbound (one slot beside HubSpot `Relay`):

```mermaid
stateDiagram-v2
  [*] --> NoSend
  NoSend --> Pending: OutboundPending
  Pending --> Dispatched: OutboundDispatched
  Pending --> Failed: OutboundFailed
```

Compose (host):

```mermaid
flowchart LR
  admin["Connect Mount Unmount"] --> mounts["Mounts sqlite"]
  catalog["Catalog PluginId to Capabilities"] --> compose["compose"]
  mounts --> compose
  compose --> bindings["Bindings Channel to Comms"]
  fake["Fake on Unmounted"] --> bindings
  plugin["Mounted plugin if Send channel"] --> bindings
  pending["OutboundPending"] --> drain["drain_outbound"]
  bindings --> drain
```

`Queue` of Warm or Hot emits `Queued` then `OutboundPending`. `Queue` of Nurture emits `Queued` only. `HandOff` of Hot emits `HandedOff`, `RelayPending`, `OutboundPending`. Empty offer / empty reply refuse. Nonempty `DeclineDraft` refuses `NotSendable` (`SendDecline` is not a command here). `MarkDispatched` only from `Pending`. Unbound channel refuses at the host, not in `decide`. Capability mismatch refuses at Mount, not in `decide`.

## Evidence

| Claim the target stands on | Where it was measured |
| --- | --- |
| Queue of Warm → `QueuedForSequence`, no send in `decide` | [[2026-11-18-queue-does-not-dispatch]] |
| `RecordReply` now carries a body; the door is still paste | [[2026-11-18-record-reply-has-no-body]], [[2026-11-18-inbound-is-paste]] |
| Playbook is a filled string; 0 URLs | [[2026-11-18-playbook-is-a-string]], [[2026-11-18-offer-is-untyped]] |
| `Relay` is one HubSpot slot | [[2026-11-18-relay-is-one-slot]] |
| Demo leads have no email field | [[2026-11-18-reveal-can-be-empty]] |
| Glance v1 named Instantly as a destination; oracle has 0 InstantlyComms | [[2026-11-18-instantly-named-as-destination]] |
| `default_comms` was Instantly or Fake, one value | [[2026-11-18-one-global-comms]] |
| Connect is brochure copy; `INSTANTLY_SEND` is the Email switch | [[2026-11-18-connect-is-brochure]], [[2026-11-18-instantly-send-is-the-email-switch]] |
| Secrets are env, not sqlite mounts | [[2026-11-18-secrets-are-not-mounts]] |

## What this deliberately does not do

- It does not replace `scoring.py`.
- It does not auto-send from `assemble`.
- It does not mint `SendDecline` in this version.
- It does not put a vendor name on the aggregate, the oracle, or a ticket's acceptance.
- It does not smash any sequencer into `Relay`.
- It does not put HubSpot on the Connect board.
- It does not store keys in sqlite or return them from JSON.
- It does not add Receive plugins or parse a vendor webhook in `decide`.
- It does not add a `Reply` arm on `Arrival`.
- It does not add a scraper ABC or a NotificationService.
- It does not rewrite the page in Next.js.

## Still open

- Live POST of a named Email vendor on a test address — owner's word after this machine exists. Not this glance's smoke.
- Voice / SMS / LinkedIn / ringless-voicemail catalog rows. Those slots have empty candidates until a plugin file exists.
- Whether `Form` and `CaseStudy` URLs exist as real assets, or `Copy` is the only reachable offer until then. Do not invent URLs.
- `SendDecline` as a later command.
- Receive plugins as a later catalog row.
