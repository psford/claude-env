# Session State

_Last updated: 2026-09-01 ~00:15 (session close — the night omni-map went public)_

## The headline

**omni-map is live on the internet and it works.** https://omni.psford.com —
Cloudflare Worker static site (merge to main = deploy, suite gates the build
in the container), Azure Functions backend (func-omnimap-prod on the
asp-stockanalyzer P0v3 plan), and a working SNAPSHOT PIPELINE (timer →
blob → CORS) with NDBC buoys as its first consumer (841 stations, hourly).
Shipped this session: GoMOFS relay port, Pages→Workers deploy, custom
domain, wildfire perimeters (WFIGS), PM2.5 smoke, USGS earthquakes, NDBC
buoys, collapsible panel sections, clear-all button. 437 tests. Patrick,
closing: "this was an excellent session, regardless of me getting mad."

## Where things stand

| Repo | State |
|------|-------|
| omni-map | `develop` == `main` @ 9338a71 (PR #24). LIVE + verified (all bakes grep-confirmed, blob CORS curl-confirmed). Epics OM-13/26/27/28/29 closed or awaiting Patrick's epic-accept (OM-26); OM-31 open holding OM-31.2 (NREL EV — probe from Azure, WSL can't resolve the host) and OM-31.3 (lightning — LICENSING CHECK before any code). |
| claude-env | `develop` == `main` (PR #64 / CE-8). TNO row + hatch deletion live. |

## Rules that changed tonight (all in memory + shared fragments)

- **ZERO TRUST / TNO**: no agent-usable hook bypass, ever; PR_BEFORE_ACCEPT_OK deleted; exceptions are Patrick's hands.
- PRs via `ticket release` ONLY (raw gh pr create starves the merge-reconcile).
- Builds succeed first-try 99.9%: scratch-clone sim BEFORE push, simulating PRESENCE (VITE_* baked vars) and ABSENCE (dangling symlinks, no CLIs) both.
- Cloudflare build minutes are metered: batch develop pushes to release time.
- Runbooks from the live UI/docs, never memory; epics never filed bare; asks are one bolded line; name the test SURFACE (localhost:5173 vs omni.psford.com).

## Azure facts (verified)

- rg-omnimap-prod: func-omnimap-prod (managed identity, Storage Blob Data
  Contributor on stomnimapprod), snapshots container (public blob,
  allowBlobPublicAccess flipped true — fine while snapshots-only), CORS for
  both site origins. Timer snapshot-ndbc hourly at :15; admin force-run
  recipe in docs/DEPLOY-API.md. Post-zip-deploy: CHECK `az functionapp
  function list` — a deploy mid-warmup leaves a stale function index
  (restart fixes).
- az CLI on this box = PATRICK's login (not the photo-portfolio SP).
  Restore SP before photo-portfolio Azure work.

## Retro fodder (Patrick flagged)

- Env-dependent test failed the CF build hours after the 99.9% rule (the
  presence-simulation gap). Two failed builds before that on machine-local
  tests. The gaslighting incident re: the merge monitor. All in memory.
- Release-ticket process: Patrick wants it nailed down further (open thread).

## Session-spawned processes

- vite dev server on :5173 (killed at session end); all background watchers
  completed.
