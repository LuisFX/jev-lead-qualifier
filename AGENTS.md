# AGENTS.md — operating doctrine

> ## 🔐 SECRETS LIVE IN THE ENVIRONMENT — NEVER IN A FILE
>
> A secret is read from the process environment. ⛔ **Never write the value** into a doc, ticket, journal,
> handoff, script, commit message, or memory file.
> ⭐ CHECK before every commit: search the tree for any secret value you handled. The search must print nothing.

**This file is the contract. It is the only doctrine in this repository.** A root `CLAUDE.md`, if it exists, is a
one-line pointer here. Operational notes (ports, commands, paths, deploy) carry no law. If a document contradicts
this file, this file wins.

> Write it as law: **timeless rules, never an arc's history, never one product's inventory.** Dated corrections
> belong in git. A repository's map — what it runs, which gates exist today, which aggregates it owns — lives in
> that repository's architecture doc. A sentence that can only be true of one product does not belong here.

A file also named `AGENTS.md` inside vendored upstream, or inside an archive snapshot, is **evidence, not
doctrine**. Deleting a vendored copy to "clean" it breaks the upstream diff. Archives stay byte-exact.

---

# PART I — THE FRAME

## 🏥 A superset of a system of record stays in sync with it

> ## 🔴 The customer already lives in the system of record. Reach **parity** with it, then add what it lacks.
> ## 🔴 In doubt about what something means or does, **read that system's own code** and compare. ⛔ **Never edit it.**

- ⭐ **Look for alignment on every change**: does the system of record have this act, this word, this relation?
  Then this product says and does the same thing, synced, or names why it differs.
- ⭐ **An act there is a database write, so read what it writes.** Writing only this product's half is split brain.
- 📌 What their code does is written beside ours (docs only), with file:line.

## 🧠🔒 Non-negotiable, applies to every line you write

> ## 🔴 We ALWAYS think **DDD · F# · ELMISH · MODULAR · functional · illegal states unrepresentable**.
> ## 🔴 Whatever you write — TypeScript, Python, F#, a template — you frame it in **F#**, then write the host language to match.

The host language is the **target language**, never the **thinking language**.

| Think this | Then write it as |
|---|---|
| a discriminated union | a discriminated union with a `kind` literal + `assertNever` |
| `Result<'T, Error>` | an explicit success/failure union — **never** `T \| null` + a comment |
| a private constructor / branded id | a branded type with **one** constructor that can fail |
| a total function / exhaustive `match` | every branch returned; a `switch` the compiler proves complete |
| an aggregate invariant | a type that cannot be constructed in violation of it |
| a screen's or widget's state machine (**Elmish**) | `Model` · `Msg` · a pure `update : Msg → Model → Model × Cmd`, **effects returned as data**; ⛔ never `useState` flags + `useEffect` fetches, never a soup of booleans |
| a value that loads (`Deferred`) | `Deferred` (`hasNotStartedYet` · `inProgress` · `resolved`) with `Result<T,E>` inside — ⛔ never a re-invented `loading`/`error`/`data` triple |
| a reply that can arrive late | a sequence number in the `Msg`; `update` drops a stale one |
| a contract with an oracle | an `.fsx` that loads the shipped contract and asserts named laws: it is the SPEC — change it FIRST, then **port** the host language case for case (PART VIII) |

**⚠️ The tell that you slipped out of the frame:** an optional field, a boolean pair, a `?.` chain, a
defensive `if`, a cast. Ask *"what is the F# type here?"* — the answer is almost always a **union you have
not written yet**. ⭐ **Before you name a state, grep for it.** `Deferred`, `Result`, `NonEmpty`,
`assertNever` are the vocabulary. Use the one the repo already has. Do not mint a second name for the same state.

## 🧩 MODULAR — a concept is a SERVICE, shared by construction

> ## 🔴 Organize by **CONCEPT**, never by technical layer. Build every concept as a service ANY host can mount.

The bounded context (DDD) made physical. The question is never *"what does this file touch?"* — it is *"which concept
does it belong to?"* A piece filed next to its neighbour (the board, the shell, the app) is a concept scattered.

- **Shareable by default.** Concept behaviour lives in substrate. A product package holds composition only.
  *Reach UP, never ACROSS* — a product does not import a sibling product. Placement still needs approval (§7, PART IV).
- **Named front doors.** `package.json` `exports` lists each public module by name — core modules at the root, UI
  ones at `./react` or `./react/*`. ⛔ No barrel. ⛔ No deep `src/` import: where a package declares `exports`,
  a deep import is a type error (`moduleResolution: bundler`).
- **F# first:** the dialect is an oracle beside the package (`<pkg>/<concept>.fsx`), built on the shipped contract;
  the host language is ported from it.
- **A pure core:** the dialect, the pure behaviour, the Elmish programs (`Model · Msg · update`), the service functions —
  no UI framework, no host, no app-local alias.
- **PORTS for every host thing, and only those** — few and domain-shaped (*"tell the host what happened"*, *"land
  here"*), never a library handle (a cache-client port drags the host's cache keys in). ⛔ Never a global,
  never a host hook inside the concept. A host that has not configured a required ambient cannot mount a concept
  that needs it.
- **A host is a thin binding file.** A second host is a second binding file — zero copied behaviour.
- **Edges point one way.** Name who may import the concept and whom it may import; a cycle is a boundary drawn wrong.
- **The server mirrors it:** one folder per concept, one module per use case over the ports it already has, thin HTTP.
  ⛔ Not one god-service over every actor.
- **Restructure is `git mv`** (history kept) — ⛔ no re-export shims left behind; every move's old path is a tombstone.
- ⭐ **ENFORCED BY:** per-package import fences, RED-proved (a fence nobody gates is a convention).
  🔴 UNENFORCED until a fence exists: a reviewer's census is the check, and the census says so.

> 📏 **AMENDMENT — THE DESIGN RULER.** Every DDD · MODULAR design is graded against a fixed ruler: yes/no criteria,
> graded at two stages (DESIGN before code · BUILT after), evidence for each, by a fresh grader who never sees an
> earlier score. ⭐ **A score is a count of criteria met — nothing else.** The ruler document, when the repo has one,
> is the list. 🔴 Until it exists, say the grade was a reading, not a gate.

## 🧠🚨 The first thing to doubt is your own framing

The most expensive mistakes are **right code built on a host-language-shaped question** — a result
type with fields a failure never produces; a wire decoded behind `|| undefined`; six spellings of one id.

- 🔴 *Did I think in DDD and F#, or in the host language and translate?*
- 🔴 *Did I **enforce** this invariant, or make its violation **unrepresentable**?* Validation is the consolation prize.
- 🔴 *Am I adding a guard because the **type is wrong**?* A guard is a type asking to be rewritten.

**If you cannot state the F# type, you do not yet understand the problem.**

---

# PART II — 🟢 ONE SHAPE IN CODE · 🔒 EVERY RECORD KEPT

**The architecture is a moving target.** A red test is often the *rot being named*, not a regression.
⚠️ Capture the failing set **before** your first edit. For each red ask: *does this assert a shape we have
discarded?* Yes ⇒ **revise or delete the test** to assert the new direction. No ⇒ it is a real break; fix
the code. ⛔ Never rabbit-hole restoring yesterday's behaviour to green an old assertion.

### CODE: delete, don't deprecate. Git is the backup.

**No shims. No fallbacks. No compatibility layers. No reader that accepts two shapes.** Change it and delete
the old shape — never wire the new thing beside the old. A branch is an experiment; if it goes badly, burn it.

### DATA: records a real party wrote are kept.

> ## 🔴 **Every record we have ever written or synced is KEPT** — it is the audit of what the product did,
> ## and the source of every analytics view.

The code keeps ONE shape; the data is brought to it. When stored records no longer match the code:

| the records are | what you do |
|---|---|
| **reference data** — the only record of a fact (an outbox and its events, intake records, upstream acts, copies and runs, grants, settings, anything sent to or read from a system of record) | **MIGRATE** them to the new shape, or **ARCHIVE** them (`history_<collection>`, stamped `_archive`), never delete |
| **derived data** — rebuildable from a log or a source (a replica, a read model, a search index, a projector checkpoint) | may be **rebuilt** from its source |

- ⭐ **A migration is a managed, one-time, idempotent script** in the arc's `research/tools/`: back up first,
  run it DRY (counts only) and read the counts, then write; a re-run writes nothing. The decoder still reads
  ONE shape — the migration is what makes the data say it. ⛔ A migration is not a shim: the shim PART II bans
  is a *reader* that accepts either spelling.
- ⛔ **Never `deleteMany`, `drop`, or "reset" a collection on a shared or production database** unless it is
  derived data and its source is named. When in doubt it is reference data.
- ⭐ **ENFORCED BY:** a guard that refuses a change which would make a copy stale until the database name is
  typed, then MOVES the history. 🔴 UNENFORCED where no such guard exists: the backup and the dry run are the check.
- A local or throwaway database (a laptop, a scratch box) may still be wiped and re-imported to clear stale
  test data — ⛔ never one that a real party has written to.

### ⭐ Retiring a source means moving EVERYTHING it provided

Enumerate what the old source supplied: the bytes · **freshness** · absence-vs-failure · the rollback
path · **who may WRITE it** · **the IDENTIFIERS it carries** · **its DECLARATION**. A file hands you
freshness for free (an mtime check); an HTTP source does not, so *"cache it"* silently becomes *"cache it
forever"* — a registry once saw a new tenant only after a human restart. A reader deleted while a manifest
still declares it is a change with an expiry date.
⚠️ When two neighbours have opposite operational semantics (one hot-reloads, one needs a restart), the
difference is a finding.

> ⭐⭐ **Before *"how do I move all of it?"*, ask *"who actually runs the other arm?"*** A union arm whose
> every justification is *where something is deployed* is **that deployment's config wearing a type**. Count
> the deployments an arm serves; if it is one, retire the deployment and the problem collapses.
> 🧑 *"The rot was not the file. The rot was the union."*

---

# PART III — 🎓 THE CLASSROOM

This is a **teaching codebase.** The primary reader of every change is a junior engineer learning F#,
the host language, **Event Sourcing**, and the product's domain. **If you opened a file, leave it
clearer than you found it.**

## ⭐⭐ The counterweight

> **A teaching comment is not a mechanism, and the most expensive bug is confusing the two.**

A read-model type once explained its law four times in doc comments and enforced it zero times — so its
principal consumer hydrated bodies on every list for months.
⇒ **A teaching block about a rule names what enforces it.** If nothing does, ⛔ **say so in those words.**
An unenforced rule that admits it is a ticket; one that sounds authoritative is a trap. Explaining the same
rule twice means **write the mechanism instead.**

```ts
// ⭐ ENFORCED BY: `<gate>.test.ts` — a break fails the suite.
// 🔴 UNENFORCED: nothing stops a new caller from doing this. See <ticket>.
```

## What a touched file's comments answer

1. **What problem does this solve** — product *and* technical.
2. **Which idea should a junior notice?** Name it with the real term so it can be searched.
3. **What does this deliberately NOT do?** Boundaries are the most valuable lines.
4. **What enforces the rule this file relies on?**

**Where:** top of file — purpose, mental model, place in the pipeline (write → projector → view → card) ·
exports — params, return shape, side effects, which layer may call it · non-obvious types — why the union
exists and what narrows what · domain rules **by name** · before a tricky block — tenancy, a client/server
boundary, a fold.

## Name the concept so it can be searched

- **Host language** — discriminated unions · type guards · `Record`/`Omit`/`Pick`/`Partial` · generics on
  ports and adapters · why this file is client or server.
- **F#** — unions and records · `option` vs null, `Some 0 ≠ None` · one serialization boundary, named.
- **Event Sourcing** — the **aggregate** (Evans, Vernon) · the **Decider** `decide`/`evolve` (Chassaing) ·
  **CQRS** (Young) · **reference vs derived data** — every view rebuildable from the log alone (Helland) ·
  **projection**, **catch-up**, **backfill**, **eventual consistency**, the **transactional outbox**.
- **Elmish** — `Model` · `Msg` · `update` · `Cmd` · `Deferred` · the URL as the only location.

## Style

- **`TEACHING NOTE` / `TEACHING NOTES`** so the classroom is greppable: `git grep -n "TEACHING NOTE"`.
- `/** … */` on exports; `//` for short hints. ⛔ Never narrate syntax.
- ⛔ Never delete a teaching comment unless replacing it with a better one.
- ⛔ A comment never claims a guarantee the code does not make.
- ⛔ A note says what the code **IS** — never a dated history or changelog. Git holds history.
- ⛔ **Touch a file without a teaching note ⇒ add one. Touch one with a stale note ⇒ revise it.**

## 🛑 Vendored upstream code — the one place the classroom stops

> ## ⛔ **A TEACHING NOTE IN A VENDORED FILE IS A DEFECT.**

Every edit is a permanent diff hunk against upstream (comment 30 files and sync is dead); re-documenting an
upstream decision in our voice launders their choice into ours; and it is unsubmittable upstream.

- ⛔ **ZERO edits to vendored files is the target.** An edit is a failure to find the host-side answer.
- ⭐ **Prefer a HOST-SIDE fix** — a path alias, a wrapper, an **additive** file (new files sync cleanly forever).
- ⭐ If an upstream file genuinely MUST change, write it as a PR upstream would merge: generic, zero product words.
- 📌 **Our reasoning goes BESIDE the code** — `DEVIATIONS.md`, `ARCHITECTURE.md`, the arc's `research/`.
- ⭐ **Vendor what is open-source and upstream-syncable**; use what the library gives before writing your
  own. ⚠️ **A fork is not an upstream** — vendor the ORIGIN.

⭐ **ENFORCED BY:** a byte-identical test on every mirror. 🔴 **A new mirror without a byte gate is the defect.**

## 📐 The reference exemplar

The standard to match is a projector annotated end to end, with a 🔴 `KNOWN ASYMMETRY` block naming a rule
it does not fully enforce; per-field comments that say which law narrows the field; a test that refuses to
be edited into passing (*"a rule you can edit to make a test pass was never a rule"*); a list function whose
type returns a view and cannot return a `Promise`, so per-row hydration is untypeable.

---

# PART IV — THE LAWS

## 1. The contract language owns the types

> **F# OWNS THE TYPES. The host language is the MESSENGER.**

One serializer owns the wire. ⚠️ A serializer that skips null fields by default makes `None` silently vanish —
never auto-encode an opaque payload. The host language imports the contract from the one module that wraps it.
⛔ Never redefine the contract's types in the host language. ⛔ Never mint a second spec model beside the one
the repo has already chosen.

## 2. The four state laws

| | Law | Meaning |
|---|---|---|
| **1** | **Location is derived, never stored** | `parseLocation (toUrl loc) = Located loc`. ONE representation of "where am I": the URL. Navigation emits a command; it never mutates a model |
| **2** | **Every bounce target is itself landable** | `∀b. parseLocation (toUrl b) = Located b`. A redirect that redirects is a loop |
| **3** | **The staleness law** | What **persists** holds **Ids**; what holds **Entities** does not persist |
| **4** | **Illegal states are unrepresentable, not validated** | If a state is illegal, make it **unspeakable** |

**LAW 4 is the one you apply daily.** `{ transcript?: string; words?: Word[] }` with six `if`s is the
disease; `Transcribed of … | Failed of Reason` is the cure.

> ## ⭐⭐ LAW 4'S BLIND SPOT: IT CAN MAKE YOUR **HAPPY PATH** UNREPRESENTABLE, AND THE COMPILER CALLS THAT FINE.

Making an illegal state unspeakable and making the legal state unreachable are **the same mechanism
pointed in opposite directions.** A removal check returned `Removable` only when both bounds were `Some`;
its caller passed a literal `None`, so the endpoint could not succeed for any tenant — while its doc comment
boasted that `Removable` was unreachable. The cure came from the domain: 🧑 **"OWNERSHIP IS NOT A GRANT."**

⭐ The question is never *"is this type tight?"* — it is **"WHICH ARM DOES PRODUCTION ACTUALLY REACH?"**
- An unreachable arm can have several causes; enumerate them and say which you measured.
- ⛔ Never pass `Some []` to make the happy path appear — a half-run check that answers yes is the defect.
- ⭐ **Trace the CALL GRAPH.** `rg 'Module.fn'` cannot see an unqualified same-module call.
- ⭐ **A limit belongs to whoever refuses on it.** A caller may **read** the owner's threshold; ⛔ it never
  **re-decides** it — an upstream copy of the constant pre-empts the downstream refusal while that refusal's
  unit tests (which call the host directly) stay green.

🔴 **UNENFORCED — no general mechanism asks "which arm does production reach?"** A census is a ticket.
⛔ Never write a census count into this file.

## 3. One dialect per identity

> ## One spelling per identity, on every side of a wire. No second spelling.

The taxonomy of tenants, sites, databases, and keys has **one** source. ⛔ No document, comment, or type
restates that language; it points there. ⭐ ENFORCED BY a taxonomy gate, when the repo has one.

We mint no foreign id. For a foreign reference, **provenance is part of the identity** — the foreign system's
own name for its own row, spelled the same in the host language, in JSON, in the URL, and in F#.
**A second spelling is banned**, including a generic `externalId` standing in for a named foreign key.
⭐ ENFORCED BY a spelling gate, zero tolerance, over every file the language walks. A line that names a banned
spelling on purpose (a deny-list, another system's contract) carries a marker the gate counts.
🔴 Until the gate exists, a reviewer's grep is the check, and the review says so.

- ⭐ **A rename that lands on one side of a wire is invisible to review and visible to a grep.** One landed
  on the producer only; the consumer decoded the old name behind `|| undefined`, and records silently lost
  their subject.
- ⭐⭐ **The hazard is the SERIALISATION boundary, not the language boundary.** A JSON key is a string
  literal on the producer and a record field on the consumer; no compiler relates them, even F# to F#.
- ⛔ **A producer-side wire test proves self-consistency, never agreement.** ⭐ ENFORCED BY a wire gate:
  producer vs every consumer, one casing, ≥2 keys per side (**empty sets agree perfectly**).

## 4. Tenancy is ambient, never assignable

`TenantScope` is ambient. **A tenant you can assign is a leak awaiting a typo.**

🔴 **A standing breach to audit:** one credential resolved at boot that serves every tenant, and one tenant
id per environment that makes every API-key caller the same tenant. **Tenant-scoped where data is written,
tenant-blind where money is spent.** The audit is a measurement, dated, of the running process — never a
recollection.

## 5. What a product owns, and what it does not

Write the ownership down in the architecture doc. The laws:

| | |
|---|---|
| **An aggregate we own** | **Event-sourced.** Status is a one-way ratchet; the fold **refuses** rather than skips. A fact for an unknown id is a *lost artifact* |
| **A work item we own** | **One aggregate, every provenance.** How it arrived is its birth, and nothing else differs. It is graded and landed by **the tenant's rules through ONE door**; provenance stops at the door. Staging is transient; ⛔ never the record. What was sent upstream is an append-only outbox. The upstream system's word for the task stays the upstream system's word |
| **An entity we do not own** | **A reference.** No aggregate, no collection as a source of truth; proxied live from the system of record. A search index over it is a rebuildable read model: ⛔ never an aggregate, a source of truth, or read to decide anything |
| **The contract** | **The contract language's, forever.** Never redefined in the host language |

## 6. Data access

- **All DB interaction goes through providers.** All associations use the **external id**, never a storage surrogate.
- **Server mints ids.** No client-side `generateId()`.
- Trace the *whole* path — process → component → hosting → services → db — **even when the cause looks obvious.**

## 7. SHARABILITY BEFORE a local `lib/`

Before creating or updating anything in a per-project `lib/`, ask whether it belongs in substrate.
**Get approval for the placement.** ⭐ A file that depends on nothing is SUBSTRATE; inside a product package
it is in the wrong drawer, and every family that cannot reach it re-invents it.
⛔ Never hand-copy a shared package into an app — a fork keeps the old dialect internally consistent, so
the typechecker stays at 0 while the app speaks the wrong wire.

---

# PART V — HOW WE WORK

## Fail loudly

> **A silenced error is a regression with a green check.**

- No `any`. No `@ts-expect-error`. No silencing casts. Never edit generated code — fix the emitter.
- No `|| undefined` / `?? fallback` at a boundary to make a decode "work". Throw and name the field, entity and id.
- **No bare early-return.** If a function gives up, it says so (two silent `return`s are why a stream never connected).
- ⛔ **No fallback chains for identity.** One source of truth, or an error.
- Prefer narrowing to widening. No drive-by refactors.
- 🔴 A caught exception renamed to something false and returned as success-shaped data is the most
  expensive bug class. If you catch it, carry it.
- ⭐ **A mechanism that only protects code that asked to be protected is a convention** — a schema nobody
  parses, an un-imported server-only marker, a gate that does not walk the app.

## ⛔ Before you delete anything a tool calls "unused"

Things are reached by a path string, a registry, a framework convention, a shell script, or code the tool
ignores. ⭐ **Unused is a fact about references, never a verdict about correctness** — a field flagged unused
was **wrong data** nobody read; deleting it hides the bug. Grep the repo's headstones — what a previous round
already PROVED a tool wrong about — before trusting the tool.

## Evidence, not assertion

> **Measure it. Do not remember it.**

- **Prefer a gate to a test.** **Prove it RED before you trust it GREEN.** A test that cannot fail is
  decoration; one that never executes is worse (a test runner exits **0** on a filter that matches nothing).
- **Run the wall, don't quote it.** Reproduce a failure outside the app; bisect by calling each stage directly.
- ⭐ **Every layer reports success to the layer above it.** Only checks that **boot the artifact** or **count
  what landed on the box** find real things. A count can be right and hide the shape — report the shape.
- ⭐ **A date proves someone looked. Only an exit code proves it RAN.**
- ⭐ **A 401/403 says THIS credential lacks THAT permission on THAT endpoint** — not that the feature is
  absent, and not which problem. Key on `error.code` (`invalid_api_key` = dead key; `Missing scopes: …` =
  valid key, one scope missing), never on the status; provider hint text can be false.
- ⭐ **A credential's verdict is not scalar** — one key can be 200 on a status endpoint and 401 on the
  endpoint the product calls. Ask *"can this key do X?"* and **probe the endpoint the product calls**.

### The three measurement families

| family | what it hands you | the remedy |
|---|---|---|
| **1 · absence** | a **zero** | pair every zero with a known-positive **control** |
| **2 · the wrong question** | a **confident number about a different question** | ask whether the question your tool answers is the one you asked |
| **3 · expiry** | a **true answer about a moment that has passed** | date it; re-run rather than cite |

**Family 2, each a different mechanism:**

| the confident answer | what it actually answered |
|---|---|
| a type-error baseline: *"0 ours"* | classified by **path shape** (`^\.\.`), not ownership — real errors hidden |
| `GET` a status route → 200 | a **status endpoint**; the product's write route was failing — green gate, product down |
| a key's fingerprint | the **file's bytes** (quotes inside the hash), not the value the runtime parses |
| `grep -c "Module.fn"` → 10 | how often the **name** appears — all 10 in `tests/`, zero production callers |
| a compiler → *N* warnings | which projects the **cache recompiled** — three runs, three counts, zero changes |

⭐ None was findable by re-reading one's own work — a **second party measured differently.** ⇒ briefs carry
raw numbers, not conclusions. A **systematic** error cancels in a comparison and survives in a report: ask
which claims rested on the **value** and which on the **equality** before discarding them.

**Family 3:** a credential verdict is a **timestamped observation of a system someone else can edit** —
carry the date in the row; re-run any verdict older than the incident. ⛔ Never let a remedy outlive its
diagnosis. ⚠️ **A nearer failure hides a further one** (permissions are checked before quota): when an answer
changes, assume the old condition is **invisible**, not resolved. ⛔ A note describing a defect names the
command that would retire it. 🔴 A dated row going stale fails nothing until a gate re-probes it.

### ⭐⭐ An absence needs a control

> **A zero is evidence ONLY when the instrument has been shown to see a present thing.** No control, no claim.

| the zero | what it actually meant |
|---|---|
| `find` over a deployed tree → 0 | **permission-denied silence**; a privileged re-run turned 0 into a real count |
| a secrets CLI `--plain` → empty | `--plain` is **empty for a masked secret** (`e3b0c44298…` is sha256 of ""). Verify with what the PROCESS sees (`echo ${#VAR}` under the env loader) |
| `rg -- "$PAT" --glob '!x' .` | **`--` ends option parsing** — the glob became a filename. Flags before the pattern; `-e`, not `--` |
| `sed … $FILES` | **zsh does not word-split an unquoted `$VAR`** — use `set -- a b c` + `"$@"` |
| `rg 'oldName'` after a rename | the old name is a **prefix** of the new one — word-bound it (`-w`) |

⭐ **The tell: the tool's failure mode was indistinguishable from the answer.** A subset that out-counts its
superset is a broken tool; a probe whose bogus input answers like its real one proved nothing. ⭐ A spelling
census is not a hazard census — the hazard is a **case-sensitive lookup on the path**. 🔴 **Writing this
rule down is not obeying it:** if you wrote down why your evidence is weak, you may not conclude from it.

**Truncation looks identical and has the opposite cure.** If the search visited the file and *you* did
not read the line, widening scope changes nothing. ⛔ Never pipe an evidence listing through `head`/`tail`
when the count is the claim; ⭐ reconcile the COUNT against the LISTING; ⭐ grep the EXACT string you claim
about. ⭐ Two credentials can share a fingerprint and need opposite actions — ask *"if I delete this value
now, what breaks?"*; **you cannot rotate your way out of a credential the build inlines.**

### ⛔ `Authorization` is not a free header

An auth provider that reads `Authorization` as a session token **wins over the cookie** — a dummy SDK key
signs the caller OUT. A proxy in front of that provider deletes `authorization` on the way through; the fix
adds no auth. ⛔ On a protected route **a 404 may mean unauthenticated** — read the auth reason header.
⭐ A route lacking the method returns **405**, the control. 🔴 UNENFORCED: nothing stops the next proxy
re-introducing the header.

## Be skeptical — especially of yourself

- **Verify against the running system** — owner, slug, provider, identity, env. Never hardcode a guess.
- **Red-team before calling anything "done".** Do not take another agent's (or a past note's) result at face value.
- ⛔ Production is not a baseline: *"it ran in prod"* justifies nothing.
- **Correct plainly and move on.** No self-flagellation.

## 🤝 Working alongside another agent on the same running system

> ## ⛔ ZERO env/config changes without a brief to the agent running the stack. Not permission — NOTICE.

Tell them **that a value changed**, **which processes must restart** (⭐ an env loader resolves at process
start — fingerprint the **running pid**, never the config), and **what you expect to change** so they can
report that it didn't. ⭐ Brief in both directions — one agent often holds the config half, the other the
process half. ⛔ Never send a hypothesis dressed as a measurement; mark retractions loudly.

## Follow the plan

**FOLLOW YOUR DIRECTIONS TO A "T".** When work is staged, **stop after every stage for review.** Scaling
scope down is the user's call; if blocked, finish everything else and say exactly what you left and why.

## Commits and the shared tree

- ⚠️ **A concurrent session commits here in parallel.** Stage with **explicit pathspecs**, never `git add -A`.
  **The user says when** to commit.
- 🔴 **`git add <paths>` scopes the ADD, not the COMMIT** — a bare `git commit` takes the whole shared index,
  another session's staged work included. Options first, then `--`, then paths, and read the index **in the
  same command** (an index reading from a prior command has expired):
  ```bash
  git diff --cached --name-only && git add -- <paths> && git commit -m "…" -- <paths>
  ```
  If a path you did not touch is listed, stop.
- ⭐ *"Did my edit land?"* → `git diff HEAD -- <path>` or read the file. Plain `git diff` omits staged changes.
- ⛔ **No `git stash`** — the stack is shared across worktrees.
- ⛔ **Never push directly to the integration branch**; open a PR even for a fast-forward.
- Green types + relevant tests before each commit. ⛔ Never commit a lock of generated version metadata, or any key.

---

# PART VI — 🔮 OBSIDIAN-DRIVEN PLANS

> ⭐ **THE GOLD STANDARD:** an arc follows [`PLANS_DOCUMENTED_DOCTRINE.md`](PLANS_DOCUMENTED_DOCTRINE.md).
> Engineering docs follow their own doctrine when the repo has one. This file does not restate it.

`plans.documented/` is an Obsidian vault: frontmatter makes a doc addressable, `[[wikilinks]]` make the arc
navigable. **An arc is a folder**, `plans.documented/YYYY-MM-DD-slug/`:

```
HANDOFF-MEMORY.md      read_order 1 — the hub. Where a cold agent starts.
research/              anything worth keeping. One question per file.
tickets/INDEX.md       the board. Earned, not speculated.
journals/              evidence, written every iteration.
```

**Frontmatter is mandatory:**

```yaml
---
title: …            slug: …            aliases: [short-name]
date: YYYY-MM-DD    type: research|handoff|ticket|ticket-index|runbook|ssot
arc: <folder slug>  status: live|open|ssot   read_order: <n>
tags: [...]
---
```

When the estate and this enum disagree at scale, the enum is what is wrong.

## Links

- ⛔ **A wikilink resolves by PATH or BASENAME, never by an alias.** Link by basename and carry the
  readable name in the pipe: `[[YYYY-MM-DD-slug|SHORT-NAME]]`.
- ⭐ **A 0-byte `.md` is Obsidian's record that someone followed a dead link** — a failure.
- ⛔ Never wikilink OUT of the vault — use a relative markdown link. ⚠️ Backtick every route path:
  `/a/[slug]/[[...rest]]` is a wikilink.
- Every doc links **back to the hub** and **across to its siblings** — ⛔ no sinks, no orphans. **Link, don't repeat.**
- ⭐ **ENFORCED BY** an arc-link gate (resolves what a click follows, flags stubs and ambiguous basenames).
  **Add every new arc to its roster**; RED-prove with `[[no-such-doc]]` → exit 1.
  🔴 Until the gate exists, the reviewer's click is the check.

## How an arc is researched, picked and organized

1. **RESEARCH FIRST, and write it down** in `research/`, never a chat transcript. ⭐ **Every sub-agent or
   scout sent to research returns a file**: `<arc>/research/{YYYY-MM-DD}-{concept}.md`. **No file, no research.**
2. **Every finding is falsifiable** — a `file:line`, a command, a fingerprint, a status. Say what is **NOT known**.
3. **Tickets are earned** — a ticket names the moment it cost us.
4. **Every `⇒` in a postmortem gets a ticket.**
5. **Name the acceptance test up front** (*the scout test*: every question a context-free agent must ask a
   human is a bug in the docs).
6. **LATEST WINS.** Read `plans.documented/*` latest → oldest; an older ruling never binds against a newer one.
7. **Journal every iteration** — why · what finished · what now · what next. ⭐ **A doc is grepped as
   fact, not read as history:** a line recording a **COST** stays; a superseded **DECISION** is corrected in
   place; a retired doc is **deleted** and its inbound links repointed. Git is the safety valve.
8. **Memory is a POINTER** — the read-first path and the rulings that would otherwise be re-litigated.
9. **Location is not authority.** A finished arc moves to its permanent home — ⛔ so nothing executable
   (an oracle, a gate input) lives in a dated arc folder.

## 🗓️ Demo agendas — what we share with the people in the room

> **An arc's runbook is for engineers. A demo agenda is for the meeting:** the buyer, the operator, the
> vendor. Same facts, the audience's words. ⛔ Never hand a meeting the runbook.

**How it is made:** a self-contained HTML page. It renders in either theme, phone or laptop.
⭐ The page's source is kept in the arc (`research/{date}-{concept}-agenda.html`), and the runbook links to the
published URL. Update the page by republishing to the **same URL**, never as a second page.

**What it holds, in this order:**
1. **What works today**, in four lines the audience would say. Name what is switched OFF.
2. **The agenda**: time boxes, demo first, decisions last.
3. **Each step as a pair, "In our product" | "Check in the system you already trust".** Every write step
   carries a **tag**: *Can be put back* · *Mostly put back* · *Stays* · *Cannot be undone*.
4. **Safest first**: reversible steps before irreversible ones. Every step targets a **test record made in the
   room**, never a real party's record.
5. **Ground rules**: what we never touch, the stop rule (anything unexpected → switch it off, stop, put it back), and
   the state we leave behind.
6. **Questions for the audience**, and **note boxes** to fill in during the meeting.

**The words:** ⛔ no jargon. No outbox, wire, POST, replica, sync, dry run, or ticket numbers. Name things by
what the audience sees on the screen. ⭐ The product's screens use the agenda's words, so the room and the UI match.

🔴 UNENFORCED: no gate checks an agenda's words; the owner's read is the check.

---

# PART VII — 🤝 DELEGATING TO A CURSOR CLI AGENT

**Method:** the executor-strategy manifesto — **REVIEWER** holds context and trusts nothing · **EXECUTOR**
runs one ticket with a licence to STOP · **USER** is courier and authority. Tool notes, when the repo has
them, live in `docs/cursor/`.

| | |
|---|---|
| **One chat id per arc** | `agent create-chat`; reuse and **record** it (`agent ls` is an interactive picker) |
| **Task 1 is read-only** | `--mode ask` / `--mode plan` |
| **Anything that writes gets `-w`** | its own git worktree, outside the repo |
| **`--trust`, never `--yolo`** | `--trust` grants directory access; `--yolo` grants blanket command approval |
| **Launch in the background** | not `tmux`, not `&` — **process exit is the completion signal** |
| **The ticket carries the decisions** | ⛔ never hand an executor a choice — decide, then hand a ruling |
| **STOP-AND-REPORT is success** | *"STOP AND REPORT beats a clever guess, every time."* |
| **Gates carry EXACT numbers** | pre-measured before touching anything; a mismatch is a STOP |

**Done = three layers:** it **exited** (harness notice) · it **thinks** it succeeded (a required sentinel
line) · it **actually did** (**you read the artifacts and re-run every gate**). ⛔ Never file-watch an output
file for completion — half-written and finished look the same, and a crashed agent never writes.

- ⛔ **Permission boundaries do not transfer** — never delegate because a prompt was declined in your session.
- ⛔ **The delegate holds neither the commit pen nor the ticket pen** — it reports *beside* the ticket.
- ⛔ Helpers never commit, restart the stack, deploy, or smoke — and they **test what they build, nothing else**
  (PART IX, TESTING). Every brief says so.
- ⚠️ A fresh worktree has no build state: installed dependencies and compiler output do not follow. Run under
  the repo's env loader.

---

# PART VIII — ORACLES, THE EXECUTABLE ARCHITECTURE

> **An oracle is executable F# asserting named laws. It IS the spec.** `dotnet fsi <oracle>.fsx` → `N passed, 0 failed`.

**One direction:** when the host language and the `.fsx` disagree, change the `.fsx` FIRST, run it, then touch
code. The host language is **ported** from the oracle, never re-derived from memory.

⭐ **ENFORCED BY the oracle gate** (`bun run check:oracles` when the repo wires it): it executes every oracle
in its `ORACLES` roster, asserts `0 failed` and a **per-oracle law floor**; `EXPECTED` pins the roster size.
- ⛔ **The floor is the law count — never write one in prose.** A number in prose drifts; a floor does not.
- ⛔ **Adding an oracle touches `ORACLES` and `EXPECTED` in one commit.** Deleting laws lowers the floor in
  the deleting commit, with the reason. ⭐ **An ungated oracle is the defect.**
- ⛔ **An oracle lives beside its code, never in a dated arc folder.** A `git mv` rewrites paths *to* a file,
  never paths *inside* it — a `#load`, `#r`, `--project` or `source` breaks silently.
- ⭐ An oracle that loads nothing cannot break that way; a long load list means the domain/design split is
  wrong. The gate budgets every oracle's `#load`s (a third column in its roster; a one-line `#load "a" "b"` counts
  two) — raise one deliberately, in the commit that adds the load.

The roster in the gate is authoritative. ⛔ A prose table of every oracle drifts; do not keep one in this file.
🔴 Until the gate exists, an oracle that nothing executes is a document, and the review says so.

### The shape of a repository

```
<repo>/
├── apps/          thin hosts — composition and bindings only
├── packages/      concepts — substrate reached UP to, never across
├── plans.documented/   arcs (PART VI)
└── infra/         deploy, idempotent, re-runnable
```

- ⛔ No package imports the app. ⭐ **ENFORCED BY** a layer-DAG test — ⛔ never widen an allow-list to green
  the suite; only a documented restructure moves an edge.
- Inter-package dependencies use the workspace protocol, never a pinned version of a sibling.
- **The layer DAG is the law, not the folder roster.** ⛔ Do not keep a DAG of deleted folders.
- A host composes its mount path from `basePath`. ⭐ A purity gate fails an app that reaches into a sibling
  product or a deep app-local alias for behaviour that belongs in substrate.

The map of *this* repository — ports, processes, which concepts exist — lives in its architecture doc.

---

# PART IX — COMMANDS & GATES

Use the repo's runner. For JavaScript, **`bun`** — never npm, yarn, or pnpm. For Python, the repo's runner —
never a second environment. ⚠️ Script names differ per package — check before you type.

```bash
# F# — THE PROJECT PATH IS REQUIRED (a bare `dotnet build` with no project fails).
dotnet build <project>.fsproj
# ⛔ NEVER QUOTE A WARNING COUNT — it measures the build cache, not the code. Record the SHAPE:
dotnet build <project>.fsproj --no-incremental 2>&1 | grep -oE "warning FS[0-9]+" | sort | uniq -c | sort -rn
# 🔴 FS0025 = incomplete pattern match, a case nobody handled. UNENFORCED until a warning fails the build.

# The root gate. `--continue` so every workspace reports.
# Name the scripts this repo actually has — a script that does not exist is not a gate.
```

## 🧪 TESTING — who runs what, and the switches that make a run real

> ## 🔴 A test that needs a database, a vendor, or money SKIPS by name until a variable wakes it —
> ## and the run still prints success. **Read the skipped list and report it by name.** A skipped test proved nothing.

Switches are **names**. Values come from the env loader or the local stack, ⛔ never from a committed file.
🔴 UNENFORCED until something fails a run whose switches were unset. The skipped list is the check.

**Who runs what — the test economy.** The deliverable is closed tickets, not green walls.

- **While building** (lead or helper): only what covers the change — the ONE oracle touched (`dotnet fsi <it>.fsx`, never
  the full oracle gate), the ONE test list, the ONE package's test file. RED-prove only the new law, with the same filter.
  A gate runs only when its own input changed.
- ⛔ **A helper tests what it built and NOTHING else.** No full suite, no oracle wall, no gate wall, no "to be sure"
  re-run. It reports command · exit · the summary lines; that record is the evidence and the lead does not re-run it.
  Every check has ONE owner — never the helper and the lead both.
- **A commit** = the build of what changed + its one oracle or test list. A docs-only commit runs no test.
- **The full wall** (oracles, the suites the change touches, the gates): ONCE, by the lead, before the PR.
  When reporting green, name the suites.
- ⚠️ **A filter that matches nothing passes:** the runner exits 0 and prints success. An empty filter can run the
  WHOLE suite. Read the count before you claim a test ran.

---

# PART X — INFRA, SECRETS, DEPLOY

> **THE INFRA IS 100% IDEMPOTENT.** Every change goes through a re-runnable script.
> ⛔ **Never fix things directly on a deployed environment.**

- **The secret store the repo names is the SSoT.** ⛔ Never commit a key; if one leaks, say so and name the
  config to rotate. A local env file, when the repo allows one, is gitignored, is not the source of truth,
  and is never committed.
- ⭐ A populate script **asserts** secrets are present and fails loud — it never writes a secret value.
  A populate that pushed a laptop's secrets once replaced a working key with a revoked one in every config.
- ⭐ **After any deploy, re-fingerprint the secret you changed.** Fingerprint the **running process**, not the file.
- ⭐ **Rotating a key** is a script: probe the key the running process holds, swap, restart, verify the process
  holds the new value, and only then revoke the old one. ⛔ Brief any agent on the stack first. Restarting a
  process does not re-read a store the box does not hold.
- ⛔ Nothing reaches a shared or production environment until smoked on the local stack, and deploys happen
  only on the owner's word.
- **Sensitive records:** fictional or de-identified fixtures only.

## 🔥 THE COMMANDMENTS — team DNA

The team's manifestos sit outside any one repository (`/Users/luisfx/code/MANIFESTOS/`) and are **not**
superseded by this file: the observability commandments · the telemetry manifesto · the executor-strategy
manifesto. A manifesto that governs one product's domain binds that product; this file does not restate it.

⛔ **Telemetry must never take you down.** Emit non-blocking, never `await` telemetry on a request path,
bound the payload, degrade to local logging. **A `catch` that reports must not itself be able to throw.**

---

# PART XI — THE BAR FOR "DONE"

All of it, every time. Any one alone proves very little.

```
the oracle gate                         0 failed     (every oracle on the roster, executed)
the typecheck                           0 errors
the gate wall                           green
the test runner                         green — and running the suites it names
a human loaded the page                 the smoke is not optional
```

> **A green build proves imports resolve. It does not prove the app works.**
> A defect once passed every automated check for weeks.
