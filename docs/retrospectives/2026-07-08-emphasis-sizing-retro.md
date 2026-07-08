# SDLC Retrospective: photo-portfolio "Emphasis Sizing" (3 attempts, 3 rejections)

**Date:** 2026-07-08
**Scope:** 2026-06-26 → 2026-07-08. Attempt 1 (row-height boost, descoped in-phase), attempt 2 (single-screen overview, PRs #48/#49, deployed 2026-06-27, prod-rolled-back and reverted via PR #53, 1,571 lines deleted), attempt 3 (span-layout bands, built fully 2026-07-08, rejected on first owner visual review, discarded uncommitted, ~800 lines). Survivor: PR #54 (responsive-sizes blur fix, 263 lines). Analysis: 4 parallel artifact-analyzer agents (retro-logs, git history, test coverage, plan accuracy) + 3 mitigation-researcher agents. Full researcher outputs with complete implementation code are preserved in the session transcript; code summaries below are the approved-for-implementation references.

## What Went Well

- **Rapid, decisive root-causing once problems surfaced.** Fill-neutralization proven by probes same-day (decisions.md 2026-06-26); prod rollback within ~28h of deploy via `wrangler rollback` before reverting main (ea8264b).
- **Strong functional-core discipline.** All three attempts had sound pure-math engines with real unit coverage (22 tests on `justify()`, 14 geometry tests on the tossed span engine); the technical diagnosis (flex-wrap is 1D; emphasis needs 2D positioning) is durable knowledge.
- **Decision records are excellent.** decisions.md captures each failure with mechanism-level why; this retro was possible largely because of it.
- **The one thing users actually needed shipped.** The blur fix (PR #54) was extracted from the wreckage: zero visual change, kills 2× derivative upscaling, fully verified.

## What Went Poorly

### Theme A — No design/feasibility gate before code (the dominant waste driver)
- 0 of 3 attempts had an **approved** design before implementation. Attempt 2's design plan literally said `DRAFT — pending Patrick's sign-off` **on the exact assumption implementation later disproved** — and implementation proceeded (design-plans/2026-06-26-overview-single-screen.md:195; phase_01.md:41-47).
- Attempt 3 had **no design doc at all**: problem statement → full code → rejection, one session.
- All three rejections were **aesthetic** ("looked bad in production", "big regression") — the *look* was never validated cheaply; layout math was treated as the design.
- `docs/feasibility-template.md` exists (created by a previous retro) and was never instantiated; the guard hook that references it is advisory-only (always exits 0).
- ACs were locked pre-feasibility and descoped mid-phase without amending plans: `phase_04.md` still lists AC4.2 as active while `test-requirements.md` marks it DESCOPED.

### Theme B — Test blind spots that let layout defects reach the owner
- **No zoom coverage.** The band-starvation defect was found by Patrick zooming his browser; the 5-project Playwright matrix varies viewport width at 4 fixed sizes only. The single-screen plan's AC6.2 explicitly required deviceScaleFactor tests — dropped with the revert. (Research note: DSF changes DPR, not CSS layout — the correct zoom-out emulation is a *larger CSS viewport*.)
- **No layout-invariant assertions** anywhere in e2e: nothing checks rows fill the container, no overlaps, no voids.
- **No visual regression/screenshot testing** — "looks wrong" is only ever caught by Patrick, at the most expensive possible moment.
- **Fixture too small**: 2 featured photos can never wrap into multiple rows; multi-row packing was structurally untestable.
- **Per-request `Math.random` shuffle** makes e2e nondeterministic — caused a flaky webkit axe contrast failure (photo behind the translucent lightbox overlay differs per load).
- The 4K project exists but the form-factor sweep explicitly `test.skip`s it.

### Theme C — Process/record gaps
- **Invisible rework:** attempt 3 (~800 lines) left zero git artifact; only a hand-written decisions.md entry records it.
- **Deploy before defense:** attempt 2 deployed before its defensive tests ran; lightbox broken in prod ~4h. `cf-deploy-preflight.sh` still checks only two env-leak classes — no clean-tree/HEAD==origin/e2e-freshness/visual-ack gate.
- **Plan drift:** descoped ACs never propagate back into phase files (concrete instance verified: phase_04.md/AC4.2).

## Proposed Mitigations (11, all with complete drop-in code from the researchers)

### Category 1: Automated Prevention (hooks/gates)
| ID | Mitigation | Prevents | Effort |
|----|-----------|----------|--------|
| A1 | `design_signoff_guard.py` (claude-env + wired to photo-portfolio): blocks commits of visual-surface files (`src/site/**`, `src/pages/**`, `*.astro`, `*.css`) on `feat/*` branches unless a matching `docs/design-plans/*.md` carries a real `**Sign-off:**` line. Bypass: `<!-- DESIGN-SIGNOFF-OK: reason -->`. Retro-tested: would have blocked both attempt 2 (DRAFT doc) and attempt 3 (no doc). | The exact attempt-2/-3 failure modes | M |
| A3 | Upgrade `feasibility_ref_guard.py` from advisory to risk-gated block: design plans matching incident-derived risk keywords (layout/resize/zoom/lightbox/deploy/auth/…) must link a filled `feasibility-*.md`; adds a "Visual/Layout Feasibility" section requiring a proto-layout render verdict. | Feasibility template staying unused | S |
| C1 | Deploy gate: shared `helpers/deploy-gate.sh` (claude-env) sourced by `cf-deploy-preflight.sh` — requires main + clean tree + HEAD==origin/main + `.deploy-gate` stamp (SHA-matched, ≤24h, written only by a green `npm run gate:e2e`) + `VISUAL_REVIEWED=1` when the diff since last deploy touches layout/style paths. Bypasses logged. | The attempt-2 prod incident class | M |
| C2 | Park-before-toss: `helpers/park-work.sh <slug>` snapshots the working tree to `refs/parked/<date>-<slug>` without touching HEAD/index/tree; PreToolUse hook blocks `git restore`/`checkout --`/`clean -f`/`rm` that would discard ≥150 uncommitted lines until parked (bypass `PARK_OK=1`). | Attempt-3-style invisible rework | M |
| A4 | AC-descope drift: extend existing (unwired) `helpers/validate_ac_coverage.py` with DESCOPED-awareness + thin commit hook; catches `phase_04.md`-style stale ACs. Verified against the real historical drift. | Stale plans misleading future sessions | M |

### Category 2: Automated Detection (tests/monitors)
| ID | Mitigation | Catches | Effort |
|----|-----------|---------|--------|
| B3 | `e2e/layout-invariants.spec.ts` + own config/fixture: groups tiles into rows by geometry; asserts row-fill, common height, no overlap, no void — across width×zoom-equivalent sweep (1280–3840×1/1.25/1.5) + breakpoint edges, chromium/firefox/webkit. Would have caught the band-starvation defect automatically. | The shipped defect class + the 4K skip + the zoom gap | M |
| B4 | Visual regression: `toHaveScreenshot` on `.proto-grid` only, chromium-only, photo bytes mocked to a flat pixel, deterministic `?seed=`; committed baselines; human-reviewed updates. | "Looks wrong" before Patrick sees it | L |
| C3 | SessionStart plan-staleness scan (advisory, print-only): fills the one gap the existing `plan_descope_drift_guard.py` can't (plans never re-touched after a descope). | Silent plan rot | S |

### Category 3: Code Guards
| ID | Mitigation | Fixes | Effort |
|----|-----------|-------|--------|
| B1 | Deterministic shuffle seed: extract the test suite's existing `mulberry32` into `src/site/core/seeded-random.ts`; `index.astro` honors `?seed=N` (else `Math.random` as today); a11y spec uses `?seed=1`. Root-causes the flaky webkit axe test. **Decision needed:** `?seed=` would be live (harmless) on prod — accept, or gate to the localhost manifest? | Shuffle-induced e2e nondeterminism | S |

### Category 4: Tooling/Workflow
| ID | Mitigation | Enables | Effort |
|----|-----------|---------|--------|
| A2 | **Visual prototype harness** (`scripts/proto-layout/render.mjs` + pluggable layout functions): fetches the real prod manifest, runs any `layout(items, opts)` pure function, emits one static HTML with real photos absolutely positioned. A layout idea becomes *viewable in Firefox in ~2 minutes* with zero app code. Ships with the baseline `justified` layout and a worked example reproducing the rejected row-height-boost (visibly does nothing — the defect that took a full implementation to discover). This is the root-cause attack: all three rejections were aesthetic and each cost a full build to find out. | Look-before-build for every future layout idea | S–M |
| B2 | `scripts/generate-large-pool-fixture.mjs` → committed `manifest.large-pool.json` (14 photos, mixed aspects/tones, reusing the test suite's verified blurhash constants). | Multi-row coverage; prerequisite for B3/B4 | S |

### Category 5: Process (no automation available)
- **Emphasis stays parked** until a design conversation anchored on *visuals* (mood board / proto-layout renders), not mechanisms. Already recorded in decisions.md + session memory; A1/A2 make the gate structural rather than remembered.

## Implementation Priority (impact ÷ effort)

1. **A2** proto-layout harness — cheapest, attacks the root cause directly
2. **C1** deploy gate — closes the costliest incident class (prod outage)
3. **B1** seed fix — S effort, kills an active flake (needs your `?seed=`-in-prod call)
4. **B2** fixture generator — S, unblocks B3/B4
5. **B3** layout-invariant e2e — automates detection of the defect class that shipped
6. **A1** design sign-off gate — blocks the attempt-2/-3 pattern structurally
7. **C2** park-before-toss — preserves rejected work
8. **A3** feasibility guard upgrade — small diff on an existing toothless hook
9. **A4** AC-descope drift — extends existing tooling, verified against real drift
10. **C3** plan-staleness scan — advisory, cheap
11. **B4** visual regression — highest ongoing maintenance; land last, after B3 proves stable

**Shared-tooling note:** A1, C1, C2, C3, A4 belong in claude-env (source of truth) per repo rules; new hooks need `tooling-manifest.json` entries (`manifest_completeness_guard.py` blocks otherwise). A2, A3, B1–B4 are photo-portfolio-local.

**STATUS: PROPOSALS ONLY — nothing implemented. Awaiting Patrick's selection.**
