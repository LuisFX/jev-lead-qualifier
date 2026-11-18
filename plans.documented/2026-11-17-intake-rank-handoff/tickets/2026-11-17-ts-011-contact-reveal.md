---
title: "ts-011 Contact is revealed from disposition"
slug: ts-011-contact-reveal
aliases: [ts-011]
date: 2026-11-17
type: ticket
arc: 2026-11-17-intake-rank-handoff
status: done
wave: 4
depends_on: [ts-009]
tags: [ticket, disposition]
---

# ts-011 Contact is revealed from disposition

Hub: [[HANDOFF-MEMORY]]. Oracle L22–L26.

## Acceptance

No `email_revealed` column. The API returns `contact: hidden | revealed`. Unreviewed and Dismissed are hidden. Held, Queued, and HandedToCloser are revealed. A dismissed lead's email is absent from the JSON.

## Progress and what is owed

- 2026-11-17: API `contact: hidden | revealed` from `contactOf`. Unreviewed and Dismissed omit the address. No `email_revealed` column.
