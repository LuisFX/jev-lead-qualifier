(**
  Work item — the aggregate this product owns.

  A person arrives (Apollo person, or a CSV row). Jev answers live on a
  fingerprint ledger. `assemble` in scoring.py folds those answers under one
  ICP version into a Judgement. That fold is NOT stored on this aggregate.
  Disposition is. Relay is the HubSpot outbox for a Hot handoff. Outbound is
  the sequencer / dialer / SMS / RVM slot. A vendor name is not stored in Relay.

  Queue of Warm/Hot authorizes a send: Queued then OutboundPending of Draft.
  Queue of Nurture is a decision with NoSend (no personal outreach).
  HandOff of Hot emits RelayPending AND OutboundPending (Voice + Calendar).
  RecordReply of a non-empty body reopens Unreviewed. Empty body refuses.
  Empty Offer refuses EmptyDraft. Queue / HandOff of nonempty DeclineDraft
  refuse NotSendable. SendDecline of Disqualify emits PersonDismissed then
  OutboundPending of that draft. Empty DeclineDraft is EmptyDraft. Any other
  Offer is NotSendable. Not Disqualify is NotSequenceable. Contact stays
  Hidden on Dismissed; drain reads payload_json.

  TEACHING NOTE: Sms and RinglessVoicemail are legal Queue channels. Nothing in
  this file's helpers is a playbook row — production pick_action does not emit
  them yet. 🔴 UNENFORCED in the host until a later ticket names a playbook row.
  CaseStudy / Form exist so a URL can be named; a blank URL is EmptyDraft.
  ⛔ Do not invent a URL to make those arms reachable.

  Bindings (Map Channel → adapter label) is host-only. It is not a field of
  Open. A missing key is ChannelUnbound at lookup, not a Refusal of decide.
  InboundMatch is host-only. A miss or a duplicate identity is UnknownSender,
  not a Refusal of decide and not a new Arrival.

  ⭐ ENFORCED BY: this file. `dotnet fsi leadqualifier/workitem.fsx` → N passed, 0 failed.
  ⭐ Host port: `leadqualifier/workitem.py`. When they disagree, this file wins.

  Loads nothing. Floor is the law count printed as `LAWS n`.
*)

open System

// --------------------------------------------------------------------------- contract

type WorkItemId = WorkItemId of string
type IcpVersionId = IcpVersionId of string
type PersonId = PersonId of string
type ImportId = ImportId of string

type Arrival =
    | ApolloPerson of PersonId
    | CsvRow of importId: ImportId * row: int

type Tier =
    | Hot
    | Warm
    | Nurture
    | Disqualify
    | Existing

type Judgement =
    | Unjudged
    | Judged of version: IcpVersionId * tier: Tier * needsReview: bool

type Disposition =
    | Unreviewed
    | HeldForHuman
    | Dismissed
    | QueuedForSequence
    | HandedToCloser

type Relay =
    | NoWrite
    | Pending
    | Delivered of remoteId: string
    | Failed of reason: string

type Channel =
    | Email
    | LinkedIn
    | Voice
    | Sms
    | RinglessVoicemail

type Offer =
    | Copy of string
    | CaseStudy of url: string
    | QualifyingQuestion of string
    | Calendar of slots: string list
    | Form of url: string
    | DeclineDraft of string

type Draft =
    { Channel: Channel
      Offer: Offer }

// HOST only. Not stored on Open. The map value is a label, not a vendor type.
type DispatchError =
    | ChannelUnbound
    | NoAddress

let lookup (bindings: Map<Channel, string>) (ch: Channel) : Result<string, DispatchError> =
    match Map.tryFind ch bindings with
    | Some id -> Ok id
    | None -> Error ChannelUnbound

let fakeBindings : Map<Channel, string> =
    [ Email; LinkedIn; Voice; Sms; RinglessVoicemail ]
    |> List.map (fun c -> c, "fake")
    |> Map.ofList

// HOST only. Not stored on Open. A miss is UnknownSender, not a Refusal of decide.
type InboundHint =
    | ByWorkItem of WorkItemId
    | ByEmail of string
    | ByPhone of string

type InboundMatch =
    | Matched of WorkItemId
    | UnknownSender

type Directory =
    { ById: Set<WorkItemId>
      ByEmail: Map<string, WorkItemId list>
      ByPhone: Map<string, WorkItemId list> }

let matchInbound (dir: Directory) (hint: InboundHint) : InboundMatch =
    let one ids =
        match ids with
        | [id] -> Matched id
        | _ -> UnknownSender
    match hint with
    | ByWorkItem id -> if Set.contains id dir.ById then Matched id else UnknownSender
    | ByEmail e when String.IsNullOrWhiteSpace e -> UnknownSender
    | ByEmail e -> one (defaultArg (Map.tryFind e dir.ByEmail) [])
    | ByPhone p when String.IsNullOrWhiteSpace p -> UnknownSender
    | ByPhone p -> one (defaultArg (Map.tryFind p dir.ByPhone) [])

type Outbound =
    | NoSend
    | Pending of Draft
    | Dispatched of remoteId: string
    | Failed of reason: string

type Contact =
    | Hidden
    | Revealed

type SearchFilters =
    { Titles: string list
      Locations: string list
      EmployeeRanges: string list
      Keywords: string list }

let filtersFromIcp (titles: string list) (geography: string) : SearchFilters =
    { Titles = titles |> List.filter (fun t -> t.Trim() <> "")
      Locations = if geography.Trim().ToLowerInvariant() = "anywhere" then [] else [ geography.Trim() ]
      EmployeeRanges = []
      Keywords = [] }

type Refusal =
    | NotArrived
    | AlreadyArrived
    | NotJudged
    | NotHeld
    | NotHot
    | NotSequenceable
    | NotQueueable
    | AlreadyDismissed
    | NotDismissable
    | AlreadyHandedOff
    | NotHandoffable
    | RelayNotPending
    | EmptyReply
    | EmptyDraft
    | NotSendable
    | OutboundNotPending

type Command =
    | Arrive of Arrival
    | Flag
    | Dismiss
    | Queue of Draft
    | HandOff of Draft
    | SendDecline of Draft
    | RecordReply of body: string
    | MarkDelivered of remoteId: string
    | MarkFailed of reason: string
    | MarkDispatched of remoteId: string
    | MarkDispatchFailed of reason: string

type Event =
    | Arrived of Arrival
    | Flagged
    | PersonDismissed
    | Queued
    | HandedOff
    | ReplyArrived of body: string
    | RelayPending
    | RelayDelivered of remoteId: string
    | RelayFailed of reason: string
    | OutboundPending of Draft
    | OutboundDispatched of remoteId: string
    | OutboundFailed of reason: string

type State =
    | Nothing
    | Open of arrival: Arrival * disposition: Disposition * relay: Relay * outbound: Outbound

let blank (s: string) = String.IsNullOrWhiteSpace s

// emptyOffer is exhaustive — a new Offer arm is a compiler error until named here.
let emptyOffer =
    function
    | Copy s
    | QualifyingQuestion s
    | CaseStudy s
    | Form s
    | DeclineDraft s -> blank s
    | Calendar slots -> List.isEmpty slots

let emptyDraft (d: Draft) = emptyOffer d.Offer

let declineNotSent =
    function
    | DeclineDraft s -> not (blank s)
    | Copy _
    | CaseStudy _
    | QualifyingQuestion _
    | Calendar _
    | Form _ -> false

// --------------------------------------------------------------------------- decide / evolve / contact

let decide (cmd: Command) (state: State) (judgement: Judgement) : Result<Event list, Refusal> =
    match cmd, state, judgement with
    | Arrive a, Nothing, _ -> Ok [ Arrived a ]
    | Arrive _, Open _, _ -> Error AlreadyArrived

    | Flag, Nothing, _ -> Error NotArrived
    | Flag, Open (_, Unreviewed, _, _), Unjudged -> Error NotJudged
    | Flag, Open (_, Unreviewed, _, _), Judged (_, _, true) -> Ok [ Flagged ]
    | Flag, Open (_, Unreviewed, _, _), Judged (_, _, false) -> Error NotHeld
    | Flag, Open (_, _, _, _), _ -> Error NotHeld

    | Dismiss, Nothing, _ -> Error NotArrived
    | Dismiss, Open (_, Unreviewed, _, _), _
    | Dismiss, Open (_, HeldForHuman, _, _), _ -> Ok [ PersonDismissed ]
    | Dismiss, Open (_, Dismissed, _, _), _ -> Error AlreadyDismissed
    | Dismiss, Open (_, QueuedForSequence, _, _), _
    | Dismiss, Open (_, HandedToCloser, _, _), _ -> Error NotDismissable

    | Queue _, Nothing, _ -> Error NotArrived
    | Queue _, Open (_, Unreviewed, _, _), Unjudged
    | Queue _, Open (_, HeldForHuman, _, _), Unjudged -> Error NotJudged
    | Queue _, Open (_, Unreviewed, _, _), Judged (_, Disqualify, _)
    | Queue _, Open (_, HeldForHuman, _, _), Judged (_, Disqualify, _)
    | Queue _, Open (_, Unreviewed, _, _), Judged (_, Existing, _)
    | Queue _, Open (_, HeldForHuman, _, _), Judged (_, Existing, _) -> Error NotSequenceable
    | Queue _, Open (_, Unreviewed, _, _), Judged (_, Nurture, _)
    | Queue _, Open (_, HeldForHuman, _, _), Judged (_, Nurture, _) -> Ok [ Queued ]
    | Queue draft, Open (_, Unreviewed, _, _), Judged (_, Hot, _)
    | Queue draft, Open (_, Unreviewed, _, _), Judged (_, Warm, _)
    | Queue draft, Open (_, HeldForHuman, _, _), Judged (_, Hot, _)
    | Queue draft, Open (_, HeldForHuman, _, _), Judged (_, Warm, _) ->
        if emptyDraft draft then Error EmptyDraft
        elif declineNotSent draft.Offer then Error NotSendable
        else Ok [ Queued; OutboundPending draft ]
    | Queue _, Open (_, Dismissed, _, _), _
    | Queue _, Open (_, QueuedForSequence, _, _), _
    | Queue _, Open (_, HandedToCloser, _, _), _ -> Error NotQueueable

    | HandOff _, Nothing, _ -> Error NotArrived
    | HandOff _, Open (_, Unreviewed, _, _), Unjudged
    | HandOff _, Open (_, HeldForHuman, _, _), Unjudged -> Error NotJudged
    | HandOff draft, Open (_, Unreviewed, _, _), Judged (_, Hot, _)
    | HandOff draft, Open (_, HeldForHuman, _, _), Judged (_, Hot, _) ->
        if emptyDraft draft then Error EmptyDraft
        elif declineNotSent draft.Offer then Error NotSendable
        else Ok [ HandedOff; RelayPending; OutboundPending draft ]
    | HandOff _, Open (_, Unreviewed, _, _), Judged _
    | HandOff _, Open (_, HeldForHuman, _, _), Judged _ -> Error NotHot
    | HandOff _, Open (_, HandedToCloser, _, _), _ -> Error AlreadyHandedOff
    | HandOff _, Open (_, Dismissed, _, _), _
    | HandOff _, Open (_, QueuedForSequence, _, _), _ -> Error NotHandoffable

    | SendDecline _, Nothing, _ -> Error NotArrived
    | SendDecline _, Open (_, Unreviewed, _, _), Unjudged
    | SendDecline _, Open (_, HeldForHuman, _, _), Unjudged -> Error NotJudged
    | SendDecline draft, Open (_, Unreviewed, _, _), Judged (_, Disqualify, _)
    | SendDecline draft, Open (_, HeldForHuman, _, _), Judged (_, Disqualify, _) ->
        if emptyDraft draft then Error EmptyDraft
        elif declineNotSent draft.Offer then Ok [ PersonDismissed; OutboundPending draft ]
        else Error NotSendable
    | SendDecline _, Open (_, Unreviewed, _, _), Judged _
    | SendDecline _, Open (_, HeldForHuman, _, _), Judged _ -> Error NotSequenceable
    | SendDecline _, Open (_, Dismissed, _, _), _ -> Error AlreadyDismissed
    | SendDecline _, Open (_, QueuedForSequence, _, _), _
    | SendDecline _, Open (_, HandedToCloser, _, _), _ -> Error NotDismissable

    | RecordReply _, Nothing, _ -> Error NotArrived
    | RecordReply body, Open _, _ when blank body -> Error EmptyReply
    | RecordReply body, Open _, _ -> Ok [ ReplyArrived body ]

    | MarkDelivered remoteId, Open (_, _, Relay.Pending, _), _ -> Ok [ RelayDelivered remoteId ]
    | MarkDelivered _, _, _ -> Error RelayNotPending
    | MarkFailed reason, Open (_, _, Relay.Pending, _), _ -> Ok [ RelayFailed reason ]
    | MarkFailed _, _, _ -> Error RelayNotPending

    | MarkDispatched remoteId, Open (_, _, _, Outbound.Pending _), _ -> Ok [ OutboundDispatched remoteId ]
    | MarkDispatched _, _, _ -> Error OutboundNotPending
    | MarkDispatchFailed reason, Open (_, _, _, Outbound.Pending _), _ -> Ok [ OutboundFailed reason ]
    | MarkDispatchFailed _, _, _ -> Error OutboundNotPending

let evolve (state: State) (event: Event) : Result<State, Refusal> =
    match state, event with
    | Nothing, Arrived a -> Ok (Open (a, Unreviewed, Relay.NoWrite, Outbound.NoSend))
    | Open (a, _, r, o), Flagged -> Ok (Open (a, HeldForHuman, r, o))
    | Open (a, _, r, o), PersonDismissed -> Ok (Open (a, Dismissed, r, o))
    | Open (a, _, r, o), Queued -> Ok (Open (a, QueuedForSequence, r, o))
    | Open (a, _, r, o), HandedOff -> Ok (Open (a, HandedToCloser, r, o))
    | Open (a, _, r, o), ReplyArrived _ -> Ok (Open (a, Unreviewed, r, o))
    | Open (a, d, _, o), RelayPending -> Ok (Open (a, d, Relay.Pending, o))
    | Open (a, d, Relay.Pending, o), RelayDelivered remoteId -> Ok (Open (a, d, Relay.Delivered remoteId, o))
    | Open (a, d, Relay.Pending, o), RelayFailed reason -> Ok (Open (a, d, Relay.Failed reason, o))
    | Open (a, d, r, _), OutboundPending draft -> Ok (Open (a, d, r, Outbound.Pending draft))
    | Open (a, d, r, Outbound.Pending _), OutboundDispatched remoteId -> Ok (Open (a, d, r, Outbound.Dispatched remoteId))
    | Open (a, d, r, Outbound.Pending _), OutboundFailed reason -> Ok (Open (a, d, r, Outbound.Failed reason))
    | _, _ -> Error NotArrived

let fold (state: State) (events: Event list) : Result<State, Refusal> =
    let rec go s es =
        match es with
        | [] -> Ok s
        | e :: rest ->
            match evolve s e with
            | Error r -> Error r
            | Ok s' -> go s' rest
    go state events

let apply cmd state judgement =
    match decide cmd state judgement with
    | Error r -> Error r
    | Ok events ->
        match fold state events with
        | Error r -> Error r
        | Ok s -> Ok (s, events)

let contactOf (state: State) : Contact =
    match state with
    | Nothing -> Hidden
    | Open (_, Unreviewed, _, _) -> Hidden
    | Open (_, Dismissed, _, _) -> Hidden
    | Open (_, HeldForHuman, _, _) -> Revealed
    | Open (_, QueuedForSequence, _, _) -> Revealed
    | Open (_, HandedToCloser, _, _) -> Revealed

// --------------------------------------------------------------------------- helpers

let v = IcpVersionId "v1"
let judgedHot = Judged (v, Hot, false)
let judgedHotReview = Judged (v, Hot, true)
let judgedWarm = Judged (v, Warm, false)
let judgedNurture = Judged (v, Nurture, false)
let judgedDq = Judged (v, Disqualify, false)
let judgedExisting = Judged (v, Existing, false)
let birth = ApolloPerson (PersonId "p1")

let copyDraft =
    { Channel = Email
      Offer = Copy "Hi — case study" }

let calendarDraft =
    { Channel = Voice
      Offer = Calendar [ "Tuesday 11:00 CET"; "Thursday 15:00 CET" ] }

let questionDraft =
    { Channel = Email
      Offer = QualifyingQuestion "roughly how many clients do you serve today?" }

let declineDraft =
    { Channel = Email
      Offer = DeclineDraft "not a fit" }

let born () =
    match apply (Arrive birth) Nothing Unjudged with
    | Ok (s, _) -> s
    | Error r -> failwithf "born failed: %A" r

let mustOk name (r: Result<'a, Refusal>) =
    match r with
    | Ok x -> x
    | Error e -> failwithf "%s: expected Ok, got Error %A" name e

let mustErr name expected (r: Result<'a, Refusal>) =
    match r with
    | Error e when e = expected -> ()
    | Error e -> failwithf "%s: expected %A, got %A" name expected e
    | Ok _ -> failwithf "%s: expected Error %A, got Ok" name expected

let dispOf =
    function
    | Open (_, d, _, _) -> d
    | Nothing -> failwith "Nothing"

let relayOf =
    function
    | Open (_, _, r, _) -> r
    | Nothing -> failwith "Nothing"

let outboundOf =
    function
    | Open (_, _, _, o) -> o
    | Nothing -> failwith "Nothing"

// --------------------------------------------------------------------------- laws

let passed = ref 0
let failed = ref 0

let law (n: int) (name: string) (ok: bool) =
    if ok then
        passed.Value <- passed.Value + 1
    else
        failed.Value <- failed.Value + 1
        eprintfn "FAIL L%d %s" n name

try
    // L1 Arrive on Nothing yields Unreviewed, NoWrite, NoSend.
    // RED: in evolve, Open (a, Unreviewed, NoWrite, NoSend) → Open (a, HeldForHuman, NoWrite, NoSend)
    let s1, e1 = apply (Arrive birth) Nothing Unjudged |> mustOk "L1"
    law 1 "arrive-unreviewed" (dispOf s1 = Unreviewed && relayOf s1 = Relay.NoWrite && outboundOf s1 = Outbound.NoSend && e1 = [ Arrived birth ])

    // L2 A second Arrive is AlreadyArrived.
    apply (Arrive birth) s1 Unjudged |> mustErr "L2" AlreadyArrived
    law 2 "arrive-twice" true

    // L3 Flag while Unjudged is NotJudged.
    apply Flag (born ()) Unjudged |> mustErr "L3" NotJudged
    law 3 "flag-unjudged" true

    // L4 Flag when judged and needsReview from Unreviewed → HeldForHuman.
    let s4, _ = apply Flag (born ()) judgedHotReview |> mustOk "L4"
    law 4 "flag-held" (dispOf s4 = HeldForHuman)

    // L5 Flag when judged and not needsReview is NotHeld.
    apply Flag (born ()) judgedHot |> mustErr "L5" NotHeld
    law 5 "flag-not-held" true

    // L6 Queue while Unjudged is NotJudged.
    apply (Queue copyDraft) (born ()) Unjudged |> mustErr "L6" NotJudged
    law 6 "queue-unjudged" true

    // L7 Queue of Disqualify is NotSequenceable. Outbound stays NoSend.
    apply (Queue copyDraft) (born ()) judgedDq |> mustErr "L7" NotSequenceable
    law 7 "queue-disqualify" true

    // L8 Queue of Existing is NotSequenceable.
    apply (Queue copyDraft) (born ()) judgedExisting |> mustErr "L8" NotSequenceable
    law 8 "queue-existing" true

    // L9 Queue of Warm from Unreviewed → QueuedForSequence and OutboundPending Email Copy.
    // RED: omit OutboundPending from the event list
    let s9, ev9 = apply (Queue copyDraft) (born ()) judgedWarm |> mustOk "L9"
    law 9 "queue-warm" (dispOf s9 = QueuedForSequence && outboundOf s9 = Outbound.Pending copyDraft && ev9 = [ Queued; OutboundPending copyDraft ])

    // L10 Queue of Hot is allowed (handoff is a different command).
    let s10, _ = apply (Queue copyDraft) (born ()) judgedHot |> mustOk "L10"
    law 10 "queue-hot" (dispOf s10 = QueuedForSequence && outboundOf s10 = Outbound.Pending copyDraft)

    // L11 Queue of Nurture is a decision with NoSend (no personal outreach).
    let s11, ev11 = apply (Queue copyDraft) (born ()) judgedNurture |> mustOk "L11"
    law 11 "queue-nurture" (dispOf s11 = QueuedForSequence && outboundOf s11 = Outbound.NoSend && ev11 = [ Queued ])

    // L12 HandOff while Unjudged is NotJudged.
    apply (HandOff calendarDraft) (born ()) Unjudged |> mustErr "L12" NotJudged
    law 12 "handoff-unjudged" true

    // L13 HandOff when not Hot is NotHot.
    apply (HandOff calendarDraft) (born ()) judgedWarm |> mustErr "L13" NotHot
    law 13 "handoff-not-hot" true

    // L14 HandOff of Hot from Unreviewed → HandedToCloser, HubSpot Pending, Voice Calendar OutboundPending.
    // RED: omit OutboundPending from the event list
    let s14, ev14 = apply (HandOff calendarDraft) (born ()) judgedHot |> mustOk "L14"
    law 14 "handoff-hot-relay" (
        dispOf s14 = HandedToCloser
        && relayOf s14 = Relay.Pending
        && outboundOf s14 = Outbound.Pending calendarDraft
        && ev14 = [ HandedOff; RelayPending; OutboundPending calendarDraft ])

    // L15 A second HandOff is AlreadyHandedOff. It does not enqueue a second pending.
    apply (HandOff calendarDraft) s14 judgedHot |> mustErr "L15" AlreadyHandedOff
    law 15 "handoff-twice" true

    // L16 Dismiss from Unreviewed → Dismissed. Relay stays NoWrite. Outbound stays NoSend.
    let s16, _ = apply Dismiss (born ()) judgedWarm |> mustOk "L16"
    law 16 "dismiss-unreviewed" (dispOf s16 = Dismissed && relayOf s16 = Relay.NoWrite && outboundOf s16 = Outbound.NoSend)

    // L17 A second Dismiss is AlreadyDismissed.
    // RED: Dismiss on Dismissed → Ok [PersonDismissed]
    apply Dismiss s16 judgedWarm |> mustErr "L17" AlreadyDismissed
    law 17 "dismiss-twice" true

    // L18 Dismiss from QueuedForSequence is NotDismissable.
    apply Dismiss s9 judgedWarm |> mustErr "L18" NotDismissable
    law 18 "dismiss-queued" true

    // L19 ReplyArrived from Dismissed returns Unreviewed. The only exit from Dismissed.
    let s19, _ = apply (RecordReply "ping") s16 Unjudged |> mustOk "L19"
    law 19 "reply-reopens-dismissed" (dispOf s19 = Unreviewed)

    // L20 ReplyArrived from HandedToCloser returns Unreviewed and keeps relay and outbound.
    let s20, _ = apply (RecordReply "Tuesday works") s14 Unjudged |> mustOk "L20"
    law 20 "reply-reopens-handed" (dispOf s20 = Unreviewed && relayOf s20 = Relay.Pending && outboundOf s20 = Outbound.Pending calendarDraft)

    // L21 CsvRow is a valid birth, same disposition as ApolloPerson.
    let csv = CsvRow (ImportId "imp", 3)
    let s21, _ = apply (Arrive csv) Nothing Unjudged |> mustOk "L21"
    law 21 "csv-birth" (match s21 with Open (CsvRow _, Unreviewed, Relay.NoWrite, Outbound.NoSend) -> true | _ -> false)

    // L22 Contact is Hidden on Unreviewed and Dismissed, Revealed after Flag, Queue, HandOff.
    law 22 "contact-hidden-unreviewed" (contactOf (born ()) = Hidden)
    law 23 "contact-hidden-dismissed" (contactOf s16 = Hidden)
    law 24 "contact-revealed-held" (contactOf s4 = Revealed)
    law 25 "contact-revealed-queued" (contactOf s9 = Revealed)
    law 26 "contact-revealed-handed" (contactOf s14 = Revealed)

    // L27 MarkDelivered only from Pending.
    apply (MarkDelivered "hs-1") (born ()) judgedHot |> mustErr "L27" RelayNotPending
    law 27 "deliver-not-pending" true
    let s27, _ = apply (MarkDelivered "hs-1") s14 judgedHot |> mustOk "L27b"
    law 28 "deliver-pending" (relayOf s27 = Relay.Delivered "hs-1")

    // L29 Flag, Queue, HandOff from Nothing is NotArrived.
    apply Flag Nothing Unjudged |> mustErr "L29a" NotArrived
    apply (Queue copyDraft) Nothing judgedWarm |> mustErr "L29b" NotArrived
    apply (HandOff calendarDraft) Nothing judgedHot |> mustErr "L29c" NotArrived
    law 29 "commands-on-nothing" true

    // L30 Queue from HeldForHuman of Warm works (human releases to sequence).
    let s30, _ = apply (Queue copyDraft) s4 judgedWarm |> mustOk "L30"
    law 30 "queue-from-held" (dispOf s30 = QueuedForSequence && outboundOf s30 = Outbound.Pending copyDraft)

    // L31 HandOff from HeldForHuman of Hot works.
    let s31, _ = apply (HandOff calendarDraft) s4 judgedHot |> mustOk "L31"
    law 31 "handoff-from-held" (dispOf s31 = HandedToCloser && relayOf s31 = Relay.Pending && outboundOf s31 = Outbound.Pending calendarDraft)

    // L32 evolve refuses an event that has no arm (Arrived on Open).
    evolve s1 (Arrived birth) |> mustErr "L32" NotArrived
    law 32 "evolve-refuses" true

    // L33 Judgement is an argument, not a field of State. Open has four parts.
    law 33 "state-has-no-judgement" (
        match born () with
        | Open (_, _, _, _) -> true
        | Nothing -> false)

    // L34 Empty titles is still a valid People Search filter.
    let emptyF = filtersFromIcp [] "anywhere"
    law 34 "search-empty-titles" (emptyF.Titles = [] && emptyF.Locations = [])

    // L35 Geography "anywhere" means no location filter.
    law 35 "search-anywhere" ((filtersFromIcp [ "Founder" ] "anywhere").Locations = [])

    // L36 Persona titles are copied; a named geography is a location.
    let f36 = filtersFromIcp [ "Founder / Owner"; "Head of Growth" ] "Hamburg"
    law 36 "search-titles-geo" (f36.Titles = [ "Founder / Owner"; "Head of Growth" ] && f36.Locations = [ "Hamburg" ])

    // L37 A second Queue does not enqueue a second pending.
    apply (Queue copyDraft) s9 judgedWarm |> mustErr "L37" NotQueueable
    law 37 "queue-twice" true

    // L38 Empty RecordReply refuses. Whitespace is empty.
    apply (RecordReply "") s16 Unjudged |> mustErr "L38a" EmptyReply
    apply (RecordReply "   ") s16 Unjudged |> mustErr "L38b" EmptyReply
    law 38 "reply-empty" true

    // L39 RecordReply of body carries that body on the event.
    let _, ev39 = apply (RecordReply "thanks") s16 Unjudged |> mustOk "L39"
    law 39 "reply-carries-body" (ev39 = [ ReplyArrived "thanks" ])

    // L40 Empty Queue Copy of Warm is EmptyDraft. Outbound stays NoSend.
    let emptyCopy = { copyDraft with Offer = Copy "" }
    apply (Queue emptyCopy) (born ()) judgedWarm |> mustErr "L40" EmptyDraft
    law 40 "queue-empty-draft" true

    // L41 MarkDispatched only from Outbound Pending.
    apply (MarkDispatched "seq-1") (born ()) judgedWarm |> mustErr "L41" OutboundNotPending
    law 41 "dispatch-not-pending" true

    // L42 MarkDispatched from Pending → Dispatched.
    let s42, _ = apply (MarkDispatched "seq-1") s9 judgedWarm |> mustOk "L42"
    law 42 "dispatch-pending" (outboundOf s42 = Outbound.Dispatched "seq-1")

    // L43 MarkDispatchFailed from Pending → Failed.
    let s43, _ = apply (MarkDispatchFailed "no_address") s9 judgedWarm |> mustOk "L43"
    law 43 "dispatch-failed" (outboundOf s43 = Outbound.Failed "no_address")

    // L44 Queue of Disqualify leaves a born item at NoSend (refusal, no evolve).
    law 44 "disqualify-stays-nosend" (outboundOf (born ()) = Outbound.NoSend)

    // L45 contactOf after RecordReply on HandedToCloser is Hidden (Unreviewed).
    law 45 "contact-hidden-after-reply" (contactOf s20 = Hidden)

    // L46 Empty HandOff Calendar of Hot is EmptyDraft.
    let emptyCalendar = { calendarDraft with Offer = Calendar [] }
    apply (HandOff emptyCalendar) (born ()) judgedHot |> mustErr "L46" EmptyDraft
    law 46 "handoff-empty-draft" true

    // L47 MarkDispatchFailed on Unreviewed (NoSend) is OutboundNotPending.
    apply (MarkDispatchFailed "x") (born ()) judgedWarm |> mustErr "L47" OutboundNotPending
    law 47 "fail-not-pending" true

    // L48 LinkedIn is a valid Queue channel (Warm). Copy, not email-by-default.
    let liDraft = { copyDraft with Channel = LinkedIn }
    let s48, ev48 = apply (Queue liDraft) (born ()) judgedWarm |> mustOk "L48"
    law 48 "queue-linkedin" (outboundOf s48 = Outbound.Pending liDraft && ev48 = [ Queued; OutboundPending liDraft ])

    // L49 Sms Queue of Warm + Copy → Pending Sms.
    let smsDraft = { Channel = Sms; Offer = Copy "hi" }
    let s49, _ = apply (Queue smsDraft) (born ()) judgedWarm |> mustOk "L49"
    law 49 "sms-queue-warm" (outboundOf s49 = Outbound.Pending smsDraft)

    // L50 RinglessVoicemail Queue of Warm + Copy → Pending RinglessVoicemail.
    let rvmDraft = { Channel = RinglessVoicemail; Offer = Copy "hi" }
    let s50, _ = apply (Queue rvmDraft) (born ()) judgedWarm |> mustOk "L50"
    law 50 "rvm-queue-warm" (outboundOf s50 = Outbound.Pending rvmDraft)

    // L51 Calendar [] Queue of Warm is EmptyDraft.
    // RED: omit `Calendar slots -> List.isEmpty slots` from emptyOffer
    let emptyCalWarm = { Channel = Voice; Offer = Calendar [] }
    apply (Queue emptyCalWarm) (born ()) judgedWarm |> mustErr "L51" EmptyDraft
    law 51 "calendar-empty" true

    // L52 CaseStudy "" Queue of Warm is EmptyDraft.
    apply (Queue { Channel = Email; Offer = CaseStudy "" }) (born ()) judgedWarm |> mustErr "L52" EmptyDraft
    law 52 "casestudy-blank" true

    // L53 Form whitespace Queue of Warm is EmptyDraft.
    apply (Queue { Channel = Email; Offer = Form "   " }) (born ()) judgedWarm |> mustErr "L53" EmptyDraft
    law 53 "form-blank" true

    // L54 QualifyingQuestion "" Queue of Warm is EmptyDraft.
    apply (Queue { Channel = Email; Offer = QualifyingQuestion "" }) (born ()) judgedWarm |> mustErr "L54" EmptyDraft
    law 54 "question-blank" true

    // L55 DeclineDraft "" Queue of Warm is EmptyDraft (emptiness beats NotSendable).
    apply (Queue { Channel = Email; Offer = DeclineDraft "" }) (born ()) judgedWarm |> mustErr "L55" EmptyDraft
    law 55 "decline-blank" true

    // L56 Nonempty DeclineDraft is NotSendable on Queue of Warm and HandOff of Hot.
    apply (Queue declineDraft) (born ()) judgedWarm |> mustErr "L56a" NotSendable
    apply (HandOff declineDraft) (born ()) judgedHot |> mustErr "L56b" NotSendable
    law 56 "decline-not-sent" true

    // L57 Fake bindings cover every Channel.
    let allChannels = [ Email; LinkedIn; Voice; Sms; RinglessVoicemail ]
    law 57 "fake-bindings-five" (Map.count fakeBindings = 5 && List.forall (fun c -> Map.containsKey c fakeBindings) allChannels)

    // L58 lookup of bound Email is Ok "fake".
    law 58 "lookup-bound-email" (lookup fakeBindings Email = Ok "fake")

    // L59 lookup of Sms on an empty map is ChannelUnbound.
    // RED: lookup _ _ -> Ok "fake"
    law 59 "lookup-missing-sms" (lookup Map.empty Sms = Error ChannelUnbound)

    // L60 swapping Email leaves Voice fake.
    let swapped = Map.add Email "email-vendor" fakeBindings
    law 60 "swap-email-keeps-voice" (lookup swapped Email = Ok "email-vendor" && lookup swapped Voice = Ok "fake")

    // L61 Bindings is not a field of Open. A fifth part fails this match at compile time.
    law 61 "state-has-no-bindings" (
        match born () with
        | Open (_, _, _, _) -> true
        | Nothing -> false)

    let emptyDir = { ById = Set.empty; ByEmail = Map.empty; ByPhone = Map.empty }
    let widA = WorkItemId "A"
    let widB = WorkItemId "B"
    let idDir = { emptyDir with ById = Set.singleton widA }
    let emailOne = { emptyDir with ByEmail = Map.ofList [ "ada@x.test", [ widA ] ] }
    let emailTwo = { emptyDir with ByEmail = Map.ofList [ "ada@x.test", [ widA; widB ] ] }
    let phoneOne = { emptyDir with ByPhone = Map.ofList [ "+494012345", [ widA ] ] }

    // L62 ByWorkItem of a known id is Matched.
    law 62 "match-by-id" (matchInbound idDir (ByWorkItem widA) = Matched widA)

    // L63 ByWorkItem on an empty directory is UnknownSender.
    // RED: miss -> Matched (WorkItemId "x")
    law 63 "unknown-id" (matchInbound emptyDir (ByWorkItem widA) = UnknownSender)

    // L64 one email mapping is Matched.
    law 64 "match-by-email" (matchInbound emailOne (ByEmail "ada@x.test") = Matched widA)

    // L65 missing email and a two-id list are both UnknownSender.
    law 65 "email-zero-or-two" (
        matchInbound emptyDir (ByEmail "ada@x.test") = UnknownSender
        && matchInbound emailTwo (ByEmail "ada@x.test") = UnknownSender)

    // L66 one phone mapping is Matched.
    law 66 "match-by-phone" (matchInbound phoneOne (ByPhone "+494012345") = Matched widA)

    // L67 blank email is UnknownSender.
    law 67 "blank-email" (
        matchInbound emailOne (ByEmail "") = UnknownSender
        && matchInbound emailOne (ByEmail "   ") = UnknownSender)

    // L68 InboundMatch is not a field of Open.
    law 68 "inbound-not-on-open" (
        match born () with
        | Open (_, _, _, _) -> true
        | Nothing -> false)

    // L69 SendDecline of nonempty DeclineDraft on Disqualify emits PersonDismissed then OutboundPending.
    let s69, ev69 = apply (SendDecline declineDraft) (born ()) judgedDq |> mustOk "L69"
    law 69 "send-decline-disqualify" (
        match s69, ev69 with
        | Open (_, Dismissed, _, Outbound.Pending d), [ PersonDismissed; OutboundPending d' ] ->
            d = declineDraft && d' = declineDraft
        | _ -> false)

    // L70 empty DeclineDraft is EmptyDraft.
    apply (SendDecline { Channel = Email; Offer = DeclineDraft "" }) (born ()) judgedDq
    |> mustErr "L70" EmptyDraft
    law 70 "send-decline-empty" true

    // L71 Copy on Disqualify SendDecline is NotSendable.
    apply (SendDecline copyDraft) (born ()) judgedDq |> mustErr "L71" NotSendable
    law 71 "send-decline-copy-not-sendable" true

    // L72 SendDecline on Warm is NotSequenceable.
    apply (SendDecline declineDraft) (born ()) judgedWarm |> mustErr "L72" NotSequenceable
    law 72 "send-decline-warm-not-sequenceable" true

    // L73 SendDecline on already Dismissed is AlreadyDismissed.
    let s73, _ = apply Dismiss (born ()) judgedDq |> mustOk "L73a"
    apply (SendDecline declineDraft) s73 judgedDq |> mustErr "L73" AlreadyDismissed
    law 73 "send-decline-already-dismissed" true

    // L74 contactOf after SendDecline is Hidden (Dismissed).
    let s74, _ = apply (SendDecline declineDraft) (born ()) judgedDq |> mustOk "L74"
    law 74 "send-decline-contact-hidden" (contactOf s74 = Hidden)

    // L75 outbound after SendDecline is Pending of that draft (drain reads payload, not Revealed).
    law 75 "send-decline-outbound-pending" (
        match s74 with
        | Open (_, Dismissed, _, Outbound.Pending d) -> d = declineDraft
        | _ -> false)

with ex ->
    failed.Value <- failed.Value + 1
    eprintfn "FAIL exception: %s" ex.Message

let laws = passed.Value + failed.Value
printfn "%d passed, %d failed" passed.Value failed.Value
printfn "LAWS %d" laws
if failed.Value > 0 then exit 1
exit 0
