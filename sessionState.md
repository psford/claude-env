# Session State

_Last updated: 2026-08-08_

## Where things stand

| Repo | State |
|------|-------|
| claude-env | `main`, clean. All guard fixes merged (#36–#41). |
| claude-harness | `main`. v0.1 built and used. **PR #10 open** (README). |
| photo-portfolio | `main`, **deployed**. Social link previews live on psford.com. |

## What happened (2026-08-07 → 08)

### 1. The guardrails were theatre, and now are not

An audit triggered by one of my own violations found that **0 of 19 repos enforced branch
protection against Patrick** — 16 unprotected, 3 with `enforce_admins: false`, which exempts the
only account that pushes. Separately, five `psford-hook-*` plugin directories had never been
registered, so none of their hooks had run for months, and 31 hooks were inspecting the wrong
repository in a multi-repo workspace (silently passing, which is worse than failing).

All fixed. The one that matters: **18/19 repos now carry `enforce_admins: true`, and the `gh`
token is scoped to Administration: read** — so the protection is unreachable from this session.
Every other fix depends on me behaving; that one does not.

Full incident list is in `claudeLog.md`.

### 2. claude-harness v0.1 exists and has been used

A ticket-driven process: store + CLI, four role skills, three gate hooks, question queue.
Design in `claude-harness/docs/design/001-ticket-driven-development.md`. 81 tests.

**One real feature shipped through it end to end** — Open Graph / Twitter card meta for
photo-portfolio. Five stories, one epic PR (photo-portfolio#56), one human UAT verdict against a
live Cloudflare preview, **zero commit approvals required**. Live on psford.com now.

## Where to start next

**Restart the session first.** The plugin cache has the hooks and skills but nothing has loaded
them yet. Three things must be true for a hook to fire — marketplace registered, plugin
installed, session started after both — and only the third is missing.

Then, in priority order:

1. **CH-3's guarantee is unproven.** The gate hooks were not loaded during the CH-4 run, so the
   CLI's gates were exercised but not the hooks that stop an agent bypassing the CLI entirely.
   That is the only claim in the store never tested the way it will be used.
2. **CH-8 — the dashboard.** Every human gate currently costs a terminal. Patrick's design
   decision: approvals behind auth the agent does not hold. Separation of duties by credential,
   not by a hook the agent could edit. And it must make the *recorded* state the thing you look
   at — he once believed he had approved something that never reached the store.
3. **Acceptance criteria cannot be edited or removed.** Hit twice. No `ac edit`.

## Open PRs

- claude-harness #10 — README

## Standing notes

- **Deploys are Patrick's.** Gate preparation is mine: checkout main at the merge commit, run
  `npm run gate:e2e`, surface a preview if layout changed, then hand him ONE line.
- `npm run cf:preview` (photo-portfolio) publishes a preview URL without touching production.
  UAT means a test region, not a screenshot.
- The plugin cache is a pinned copy. Editing `plugins/` changes nothing until reinstall +
  restart.
