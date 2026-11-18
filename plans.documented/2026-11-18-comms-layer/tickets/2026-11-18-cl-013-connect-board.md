---
title: "cl-013 Connect is the mount board"
slug: cl-013-connect-board
aliases: [cl-013]
date: 2026-11-18
type: ticket
arc: 2026-11-18-comms-layer
status: done
wave: 8
depends_on: [cl-012]
tags: [ticket, connect, elmish]
---

# cl-013 Connect is the mount board

Hub: [[HANDOFF-MEMORY]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v3_integrations]]. Cost: [[2026-11-18-connect-is-brochure]]. Board: [INDEX](INDEX.md).

## Acceptance

`#connect` is five Channel Out cards (Email, LinkedIn, Voice, Sms, Ringless voicemail). Each card shows occupancy (Fake vs plugin id), `ready` / `needs_credential`, Mount from `candidates`, Unmount. Voice candidates are `[]` — no pretend dialer. HubSpot write is one line of copy (Relay, env, not this board). Apollo enrich, Jev test, privacy list stay. Elmish: location is already `#connect`; `Msg = Mounted | Unmounted | Loaded of snapshot`; `seq` drops stale HTTP. Page holds slot ids, not plugin objects. GET/POST `/api/integrations` never returns keys. `/api/status` carries a mounts summary; the old `instantly.send` key dies.

## Progress and what is owed

- Wave 8: `GET/POST /api/integrations`. `/api/status` `mounts`. `#connect` five Channel Out cards. Voice candidates `[]`. Fake smoke `:8786` 2026-11-18. Closed with cl-012 and cl-014.
