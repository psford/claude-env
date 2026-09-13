# Session State

_Last updated: 2026-09-12 (session end — Patrick is launching a process that may crash this machine)_

## Where things stand, 2026-09-12

The board is the state of the work; this is only what the board cannot say.

**Accepted today:** CE-12.7, CE-12.4 (claude-env); CH-224.37 (harness).

**At `in_review` with every criterion Clyde-passed and NO QA verdict** —
CH-224.33, CH-224.39, CH-224.41. Not a bounce: QA ran out of time. Pick
these up first.

**CH-224.41 needs Patrick's eyes** on AC1, at http://localhost:8787
(serving e746ea5). Every story card carries a hairline bar filled to the
fraction of its criteria that are verified; a card with a live worker on
it carries a breathing blue halo. 95 bars and 1 halo at deploy time.

**THE OPEN QUESTION IS QA'S COST.** Patrick set the dispatch budget at
**5 minutes** (`GLM_AGENT_TIMEOUT`, now defaulted to 300 in glm-agent) and
moved QA to the **sonnet** tier. CE-12.4 passed inside that. CH-224.33 and
CH-224.39 did not. Measured: a MINIMAL prompt at opus/high took 5m24s and
recorded nothing, so the cost is QA's own method, not the prompt. The
remaining levers are CH-224.38 (judge the delta, not the branch) and
CH-224.40 (QA gates the release, not every ticket) — both filed, both
Patrick's call because each loosens a control that checks the dev.

**Do not raise the ceiling.** It is a budget, not an estimate. A review
that cannot answer in five minutes is reviewing too much.

**Clyde runs per-criterion, in parallel, inside ONE approved command.**
The dispatch gate refuses a backgrounded dispatch, so `&` + `wait` in a
single command is the only parallelism available — and it still shows
Patrick every prompt. Do not write procedures into a Clyde prompt: name
the criterion, say exercise it, stop.

## Orientation, not hand-off

Patrick, closing: **"the board should be the state of the work."** A new
session orients from the ticket stores (`ticket list` per repo), not from
this file. Nothing is in flight anywhere; every open ticket is a valid,
pruned backlog item. Memories carry the behavioral rules; this file only
points.

## Facts a fresh session needs fast

- **omni-map is LIVE**: https://omni.psford.com (Cloudflare Worker, merge
  to main = deploy, suite runs in the build container). Azure backend
  func-omnimap-prod (GoMOFS relay + hourly NDBC snapshot blob). develop ==
  main. Specs: docs/SPEC-FUNCTIONAL.md / SPEC-TECHNICAL.md; runbooks:
  docs/DEPLOY.md / DEPLOY-API.md.
- **Before any omni-map push**: run the suite prod-env-shaped
  (VITE_API_BASE + VITE_SNAPSHOT_BASE set) AND remember every develop push
  fires a metered Cloudflare build — batch to release time, PRs via
  `ticket release` only.
- **az CLI on this box is logged in as PATRICK** (his provisioning login),
  not the photo-portfolio SP. Restore before photo-portfolio Azure work.
- **Zero trust / TNO** is in the shared core: no agent-usable hook
  bypasses exist or will; a block means satisfy-or-surface.
- The PR-state hook's "N unmerged commits" line is stale without a fetch;
  verify with `git fetch` + `git log origin/main..origin/develop` before
  believing it either way.
- Open threads by board: omni-map OM-26.5/26.7 (source ideas), OM-31.2/31.3
  (EV probe-from-Azure, lightning licensing-first); claude-harness board
  untouched by the prune, awaiting a session with Patrick; nail down the
  release-ticket process (his open ask); session-log commits need a lane
  through the ticket commit guard (file a CH ticket).
