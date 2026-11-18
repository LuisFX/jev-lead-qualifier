---
title: "cl-014 Retire INSTANTLY_SEND as the Email switch"
slug: cl-014-retire-instantly-send
aliases: [cl-014]
date: 2026-11-18
type: ticket
arc: 2026-11-18-comms-layer
status: done
wave: 8
depends_on: [cl-012]
tags: [ticket, tombstone]
---

# cl-014 Retire INSTANTLY_SEND as the Email switch

Hub: [[HANDOFF-MEMORY]]. Glance: [[ARCHITECTURE-AT-A-GLANCE_v3_integrations]]. Cost: [[2026-11-18-instantly-send-is-the-email-switch]]. Tombstone: [[TOMBSTONES]]. Board: [INDEX](INDEX.md).

## Acceptance

`default_bindings` no longer reads `INSTANTLY_SEND`. Composition is `compose(catalog, load_mounts())`. `rg INSTANTLY_SEND leadqualifier/bindings.py` is 0. InstantlyEmail is registered in the catalog only. `config.instantly_api_key` / campaign id remain the **ready** probe. Do not reopen [cl-007](2026-11-17-cl-007-instantly.md). Do not POST Instantly as this ticket's smoke.

## Progress and what is owed

- Wave 8: `default_bindings` is `compose(catalog, load_mounts())`. `rg INSTANTLY_SEND leadqualifier/bindings.py` → 0. Tombstone in [[TOMBSTONES]]. Closed 2026-11-18 with cl-012 and cl-013. No Instantly POST.
