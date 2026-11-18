---
title: "ts-004 Named ICP versions"
slug: ts-004-profile-versions
aliases: [ts-004]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 2
depends_on: [ts-001]
tags: [ticket, profile]
---

# ts-004 Named ICP versions

Hub: [[HANDOFF-MEMORY]]. Cost: [[2026-11-17-icp-is-one-file]]. Tombstone T2.

## Acceptance

Saving the editor inserts a new version row with an `IcpVersionId`. It does not replace previous rows. Loading a preset is a new version, not an overwrite of `data/icp.json` as the only copy. The live version is the one `assemble` reads. Preset files stay seeds.

## Progress and what is owed

- 2026-11-17: `icp.save` inserts `icp_version` and points `app_state`. Two saves → two rows. Presets remain files.
