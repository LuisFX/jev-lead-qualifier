---
title: "plans.documented doctrine — how an arc is researched, designed, built and handed off (the gold standard)"
slug: plans-documented-doctrine
date: 2026-10-09
updated: 2026-11-17
type: ssot
status: live
related:
  - AGENTS.md
tags: [doctrine, arcs, ddd, fsharp, elmish, oracles, tickets, handoff]
---

# plans.documented doctrine — the gold standard

> Owner ruling, 2026-10-09: *"This arc has been amazing to work with — we want to make this our actual gold standard."*
> This file describes that shape so the next arc starts there. It complements — never restates — the root
> `AGENTS.md` (PART I the frame, PART IV the laws, PART V evidence, PART VI Obsidian-driven plans). Where they
> disagree, `AGENTS.md` wins and this file is corrected. Engineering docs (`docs/engineering/…`) follow their own
> doctrine when the repo has one; this file does not restate it.

This doctrine is app-agnostic. It names how an arc is built. It does not name one product's aggregates, one
system of record, or folders that live in another repository.

## TL;DR

An arc is a folder that **thinks in DDD and F# first**: research measures the real system and writes it down; a
**VERSIONED ARCHITECTURE-AT-A-GLANCE** (`_v{n}_{concept}`, each written from scratch, grounded in measurements) shows the
target on one page and the owner confirms a version; only then the full
**ARCHITECTURE** states the domain as **types and an executable oracle** before any code; waves are **cut into tickets
only after the design is rated**; every wave ends **green and smoked on the local stack, then one commit**; a
**HANDOFF-MEMORY** hub lets a cold agent resume in one read; journals record each iteration; the **board** is always
current. Nothing in the arc is asserted that was not measured, and nothing is built that the oracle did not admit first.

## 1 · The ethos — DDD · F# · Elmish (the part that matters most)

1. **The domain is a type before it is a screen.** Every concept is written as an F# union or record in the shared
   contract — e.g. `Related = Nothing | KnownRecord | OtherRecord`,
   `RecordLink = Filled | Named | Unmatched`, `Writes = WritesNotMeasured | WritesMeasured of WriteGrants * at`.
   An optional field, a boolean pair or a `?.` chain in the design is a **union not yet written** (AGENTS.md PART I).
2. **Illegal states are unrepresentable; the legal one must be REACHABLE.** Ask *"which arm does production reach?"* of
   every union (AGENTS.md PART IV.2). An unmeasured tenant admits no write (`Blocked WriteNotMeasured`) — never a default.
3. **The aggregate refuses.** A state machine is a **Decider** (`decide` / `evolve`, Chassaing) whose `apply` REFUSES an
   illegal event with a name — never skips it. The model is a closed set of cases with a full transition matrix in the
   oracle: Held · Ready · InFlight · OutcomeUnknown · Delivered · Blocked(reason) · Failed · Cancelled · Overtaken.
4. **CQRS and the outbox, named by their canon.** What a screen shows is a **read model** rebuilt from the source of truth
   (the system of record's rows, read back by a projector); a write is a **transactional outbox** item, delivered by a relay,
   idempotent on a key. Cite the pattern by name in teaching notes; flag a deviation while in flight.
5. **Elmish on the client.** The page holds **ids, never entities** (LAW 3); the URL is the only location (LAW 1); a
   screen's mode is a union (`view | edit | complete | remove | withdraw`); a load is `Deferred`, never `(loading, data,
   error)`; a lookup returns a union (`Name = named | resolving | notAvailable | notAsked`).
6. **Who owns what is written down** (bounded contexts): what this product owns, what it only READS, and the one door
   through which each concept is written. Provenance stops at the door (AGENTS.md PART IV.5).
7. **Measured, never declared.** A fact the database can answer is measured, never typed in by a person and never defaulted.
8. ⭐ **STATE IS ALWAYS DRAWN AS A DDD · ELMISH · F# MERMAID STATE DIAGRAM** (owner, 2026-10-09). Any time, anywhere a
   diagram shows STATE — an aggregate and its Decider, a contract's union, an oracle's laws, a read model, app state
   (an Elmish page, its `Mode`, its `Deferred`) — it is a Mermaid `stateDiagram-v2` in the domain's own terms.
   ⚖️ **AMENDED the same day by the owner: "only state" is too strict.** Other diagrams stay valid where they fit
   better — a `sequenceDiagram` for WHO CALLS WHOM across processes, a flowchart for a build or deploy pipeline. A doc
   may carry both. ⛔ What is never valid: state drawn as boxes and arrows that are not union cases and named events.
   ⚠️ **Before drawing, re-read** `AGENTS.md` **§ PART I — THE FRAME** (*"DDD · F# · functional ·
   illegal states unrepresentable"*) and **§ PART IV.2 — The four state laws** (Elmish: the URL is the location, ids not
   entities, illegal states unspeakable). Then:
   - **A state is a union case, spelled as the code spells it** (`Blocked`, `RecordLink.Named`);
     **an arrow is a named event** of the Decider (`Released`, `Committed`, `FoundByKey`) or a measured fact — never a verb
     someone made up for the picture.
   - **Draw from the code, not from memory**: read the `apply` / `decide` match and draw EVERY arm it admits — including
     the ones that loop (`Amended`), refuse (a `note` naming the refusal) or end in "nothing" (`None`). ⛔ An arm the code
     admits and the diagram omits is a wrong diagram, not a simplified one.
   - **Group by owner** (`state "…" as X { }`): the aggregate, the read model (the system of record's row), the contract's
     union, the Elmish page.
   - **Render it before committing — on the OLDEST parser that will read it**: `bunx @mermaid-js/mermaid-cli@10.2.4 -i x.mmd
     -o x.png` (the version the owner's viewer runs) as well as a current one, and look at it. A broken diagram throws;
     ⚠️ ONE `:` per line — the first splits a state from its description (or an arrow from its label), and 10.2.x refuses a
     second (measured 2026-10-09: 11.4.2 and 10.9.1 rendered a label with a second colon, the owner's viewer did not);
     ⚠️ `\n` in a transition label prints literally — use `<br/>`; two self-loops on one state collapse into one.
   - 🔴 UNENFORCED: no gate checks a diagram against its code. Diagrams have passed review and still been wrong (a missing
     `None`, an arm the match admits and the picture skips) — found only by reading the match arms. ⇒ the code is read at
     the moment of drawing, every time.

## 1b · Frontmatter — the arc's spine (it is how every doc is FOUND)

> A doc is not read as history; it is **grepped and graphed**. Frontmatter is what makes it addressable (Obsidian), what
> lets a cold agent know what exists without opening it, and what ties the arc to the docs it produced. ⛔ A doc without
> frontmatter is a defect, not a draft.

**Every arc doc** (hub, ARCHITECTURE, research, journal, ticket, board) carries the base schema from AGENTS.md PART VI:
`title · slug · aliases · date · type · arc · status · read_order · tags` — and the **hub** additionally carries the
arc's FLAGS and BACKLINKS:

```yaml
---
title: "…"
slug: handoff-memory
type: handoff
arc: YYYY-MM-DD-slug
status: live
read_order: 1
branch: { <repo>: <branch> }
# FLAGS — facts, never wishes; flip them in the commit that makes them true
architecture_settled: true          # the design is rated ≥ 9/10 (the review ledger)
tickets_cut: true                   # the board exists and holds cut tickets
has_user_stories: true              # docs/engineering/user-stories/<set>/ exists for this arc
has_upstream_docs: true             # the system of record's engineering docs exist for this arc
has_known_issues: true              # the user story set has a KNOWN_ISSUES.md
deployed: false                     # ✈ — only on the owner's word
# BACKLINKS — repo-qualified, every doc the arc produced outside plans.documented/
user_stories:
  - <repo>:docs/engineering/user-stories/<set>/README.md
engineering_docs:
  - <repo>:docs/engineering/<area>/README.md
upstream_docs:
  - <upstream-repo>:docs/engineering/YYYY-MM-DD-concept.md
upstream_use_cases:
  - <upstream-repo>:docs/engineering/use-cases/<case>/README.md
---
```

**A ticket** carries `type: ticket`, `arc`, `status`, its `wave`, `depends_on`, and — once the work is written up — the
same backlinks for the docs that describe it. **A research doc** names the `tickets` it earned and the engineering doc
it fed (`feeds:`), so a finding can be traced to where it became law.

## 1c · The relationship — arc ⇄ user stories ⇄ upstream use cases

```
plans.documented/<arc>/                         HOW it was decided and built (research · architecture · tickets · journals)
        │  hub frontmatter: user_stories · engineering_docs · upstream_docs · upstream_use_cases
        ▼
docs/engineering/user-stories/<set>/            WHAT it does today (stories · KNOWN_ISSUES · CALL-SITES)
        │  frontmatter: arc · tickets · ticket_board · related (every doc in the set)
        ├──▶ docs/engineering/<area>/           how each layer of this product does it
        └──▶ <upstream-repo>:docs/engineering/  how the system of record does it, when this arc touches one
                 └──▶ use-cases/<case>/         ONE concrete case, table by table
```

- **The arc is the WHY and the HOW-WE-GOT-HERE; the user story is the WHAT-IT-DOES-TODAY.** The arc may be archived when
  it closes; the user story stays live and is corrected as the code moves.
- **Every link is two-way.** The hub lists the story set and the upstream use cases; each of those lists the arc
  (`arc:`), its tickets (`tickets:` + `ticket_board:`) and every sibling (`related:`). `KNOWN_ISSUES.md` rows name their
  tickets; the tickets point back at the story set.
- **The flags make the graph queryable**: `grep -l "has_upstream_docs: true" plans.documented/*/HANDOFF-MEMORY.md`
  answers *"which arcs touched the system of record directly?"* without opening a file.
- A flag for a doc kind this arc did not produce stays absent. A `false` that means "not this arc's job" is a wish
  wearing a fact. Flip a flag in the commit that makes it true.

## 2 · The folder

```
YYYY-MM-DD-slug/
  HANDOFF-MEMORY.md         read_order 1 — the hub: TL;DR, RESUME HERE, the owner's rulings, what is owed
  ARCHITECTURE-AT-A-GLANCE_v{n}_{concept}.md   ALWAYS FIRST, VERSIONED — the target on one page (§4); a new direction
                            is a new file written from scratch; earlier versions stay, marked superseded
  POST-MORTEM.md            what the build surfaced OUTSIDE the arc's tickets: dated rows, owner-ruled before acted on
  TOMBSTONES.md             MANDATORY when the arc retires anything: every burial, where it lived, what replaces it,
                            ⚰️ planned → 🪦 buried <commit> (0 references, measured with a control). 🧑 2026-10-10:
                            "THE BEST ARCS RETIRE AS MUCH AS ADD… RETIRE THE OLD MACHINERY IN FULL, DON'T SHIM IT"
  ARCHITECTURE.md           the design: rules, bounded contexts, THE state diagram (§1.8), the contract files, the oracles,
                            the journeys, the waves, decisions, patterns, the review ledger, as-built deviations
  ARCHITECTURE-*-DIAGRAM.md a user story's diagrams: its STATES (§1.8), plus a sequence when the hops matter (optional)
  research/                 one question per file: {date}-{concept}.md — falsifiable findings, "What is NOT known"
  research/tools/           every tool a finding cites: {date}-{concept}.{fsx,sh,py,sql,ts} (ts is bun-driven) — not limited to these
  research/{date}-{ticket}-smoke/       the SCREENSHOTS a smoke produced
  research/<date>-baseline-shots/<wave>/   the same, grouped by wave when one smoke spans a wave
  research/archive/         superseded rounds (kept as evidence, linked from the review ledger)
  journals/{date}-journal.md   every iteration: why · just finished · now · next · re-read the plan
  tickets/INDEX.md          the board
  tickets/{date}-ts-NNN-{slug}.md   one ticket each
```

⛔ **No sub-arcs** (owner, 2026-10-09: *"I had created some arcs with sub-arcs… that's not working out"*). An arc never holds
another arc. A new concern is its own top-level `YYYY-MM-DD-slug` arc beside its parent, linked both ways by relative
markdown links (a wikilink cannot leave its vault).

## 3 · research/ and research/tools/

- **Research first, written down** — never left in a chat. One question per file, Obsidian frontmatter, wikilinks to the
  hub and siblings, every finding falsifiable (`file:line`, a command, a count **with its date and database**), and a
  closing **What is NOT known**. A helper agent sent to research comes back **with a file**, not a reply.
- **Measure the real system.** A system of record is read **SELECT-only**, through one wrapper (`research/tools/sql.sh`)
  that never prints a credential; every query that produced a cited number is saved in `research/tools/` and named in
  the finding.
- **Every zero has a control** (a positive case beside it); every refusal has its positive twin.
- **Research tools are files, never a chat transcript**: `.fsx` (F# — an oracle-style probe that loads the shipped
  contract), `.sh` (a wrapper, e.g. `sql.sh`), `.py`, `.sql` (SELECT-only), `.ts` (bun-driven: an API probe, a browser
  smoke) — and not limited to these. Each is named `{date}-{concept}.{ext}`, runs from the repo root, and is cited by
  path in the finding it produced.
- ⭐ **A smoke leaves its SCREENSHOTS in the arc.** The browser smoke is a script in `research/tools/` (real Chrome
  via the repo's browser driver, a sign-in token from the environment, ⛔ never a password in a file); its shots go in
  `research/{date}-{ticket}-smoke/` (or `research/<date>-baseline-shots/<wave>/`), named for what each proves,
  covering the control as well as the case — another tenant, light **and** dark, the refusal.
  The ticket's *Progress* cites the folder and states what each shot shows, with the numbers checked against the source.
- ⭐⭐ **ONLY THE REVIEWER SMOKES** (owner, 2026-10-09: *"THE SCOUTS SHOULD NOT SMOKE!! ONLY YOU SHOULD!!"*). 🧑 *"SCOUTS WRITE THE TESTS **AND** THE SMOKE SCRIPTS…
  THEY **DO NOT RUN THE SMOKES**, JUST THE TESTS!!"* — a helper writes the code, the tests, the RED proofs and the smoke
  script, and RUNS the tests; ⛔ it never runs a browser smoke. The reviewer runs it once, on the
  restarted shared stack, unrouted. A helper's smoke with no deadline has hung the larger part of a wave, and
  each wave has re-walked sign-in on its own.
  ⭐ Every smoke, gate and probe that calls a service carries a hard deadline and closes its browser in a `finally`.
- ⭐ **The browser driver is pinned** and drives the installed Chrome (`channel: 'chrome'`, no browser download). A smoke
  runs IN PLACE from the repo root — `bun plans.documented/<arc>/research/tools/<smoke>.ts <shots-dir>` — ⛔ never copied
  to a temp dir to install it there.
- **Correct in place.** A finding the code later contradicts is corrected where it stands (costs stay, superseded
  decisions do not) — AGENTS.md PART VI.7.

## 4 · ARCHITECTURE.md — DDD + oracles

⭐ **AT A GLANCE FIRST, VERSIONED; THE FULL ONE AFTER THE OWNER CONFIRMS A VERSION** (owner, 2026-10-09; versioned
2026-10-12). An arc ALWAYS writes the glance before `ARCHITECTURE.md` — the target on one page. ⛔ `ARCHITECTURE.md` is
written only after the owner has confirmed a version — a full design built on an unconfirmed shape is the most expensive
draft an arc can write.

🧑 2026-10-12: *"a chance to evolve the ASPIRATIONAL DIRECTION that defines the arc… doc from scratch every time… the best
practices from what we've measured, probed, experimented and conclude would be the best arc decisions."* And: *"how would
I be able to approve the at-a-glance if we haven't measured?"* The rules:

1. **One file per version:** `ARCHITECTURE-AT-A-GLANCE_v{n}_{concept}.md` — `n` counts up, `concept` names the idea that
   version stands on (`v7_one-site-snapshot`). Frontmatter: `slug: architecture-at-a-glance-v{n}`, `supersedes:` the
   previous file, `status: live` on the current one.
2. **Written from scratch, never edited into the next.** A new direction is a new file. Within a version, only its
   EVIDENCE may be updated in place (a measurement lands, a number is corrected); a changed decision is a new version.
3. **The target only — the aspiration.** The best design that what was measured, probed and concluded supports. ⛔ Never
   today's shape with "exists" / "today" columns: that carries the rot forward. Today's shape lives in the census
   research; what goes away lives in `TOMBSTONES.md`.
4. **Measured before it is offered.** A version the owner is asked to confirm cites the measurements it stands on
   (research files, receipts, probes on the disposable copy) — a version written from code reading and canon alone is a
   draft for discussion, and says so in its `status`.
5. **What a version holds:** the story · the shape · **the "what it replaces, and how" matrix** (owner, 2026-10-12: *"I
   did like the 'what it replaces and how' table"* — one row per screen or flow: the target (view ← job ← call) · what it
   replaces, by its `TOMBSTONES.md` row · how) · ONE state diagram (§1.8) · the contract sketch · the evidence · what it
   deliberately does not do · what is still open.
6. **Earlier versions stay**, `status: superseded by v{n+1}`, as the record of how the direction moved. The hub links the
   current version first and the previous one beside it.
7. **After confirmation** the confirmed version is the full design folded. Where the build departs from it, the
   departure is named in `ARCHITECTURE.md` §14 (as built); a change of DIRECTION is a new glance version, confirmed again.

1. **§0 the rules** it obeys · **§1 bounded contexts** · **§1b THE diagram** (one, here only — a DDD · Elmish · F# Mermaid
   state diagram, §1.8).
2. **The contract files, in compile order** — the F# types, written first.
3. **The oracle** — an executable `.fsx` beside the contract it specs, loading the SHIPPED types, with **numbered laws**,
   each **RED-proven by a named mutation** (break the code, watch exactly that law fail, restore). The floor lives in the
   oracle gate's roster and moves **in the commit that adds or deletes laws, with the reason** (AGENTS.md PART VIII).
4. **The journeys** — each user story as an oracle SCENARIO (assert after every step) plus where it is smoked.
5. **The flows (Elmish)** · **the waves** (smoke-ready, green at every commit; ✈ marks a deploy, only on the owner's word)
   · **decisions** (the recommendation typed, the alternative named) · **patterns, named** (nothing novel).
6. **The review ledger** — the design is rated by review rounds (each round's doc archived); **tickets are cut only after
   a rating ≥ 9/10**. Settled = a version stamp (*v13 — settled*).
7. **As built** — where the code differs from the design, named while in flight (§14), never silently.

## 5 · tickets/ and tickets/INDEX.md — the board

- **Earned, not speculated**: a ticket names the moment it cost us. Each has frontmatter, the acceptance test up front,
  `depends on`, and a **"Progress and what is owed"** section kept current.
- **The board** (`INDEX.md`): a waves table (`wave | tickets | the smoke that closes the wave | status`) and a tickets
  table (`# | ticket | wave | depends on | status`).
- ⭐ **A PLAN IS ALWAYS EXECUTED IN WAVES** (owner, 2026-10-09). The board makes the organization unmistakable before
  any ticket row: **the waves table comes first and IS the plan** — its order is the priority, each wave groups the
  tickets it ships, names the smoke that closes it, and carries its own status; every ticket row names its wave and what
  it depends on. Work that arrives after the plan (a post-mortem list) is its own wave row, never loose tickets.
  ⛔ A board a reader cannot answer *"what is next, and what ships with it?"* from, in one glance, is not a board.
- ⭐ **THREE BOARD LAWS** (owner, 2026-10-09):
  1. **A BOARD IS NOT A JOURNAL — KEEP IT CLEAN.** A status cell holds the status, its date, and at most one short clause
     (*what closes it*, or *what it waits on*) — never the story of how it got there. The evidence (commits, smokes,
     counts, what was tried) lives in the ticket's **"Progress and what is owed"**, and the narrative in `journals/`.
     The same holds for a list ticket's rows: what, where measured, the cost, then the outcome in one line with
     the commit. ⚠️ The tell: a cell that needs scrolling, or a sentence beginning *"then"*, *"note"*, *"⚠️ owed"*.
  2. **REVISED AFTER EVERY COMPLETION.** When a task completes, the ticket (its `status:` frontmatter + its Progress
     section) **and** the board row move **in the same commit** as the work, marked with the right progress symbol.
     The ticket's `status:` and the board's symbol must agree (`open` ↔ ⬜ · `in-progress` ↔ ◑ · `code-done` ↔ 🟦 · `done` ↔ ✅);
     a disagreement is a defect in whichever is older.
  3. **A BOARD ALWAYS CARRIES A LEGEND** — and the legend defines **every** symbol the board uses (status, ✈, ❓, ⚠️ …),
     at the top, as a table. A symbol used and not defined is a defect; a list ticket carries its own legend
     when its rows use symbols.
   ⭐ ENFORCED BY the arc-board gate, when the repo wires one: waves first with a status column and every
   ticket in a declared wave; status cells ≤ 120 chars and a Progress section on every ticket with work done; ticket
   `status:` ↔ board symbol; a LEGEND covering every symbol (the board's, and a list ticket's own); the index row in step.
   RED-prove each law on its own mutation; an unmutated copy passes. 🔴 The gate covers only the boards on its roster —
   an arc joins in the commit that brings its board to these laws. Until the gate exists, the reviewer's read is the check.
- ⭐ **The index of arcs** is `plans.documented/INDEX.md` — every arc with its ticket code, status, done / total and
  progress. When an arc's board moves, its INDEX row moves in the same commit. Older, undated or lingering work is parked
  in an archive that is never pruned, and every arc folder is named `YYYY-MM-DD-slug`.
- STATUS LEGEND (the default): ✅ done · 🟦 code done + smoked locally, closes on the deploy smoke · ◑ partly done (what is
  owed is named) · ⬜ open · ❓ waits on an owner ruling · ✈ a deploy, only on the owner's word.
- **A post-mortem list ticket** collects what the build surfaced: one dated row per item, *where it is measured*,
  *the cost / the risk*, and its outcome written into the row (✅ DONE … with commits and the smoke). New findings are
  **appended as found**, never acted on unasked.
- ⭐ **`POST-MORTEM.md` at the arc root** (owner, 2026-10-09) is where a finding OUTSIDE the arc's tickets goes — a
  defect a helper hit on the way, a decision the arc cannot make. Same row format as the list ticket, linked from the hub;
  ⛔ never a loose question left in a chat, never a ticket opened unasked.
- ⭐ **The board is current at every commit and read back before it** (owner rule). A user story's
  `KNOWN_ISSUES.md` uses the same format plus a `relates to ticket(s)` column.

## 6 · journals/

Every iteration, appended: **why I am on this · what I just finished · what I am on now · what is next · re-read the plan
and my own notes**. ⭐ **One file per working day** (`journals/{date}-journal.md`) — a day with no journal is how a board
becomes one: the narrative has nowhere else to go. Costs stay; a journal line that now misleads is corrected or deleted
(AGENTS.md PART VI.7, owner ruling 2026-08-27).

## 7 · HANDOFF-MEMORY.md — the hub

- `read_order: 1`. A TL;DR, then **⭐ RESUME HERE** (dated): what was just done (with commits), what is next, and what
  waits on the owner's word. The owner's rulings, verbatim and dated (🧑 *"…"*). The read order of the rest.
- Updated **before every compaction and at the end of every wave** — the next agent starts here, cold.
- Auto-memory holds only a **pointer** to the hub plus the rulings that would otherwise be re-litigated (AGENTS.md PART VI.8).

## 8 · How a wave runs (the working agreement)

1. Read the hub → the board → the ticket. 2. Contract + oracle first (RED-proven). 3. Code, layer by layer, with teaching
notes. 4. Gates: the oracle touched, the typecheck, the targeted tests, one full suite of what changed. 5. **Restart the
stack the way this repo starts it, and smoke it yourself in a real browser and against the source of truth** — a green
build is not a smoke. 6. Update the ticket, the board, the hub.
7. One commit, **explicit pathspecs**, the secret check (search the tree for any secret value you handled; it prints
nothing) — ⛔ never push, PR or deploy without the owner's word; ⛔ never commit when the owner says not to. Helpers
research or build in parallel but **never commit, restart or deploy**; the lead re-runs every gate a helper reports (layer 3).

## 9 · The engineering docs that close an arc

When a user story works, it is written up under `docs/engineering/user-stories/<story-set>/` (stories **as they work
today**, Mermaid state diagrams, `KNOWN_ISSUES.md`, `CALL-SITES.md`) and the engineering docs per mechanism. When a
system of record is involved, its engineering docs and one concrete use case are written there and cross-linked in
frontmatter. The law for those docs is that repo's engineering-docs doctrine.

## What is NOT settled

- Arcs that predate this doctrine are not retrofitted (LATEST WINS — AGENTS.md PART VI.6).
- Where a completed arc's folder MOVES (AGENTS.md PART VI.9) is decided per repo, not in this file.
