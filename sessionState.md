# Session State

_Last updated: 2026-08-30 (end of a long session — context cleared after this)_

## Where things stand

| Repo | State |
|------|-------|
| claude-env | `develop` @ `efb5740`, pushed, **9 ahead of `main`, no PR** |
| claude-harness | `develop` @ `63f3ae8`, pushed, no PR |
| omni-map | `develop` @ `87fdc02`, pushed. **PR #8 open → `main`** (14 commits) |
| road-trip | `develop`, pushed, clean |
| stock-analyzer | `fix/bicep-appservice-sku-p0v3`, pushed. 8 untracked leftovers, **not mine** |
| photo-portfolio | `main`, PR #57 merged. 1 dirty file is a ticket JSON, not mine |
| T-Tracker | PR #21 merged to `master` |
| SysTTS / whisper-service / gpu-crash-analyzer | `develop`, pushed, clean |

**Nothing of mine is uncommitted or unpushed.**

## What waits on Patrick

- **omni-map PR #8** → `main`. Two epics: seabed, and units. Not deployed
  anywhere; omni-map runs locally only.
- **OM-13** is a draft epic awaiting scope approval — add jsdom so the render
  path is tested. He asked for it to be filed.
- **claude-env is 9 commits ahead of `main`** with no PR.

## What happened

Four things, in order.

**CE-5 — the shared rules became one file.** Eleven repos each held a copy of
`00-universal.md` and nothing compared them. A fragment with no `{{VARS}}` is now
symlinked into `.claude/rules/`; all ten linked repos resolve to **one inode**.
`git-flow-develop-main` joined them (it had one value across eight repos);
`git-flow-trunk` stays generated because its two consumers genuinely differ.
`shared_rules_link_guard` refuses a commit in a repo whose links are missing.

**CH-192.1 — a commit may name another repo's ticket.** Built mid-epic because
the cross-repo wall blocked the rollout twice and cost Patrick three button
presses for one repo.

**OM-6 — seabed on its own switch.** The configurable-`layers=` design would
have broken the chart OFFLINE, because the cache keys on the resolved URL. Two
static templates instead.

**OM-5 — units, and our own soundings.** omni-map went 222 → 313 tests.

## The pattern worth carrying forward

**Controls that could not fail** found three separate defects: `--check` was not
read-only, `shared_rules_link_guard` could be bypassed by any env prefix, and
`git -C $var` makes every guard judge the wrong repo. When a mutation changes
nothing, the usual explanation is that the test never tested it.

**An instrument returning a confident negative** happened three times — a probe
reading the wrong JSON field, a bbox pointed at empty water, a `str.replace`
that matched nothing. Each time the fix was the same: make the instrument find a
known positive before believing a zero.

**Research reproduced exactly and still concluded wrongly** twice in OM-5. The
epic's ENC figures were right and its band had zero soundings where the app is
used; its S-52 threshold was ten metres off. Verify per the case you care about,
not per the headline number.

## Mistakes on the record

- The soundings layer **shipped drawing nothing** (no `glyphs` in the style,
  silent). I had named that exact gap in the QA an hour earlier.
- I filed **CH-224.19** claiming the harness could not tell a bug from a refused
  approach. It can — `iterate` — which Patrick then used. I had read the rule
  that blocked me without reading the verdict list it consults. Ticket rewritten
  to the real, narrower problem.
- I gave Patrick a command that **could not work** (`ticket move --actor human`
  past a rejected verdict; the rule exempts no actor).
- I killed his dev server with a `pkill` pattern that matched both his and mine.
- Repeated feedback, now in memory as `feedback_lead_with_the_verdict`: **walls
  of text with no verdict, then stopping.** The ENC report was the worst case —
  five findings, four of which I already knew how to fix, presented as a hazard
  list. He read it as "this isn't going to work."

## Filed, not started

| | |
|---|---|
| `CH-224.16` | `mechanical-check` cannot read bash test names — every claude-env criterion resolves N/C |
| `CH-224.17` | no registry of local ports (8787 collided; cost a day of photo-portfolio pushes) |
| `CH-224.18` | a finished epic never reaches Patrick's queue, so it can never be closed |
| `CH-224.19` | a mis-recorded `rejected` verdict cannot be corrected |
| `CH-192.2` | a shell variable in a path makes a guard judge the wrong repo |
| `OM-13` | jsdom — the render path is untested (draft, needs scope approval) |
| `TT-3` | T-Tracker harness normalisation |

## Known environment facts

- **A 404 from `gh` means the robot cannot SEE that repo**, never that a feature
  is disabled. This cost a wrong claim written into road-trip's rules. See
  `reference_robot_github_access`.
- road-trip's Actions ARE enabled; CI runs there and passed on every push today.
- photo-portfolio's playwright suites moved to port **9787** — 8787 is the
  harness dashboard.
- omni-map's `.claude/rules` links are relative: claude-env must sit beside it.
