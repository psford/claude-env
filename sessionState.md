# Session State

_Last updated: 2026-09-01 (session end — context cleared for the new Claude update)_

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
