# First Read — architecture at a glance

Date: 2026-11-17. This is the short map. The module-level write-up is [ARCHITECTURE.md](ARCHITECTURE.md).

First Read qualifies an inbound lead before a person opens it. One request to Jev (TypeSafe System One, model `jev-1.13.0`) answers a set of atomic questions about that lead. Ordinary Python turns those probabilities into a fit score, an intent score, a tier, a route, and a next action. The ideal customer profile (ICP) is data. Weights, thresholds, and routing stay in code.

The demo ships 65 fictional leads, 12 CRM accounts, and hidden gold labels for the default ICP (`lanternfield_agencies`, client Lanternfield Automation).

## The system in one picture

```mermaid
flowchart LR
  subgraph sources [Inbound shapes]
    msg[Message<br/>form, DM, reply]
    bio[Person bio]
    profile[Company profile]
  end

  subgraph app [First Read · one process]
    ui[Browser UI<br/>web/]
    api[FastAPI<br/>leadqualifier/server.py]
    qual[Qualifier<br/>pipeline.py]
    score[Scorer<br/>scoring.py]
    disk[(data/<br/>leads, ICP, CRM, cache)]
  end

  jev[Jev<br/>POST /v1/systemone]
  person[Person on the team]

  sources --> disk
  ui <--> api
  api --> qual
  qual --> score
  qual <--> disk
  qual -->|"missing questions only"| jev
  jev -->|typed probabilities| qual
  score -->|tier, route, action| ui
  ui --> person
```

`./run.sh serve` starts one uvicorn process on `127.0.0.1:8780`. The browser is a single HTML page with plain CSS and JS. There is no build step and no database.

## One lead, one request

```mermaid
sequenceDiagram
  participant UI as Browser
  participant API as FastAPI
  participant Q as Qualifier
  participant Cache as answers.json
  participant Jev as Jev

  UI->>API: GET /api/run/stream
  API->>Q: score(lead)
  Q->>Q: build questions from ICP + lead
  Q->>Cache: answers whose fingerprint still matches
  alt some questions are missing
    Q->>Jev: state + missing questions
    Jev-->>Q: probabilities
    Q->>Cache: store new answers
  end
  Q->>Q: assemble tier, route, action
  API-->>UI: SSE result
```

A full cache hit asks Jev nothing. Changing a weight or a threshold re-scores from cache. Changing a pain's wording changes that question's fingerprint, so the next run asks only the questions that moved.

## Who decides what

```mermaid
flowchart TB
  icp["ICP JSON<br/>industries, personas, pains, disqualifiers<br/>weights, thresholds, routes"]
  questions["constants.build_questions<br/>Choice, Score, Noul"]
  jev["Jev<br/>one probability distribution per question"]
  code["scoring.assemble<br/>fit, intent, overrides, gate, route, action"]

  icp --> questions
  questions --> jev
  jev --> code
  icp --> code
  code --> board[Tier board and lead page]
```

Jev never sees the arithmetic. The ICP text lives in question criteria. The lead state is the company, the person, the message, and sentence ids. Email addresses and phone numbers stay off that state.

## How a tier is chosen

Overrides run first. The matrix runs only when none of them fire.

```mermaid
flowchart TD
  start[Answers for this lead] --> spam{Spam at or above spam_p?}
  spam -->|yes| dq[Disqualify]
  spam -->|no| crm{CRM match at or above dedupe_p?}
  crm -->|yes| existing[Existing account]
  crm -->|no| other{Any other disqualifier?}
  other -->|yes| dq
  other -->|no| matrix[Fit band × intent band]
  matrix --> timing{Warm and a timing objection?}
  timing -->|yes| nurture[Nurture]
  timing -->|no| tier[Hot, Warm, or Nurture]
  dq --> gate[Confidence gate]
  existing --> gate
  nurture --> gate
  tier --> gate
  gate --> route[Route for the tier<br/>hold when a human should confirm]
```

Default bands on the Lanternfield ICP: fit hot `0.62`, fit warm `0.42`, intent hot `0.60`, intent warm `0.25`.

| | Intent high | Intent mid | Intent low |
| --- | --- | --- | --- |
| Fit high | Hot | Warm | Nurture |
| Fit mid | Warm | Warm | Nurture |
| Fit low | Warm, flagged | Nurture | Nurture |

Fit is a weighted mix of industry, maturity, persona, and pain, then a size penalty and a geography penalty. Intent is a weighted mix of purchase-intent level, a meeting ask, budget, urgency, and timeline. A bare profile cannot ask for a meeting, so those message-only signals stay at zero.

## What the browser talks to

```mermaid
flowchart LR
  pipeline[Pipeline] -->|SSE run| stream["/api/run/stream"]
  lead[Lead] -->|cached detail| detail["/api/leads/{id}"]
  icp[ICP editor] -->|live re-tier| rescore["POST /api/rescore"]
  icp -->|save| put["PUT /api/icp"]
  accuracy[Accuracy] -->|gold, default ICP only| metrics["/api/metrics"]
  connect[Connect] -->|optional| apollo["POST /api/apollo/enrich"]
```

Apollo enrichment is a side lookup by domain. It is off unless `APOLLO_ENRICH=1` and `APOLLO_API_KEY` are both set. Its result never enters a Jev request. The three Apollo roles (live lookup, export-shaped demo leads, and the Connect copy) are in [how First Read uses Apollo](apollo/2026-11-17-how-first-read-uses-apollo.md).

## Where the code lives

| Piece | Role |
| --- | --- |
| `leadqualifier/server.py` | HTTP, SSE jobs, in-memory app state |
| `leadqualifier/pipeline.py` | One lead or many; cache merge; thread pool |
| `leadqualifier/constants.py` | Question texts, model pin, fingerprints |
| `leadqualifier/scoring.py` | Fit, intent, tier, gate, route, action |
| `leadqualifier/jev.py` | HTTP client, retries, cost |
| `leadqualifier/cache.py` | `data/cache/answers.json` |
| `leadqualifier/dedupe.py` | Generous CRM shortlist, at most 10 |
| `web/` | The six pages and the demo panel |
| `data/` | Live ICP, presets, leads, CRM, playbook, gold |

`FIRSTREAD_FAKE=1` swaps in `fake_client.py`. The UI still renders. The status pill says the numbers are a stand-in.

## Reading next

[ARCHITECTURE.md](ARCHITECTURE.md) covers the question set, the cache key, the assemble order, the SSE job, and the failure paths.
