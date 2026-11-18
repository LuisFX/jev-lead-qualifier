(**
  Work item — the aggregate this product owns.

  A person arrives (Apollo person, or a CSV row). Jev answers live on a
  fingerprint ledger. `assemble` in scoring.py folds those answers under one
  ICP version into a Judgement. That fold is NOT stored on this aggregate.
  Disposition is. Relay is the HubSpot outbox for a Hot handoff.

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

type Command =
    | Arrive of Arrival
    | Flag
    | Dismiss
    | Queue
    | HandOff
    | RecordReply
    | MarkDelivered of remoteId: string
    | MarkFailed of reason: string

type Event =
    | Arrived of Arrival
    | Flagged
    | PersonDismissed
    | Queued
    | HandedOff
    | ReplyArrived
    | RelayPending
    | RelayDelivered of remoteId: string
    | RelayFailed of reason: string

type State =
    | Nothing
    | Open of arrival: Arrival * disposition: Disposition * relay: Relay

// --------------------------------------------------------------------------- decide / evolve / contact

let decide (cmd: Command) (state: State) (judgement: Judgement) : Result<Event list, Refusal> =
    match cmd, state, judgement with
    | Arrive a, Nothing, _ -> Ok [ Arrived a ]
    | Arrive _, Open _, _ -> Error AlreadyArrived

    | Flag, Nothing, _ -> Error NotArrived
    | Flag, Open (_, Unreviewed, _), Unjudged -> Error NotJudged
    | Flag, Open (_, Unreviewed, _), Judged (_, _, true) -> Ok [ Flagged ]
    | Flag, Open (_, Unreviewed, _), Judged (_, _, false) -> Error NotHeld
    | Flag, Open (_, _, _), _ -> Error NotHeld

    | Dismiss, Nothing, _ -> Error NotArrived
    | Dismiss, Open (_, Unreviewed, _), _
    | Dismiss, Open (_, HeldForHuman, _), _ -> Ok [ PersonDismissed ]
    | Dismiss, Open (_, Dismissed, _), _ -> Error AlreadyDismissed
    | Dismiss, Open (_, QueuedForSequence, _), _
    | Dismiss, Open (_, HandedToCloser, _), _ -> Error NotDismissable

    | Queue, Nothing, _ -> Error NotArrived
    | Queue, Open (_, Unreviewed, _), Unjudged
    | Queue, Open (_, HeldForHuman, _), Unjudged -> Error NotJudged
    | Queue, Open (_, Unreviewed, _), Judged (_, Disqualify, _)
    | Queue, Open (_, HeldForHuman, _), Judged (_, Disqualify, _)
    | Queue, Open (_, Unreviewed, _), Judged (_, Existing, _)
    | Queue, Open (_, HeldForHuman, _), Judged (_, Existing, _) -> Error NotSequenceable
    | Queue, Open (_, Unreviewed, _), Judged _
    | Queue, Open (_, HeldForHuman, _), Judged _ -> Ok [ Queued ]
    | Queue, Open (_, Dismissed, _), _
    | Queue, Open (_, QueuedForSequence, _), _
    | Queue, Open (_, HandedToCloser, _), _ -> Error NotQueueable

    | HandOff, Nothing, _ -> Error NotArrived
    | HandOff, Open (_, Unreviewed, _), Unjudged
    | HandOff, Open (_, HeldForHuman, _), Unjudged -> Error NotJudged
    | HandOff, Open (_, Unreviewed, _), Judged (_, Hot, _)
    | HandOff, Open (_, HeldForHuman, _), Judged (_, Hot, _) -> Ok [ HandedOff; RelayPending ]
    | HandOff, Open (_, Unreviewed, _), Judged _
    | HandOff, Open (_, HeldForHuman, _), Judged _ -> Error NotHot
    | HandOff, Open (_, HandedToCloser, _), _ -> Error AlreadyHandedOff
    | HandOff, Open (_, Dismissed, _), _
    | HandOff, Open (_, QueuedForSequence, _), _ -> Error NotHandoffable

    | RecordReply, Nothing, _ -> Error NotArrived
    | RecordReply, Open _, _ -> Ok [ ReplyArrived ]

    | MarkDelivered remoteId, Open (_, _, Pending), _ -> Ok [ RelayDelivered remoteId ]
    | MarkDelivered _, _, _ -> Error RelayNotPending
    | MarkFailed reason, Open (_, _, Pending), _ -> Ok [ RelayFailed reason ]
    | MarkFailed _, _, _ -> Error RelayNotPending

let evolve (state: State) (event: Event) : Result<State, Refusal> =
    match state, event with
    | Nothing, Arrived a -> Ok (Open (a, Unreviewed, NoWrite))
    | Open (a, _, r), Flagged -> Ok (Open (a, HeldForHuman, r))
    | Open (a, _, r), PersonDismissed -> Ok (Open (a, Dismissed, r))
    | Open (a, _, r), Queued -> Ok (Open (a, QueuedForSequence, r))
    | Open (a, _, r), HandedOff -> Ok (Open (a, HandedToCloser, r))
    | Open (a, _, r), ReplyArrived -> Ok (Open (a, Unreviewed, r))
    | Open (a, d, _), RelayPending -> Ok (Open (a, d, Pending))
    | Open (a, d, Pending), RelayDelivered remoteId -> Ok (Open (a, d, Delivered remoteId))
    | Open (a, d, Pending), RelayFailed reason -> Ok (Open (a, d, Failed reason))
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
    | Open (_, Unreviewed, _) -> Hidden
    | Open (_, Dismissed, _) -> Hidden
    | Open (_, HeldForHuman, _) -> Revealed
    | Open (_, QueuedForSequence, _) -> Revealed
    | Open (_, HandedToCloser, _) -> Revealed

// --------------------------------------------------------------------------- helpers

let v = IcpVersionId "v1"
let judgedHot = Judged (v, Hot, false)
let judgedHotReview = Judged (v, Hot, true)
let judgedWarm = Judged (v, Warm, false)
let judgedNurture = Judged (v, Nurture, false)
let judgedDq = Judged (v, Disqualify, false)
let judgedExisting = Judged (v, Existing, false)
let birth = ApolloPerson (PersonId "p1")

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
    | Open (_, d, _) -> d
    | Nothing -> failwith "Nothing"

let relayOf =
    function
    | Open (_, _, r) -> r
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
    // L1 Arrive on Nothing yields Unreviewed and NoWrite.
    // RED: in evolve, Open (a, Unreviewed, NoWrite) → Open (a, HeldForHuman, NoWrite)
    let s1, e1 = apply (Arrive birth) Nothing Unjudged |> mustOk "L1"
    law 1 "arrive-unreviewed" (dispOf s1 = Unreviewed && relayOf s1 = NoWrite && e1 = [ Arrived birth ])

    // L2 A second Arrive is AlreadyArrived.
    // RED: Arrive on Open → Ok [Arrived a]
    apply (Arrive birth) s1 Unjudged |> mustErr "L2" AlreadyArrived
    law 2 "arrive-twice" true

    // L3 Flag while Unjudged is NotJudged.
    // RED: Flag + Unjudged → Ok [Flagged]
    apply Flag (born ()) Unjudged |> mustErr "L3" NotJudged
    law 3 "flag-unjudged" true

    // L4 Flag when judged and needsReview from Unreviewed → HeldForHuman.
    // RED: Flagged evolve → Dismissed
    let s4, _ = apply Flag (born ()) judgedHotReview |> mustOk "L4"
    law 4 "flag-held" (dispOf s4 = HeldForHuman)

    // L5 Flag when judged and not needsReview is NotHeld.
    // RED: Flag + needsReview false → Ok [Flagged]
    apply Flag (born ()) judgedHot |> mustErr "L5" NotHeld
    law 5 "flag-not-held" true

    // L6 Queue while Unjudged is NotJudged.
    // RED: Queue + Unjudged → Ok [Queued]
    apply Queue (born ()) Unjudged |> mustErr "L6" NotJudged
    law 6 "queue-unjudged" true

    // L7 Queue of Disqualify is NotSequenceable.
    // RED: drop the Disqualify arm
    apply Queue (born ()) judgedDq |> mustErr "L7" NotSequenceable
    law 7 "queue-disqualify" true

    // L8 Queue of Existing is NotSequenceable.
    // RED: drop the Existing arm
    apply Queue (born ()) judgedExisting |> mustErr "L8" NotSequenceable
    law 8 "queue-existing" true

    // L9 Queue of Warm from Unreviewed → QueuedForSequence.
    // RED: Queued evolve → Unreviewed
    let s9, _ = apply Queue (born ()) judgedWarm |> mustOk "L9"
    law 9 "queue-warm" (dispOf s9 = QueuedForSequence)

    // L10 Queue of Hot is allowed (handoff is a different command).
    // RED: add Hot to NotSequenceable
    let s10, _ = apply Queue (born ()) judgedHot |> mustOk "L10"
    law 10 "queue-hot" (dispOf s10 = QueuedForSequence)

    // L11 Queue of Nurture is allowed.
    let s11, _ = apply Queue (born ()) judgedNurture |> mustOk "L11"
    law 11 "queue-nurture" (dispOf s11 = QueuedForSequence)

    // L12 HandOff while Unjudged is NotJudged.
    apply HandOff (born ()) Unjudged |> mustErr "L12" NotJudged
    law 12 "handoff-unjudged" true

    // L13 HandOff when not Hot is NotHot.
    // RED: Warm arm → Ok
    apply HandOff (born ()) judgedWarm |> mustErr "L13" NotHot
    law 13 "handoff-not-hot" true

    // L14 HandOff of Hot from Unreviewed → HandedToCloser and Pending.
    // RED: omit RelayPending from the event list
    let s14, ev14 = apply HandOff (born ()) judgedHot |> mustOk "L14"
    law 14 "handoff-hot-relay" (dispOf s14 = HandedToCloser && relayOf s14 = Pending && ev14 = [ HandedOff; RelayPending ])

    // L15 A second HandOff is AlreadyHandedOff.
    apply HandOff s14 judgedHot |> mustErr "L15" AlreadyHandedOff
    law 15 "handoff-twice" true

    // L16 Dismiss from Unreviewed → Dismissed. Relay stays NoWrite.
    let s16, _ = apply Dismiss (born ()) judgedWarm |> mustOk "L16"
    law 16 "dismiss-unreviewed" (dispOf s16 = Dismissed && relayOf s16 = NoWrite)

    // L17 A second Dismiss is AlreadyDismissed.
    // RED: Dismiss on Dismissed → Ok [PersonDismissed]
    apply Dismiss s16 judgedWarm |> mustErr "L17" AlreadyDismissed
    law 17 "dismiss-twice" true

    // L18 Dismiss from QueuedForSequence is NotDismissable.
    apply Dismiss s9 judgedWarm |> mustErr "L18" NotDismissable
    law 18 "dismiss-queued" true

    // L19 ReplyArrived from Dismissed returns Unreviewed. The only exit from Dismissed.
    // RED: ReplyArrived evolve → keep Dismissed
    let s19, _ = apply RecordReply s16 Unjudged |> mustOk "L19"
    law 19 "reply-reopens-dismissed" (dispOf s19 = Unreviewed)

    // L20 ReplyArrived from HandedToCloser returns Unreviewed and keeps the relay.
    let s20, _ = apply RecordReply s14 Unjudged |> mustOk "L20"
    law 20 "reply-reopens-handed" (dispOf s20 = Unreviewed && relayOf s20 = Pending)

    // L21 CsvRow is a valid birth, same disposition as ApolloPerson.
    let csv = CsvRow (ImportId "imp", 3)
    let s21, _ = apply (Arrive csv) Nothing Unjudged |> mustOk "L21"
    law 21 "csv-birth" (match s21 with Open (CsvRow _, Unreviewed, NoWrite) -> true | _ -> false)

    // L22 Contact is Hidden on Unreviewed and Dismissed, Revealed after Flag, Queue, HandOff.
    // RED: contactOf Unreviewed → Revealed
    law 22 "contact-hidden-unreviewed" (contactOf (born ()) = Hidden)
    law 23 "contact-hidden-dismissed" (contactOf s16 = Hidden)
    law 24 "contact-revealed-held" (contactOf s4 = Revealed)
    law 25 "contact-revealed-queued" (contactOf s9 = Revealed)
    law 26 "contact-revealed-handed" (contactOf s14 = Revealed)

    // L27 MarkDelivered only from Pending.
    apply (MarkDelivered "hs-1") (born ()) judgedHot |> mustErr "L27" RelayNotPending
    law 27 "deliver-not-pending" true
    let s27, _ = apply (MarkDelivered "hs-1") s14 judgedHot |> mustOk "L27b"
    law 28 "deliver-pending" (relayOf s27 = Delivered "hs-1")

    // L29 Flag, Queue, HandOff from Nothing is NotArrived.
    apply Flag Nothing Unjudged |> mustErr "L29a" NotArrived
    apply Queue Nothing judgedWarm |> mustErr "L29b" NotArrived
    apply HandOff Nothing judgedHot |> mustErr "L29c" NotArrived
    law 29 "commands-on-nothing" true

    // L30 Queue from HeldForHuman of Warm works (human releases to sequence).
    let s30, _ = apply Queue s4 judgedWarm |> mustOk "L30"
    law 30 "queue-from-held" (dispOf s30 = QueuedForSequence)

    // L31 HandOff from HeldForHuman of Hot works.
    let s31, _ = apply HandOff s4 judgedHot |> mustOk "L31"
    law 31 "handoff-from-held" (dispOf s31 = HandedToCloser && relayOf s31 = Pending)

    // L32 evolve refuses an event that has no arm (Arrived on Open).
    evolve s1 (Arrived birth) |> mustErr "L32" NotArrived
    law 32 "evolve-refuses" true

    // L33 Judgement is an argument, not a field of State. Open has three parts.
    law 33 "state-has-no-judgement" (
        match born () with
        | Open (_, _, _) -> true
        | Nothing -> false)

    // L34 Empty titles is still a valid People Search filter.
    let emptyF = filtersFromIcp [] "anywhere"
    law 34 "search-empty-titles" (emptyF.Titles = [] && emptyF.Locations = [])

    // L35 Geography "anywhere" means no location filter.
    law 35 "search-anywhere" ((filtersFromIcp [ "Founder" ] "anywhere").Locations = [])

    // L36 Persona titles are copied; a named geography is a location.
    let f36 = filtersFromIcp [ "Founder / Owner"; "Head of Growth" ] "Hamburg"
    law 36 "search-titles-geo" (f36.Titles = [ "Founder / Owner"; "Head of Growth" ] && f36.Locations = [ "Hamburg" ])

with ex ->
    failed.Value <- failed.Value + 1
    eprintfn "FAIL exception: %s" ex.Message

let laws = passed.Value + failed.Value
printfn "%d passed, %d failed" passed.Value failed.Value
printfn "LAWS %d" laws
if failed.Value > 0 then exit 1
exit 0
