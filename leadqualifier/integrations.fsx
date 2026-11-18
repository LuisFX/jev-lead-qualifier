(**
  Integrations — catalog, mounts, compose.

  Queue / HandOff still authorize. Another app still sends. The operator
  mounts a PluginId onto a Channel slot. Unmounted is Fake. Mounted is a
  plugin that declares Send of that channel. Two plugins on one slot is
  unspeakable (one Mount per Channel). A plugin that only sends Email
  cannot occupy Voice.

  This file loads nothing. Channel is the same five arms as workitem.fsx;
  that file exits, so this one does not #load it. A rename of an arm must
  touch both. 🔴 UNENFORCED until a shared contract file exists.

  Open stays four parts (arrival, disposition, Relay, Outbound). Catalog
  is not stored on Open. This oracle does not re-state that law.

  ⛔ Vendor words do not appear in this file. A plugin id is an opaque label.

  ⭐ ENFORCED BY: this file. `dotnet fsi leadqualifier/integrations.fsx`
  → N passed, 0 failed. Host port: `leadqualifier/integrations.py`.
*)

open System

// --------------------------------------------------------------------------- contract

type Channel =
    | Email
    | LinkedIn
    | Voice
    | Sms
    | RinglessVoicemail

type Direction = Out

type Capability = Send of Channel

type PluginId = PluginId of string

type Catalog = Map<PluginId, Set<Capability>>

type Mount =
    | Unmounted
    | Mounted of PluginId

type Mounts = Map<Channel, Mount>

type ComposeError =
    | UnknownPlugin
    | CapabilityMismatch

let allChannels = [ Email; LinkedIn; Voice; Sms; RinglessVoicemail ]

let mountOf (mounts: Mounts) ch =
    match Map.tryFind ch mounts with
    | Some m -> m
    | None -> Unmounted

let compose (catalog: Catalog) (mounts: Mounts) : Result<Map<Channel, string>, ComposeError> =
    let rec go acc remaining =
        match remaining with
        | [] -> Ok acc
        | ch :: rest ->
            match mountOf mounts ch with
            | Unmounted -> go (Map.add ch "fake" acc) rest
            | Mounted pid ->
                match Map.tryFind pid catalog with
                | None -> Error UnknownPlugin
                | Some caps when Set.contains (Send ch) caps ->
                    let (PluginId label) = pid
                    go (Map.add ch label acc) rest
                | Some _ -> Error CapabilityMismatch

    go Map.empty allChannels

let candidates (catalog: Catalog) (ch: Channel) : PluginId list =
    catalog
    |> Map.toList
    |> List.choose (fun (pid, caps) -> if Set.contains (Send ch) caps then Some pid else None)

let emailPlugin = PluginId "email-plugin"

let catalog: Catalog =
    Map.ofList [ emailPlugin, set [ Send Email ] ]

let emptyMounts: Mounts = Map.empty

// --------------------------------------------------------------------------- laws

let passed = ref 0
let failed = ref 0

let law (n: int) (name: string) (ok: bool) =
    if ok then
        passed.Value <- passed.Value + 1
    else
        failed.Value <- failed.Value + 1
        eprintfn "FAIL L%d %s" n name

let mustOk name (r: Result<'a, ComposeError>) =
    match r with
    | Ok x -> x
    | Error e -> failwithf "%s: expected Ok, got Error %A" name e

let mustErr name expected (r: Result<'a, ComposeError>) =
    match r with
    | Error e when e = expected -> ()
    | Error e -> failwithf "%s: expected %A, got %A" name expected e
    | Ok _ -> failwithf "%s: expected Error %A, got Ok" name expected

try
    // L1 empty mounts compose to Fake on all five channels.
    let b1 = compose catalog emptyMounts |> mustOk "L1"
    law
        1
        "empty-mounts-all-fake"
        (List.forall (fun ch -> Map.find ch b1 = "fake") allChannels
         && b1.Count = 5)

    // L2 mount email-plugin on Email leaves Voice Fake.
    let emailMounted = Map.ofList [ Email, Mounted emailPlugin ]
    let b2 = compose catalog emailMounted |> mustOk "L2"
    law
        2
        "email-plugin-on-email-voice-fake"
        (Map.find Email b2 = "email-plugin" && Map.find Voice b2 = "fake")

    // L3 mount email-plugin on Voice is CapabilityMismatch.
    // RED: drop `when Set.contains (Send ch) caps` in compose and this fails.
    compose catalog (Map.ofList [ Voice, Mounted emailPlugin ])
    |> mustErr "L3" CapabilityMismatch
    law 3 "email-plugin-on-voice-mismatch" true

    // L4 unknown PluginId is UnknownPlugin.
    compose catalog (Map.ofList [ Email, Mounted(PluginId "no-such") ])
    |> mustErr "L4" UnknownPlugin
    law 4 "unknown-plugin" true

    // L5 unmount Email after a swap returns Email to Fake; Voice unchanged.
    let b5a = compose catalog emailMounted |> mustOk "L5a"
    let b5b = compose catalog (Map.add Email Unmounted emailMounted) |> mustOk "L5b"
    law
        5
        "unmount-email-returns-fake"
        (Map.find Email b5a = "email-plugin"
         && Map.find Email b5b = "fake"
         && Map.find Voice b5a = "fake"
         && Map.find Voice b5b = "fake")

    // L6 two catalog entries: Email plugin cannot appear in Voice candidates.
    let other = PluginId "other-plugin"
    let two: Catalog =
        Map.ofList
            [ emailPlugin, set [ Send Email ]
              other, set [ Send LinkedIn ] ]
    law
        6
        "voice-candidates-empty"
        (candidates catalog Voice = []
         && candidates catalog Email = [ emailPlugin ]
         && candidates two Voice = []
         && not (List.contains emailPlugin (candidates two Voice)))

with ex ->
    failed.Value <- failed.Value + 1
    eprintfn "FAIL exception: %s" ex.Message

let laws = passed.Value + failed.Value
printfn "%d passed, %d failed" passed.Value failed.Value
printfn "LAWS %d" laws
if failed.Value > 0 then exit 1
exit 0
