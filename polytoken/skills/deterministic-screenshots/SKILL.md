---
name: deterministic-screenshots
description: How to take and compare Playwright screenshots that don't flake — pinned contexts, animated-camera readiness, raster-jitter tolerance, and the debug checklist that replaces guessing.
---

# Deterministic Playwright screenshots

Screenshots flake for a small number of KNOWN physical reasons. Follow this
procedure and taking a screenshot is never a guessing game. Ground truth:
road-trip `tests/playwright-layout/` (helpers + README, 2026-10-05 — ~2h was
lost there ONCE; the fixes below are all in-tree, copy them, don't rederive).

## Before you capture — three rules

1. **Pin the context.** Project device options (UA, touch, DPR) leak into
   `browser.newContext()`. In any context meant to be reproducible, set ALL
   of: `userAgent` (explicit string, byte-identical across capture + compare
   code), `deviceScaleFactor: 1`, `hasTouch: false`, `isMobile: false`.
   Also: Playwright WebKit's default UA is Macintosh-Safari-shaped — page
   code sniffing for iOS (`platform==='MacIntel' && maxTouchPoints>1`) can
   match it and inject different DOM.
2. **Never gate readiness on a timer if anything animates.** Maps are the
   classic: MapLibre `fitBounds`/`jumpTo` fly (zoom dips then climbs,
   ~0.5–1s). A `waitForTimeout` grabs a mid-flight frame whose phase shifts
   whenever load timing shifts. Instead: wait for the flight to START
   (`isMoving()` with a cap — pages without flights skip through), then
   wait for SETTLE (`!isMoving()`), then `document.fonts.ready`.
3. **Decide determinism BEFORE the first flake.** Run the capture twice and
   byte-diff. If it differs with identical code, you have raster jitter —
   go straight to the tolerance compare, don't chase "the bug".

## Comparing

- **DOM snapshot first, pixels second.** Serialize body (tag + id + class +
  data-attrs, text collapsed) and compare structurally; allow-list
  intentional diffs explicitly (e.g. loading scripts, mount points).
- **Never byte-compare screenshots.** WebKit AA-jitters fractionally
  positioned SVG by ±1–2 units; WebGL canvas line rasterization jitters
  more (MSAA sample patterns). Decode both PNGs and allow a bounded pixel
  budget — e.g. ≤512 px beyond Δ12 per channel. A real regression moves
  thousands of pixels; jitter moves dozens-to-hundreds. Dependency-free
  decoder pattern: `tests/playwright-layout/helpers/png-diff.js`
  (zlib + unfilter, ~80 lines).

## Debug checklist (in order — no guessing)

1. Is the DOM snapshot clean but only PNGs differ? → raster jitter or
   canvas; run the bounded diff and read `changed`/`maxDelta`.
2. Localize FIRST: decode both images in-page (`Image` + `OffscreenCanvas`
   `getImageData`), compute the diff bounding box + changed-pixel count.
   The box tells you WHICH element; sample colors in the box to identify it.
3. Diff the element geometry, not the page: dump `[class, x, y, w, h]` for
   elements intersecting the box, twice. Identical geometry + differing
   pixels = rasterizer; differing geometry = your readiness gate is letting
   an animation/camera flight through (rule 2).
4. Instrument the suspect API through `addInitScript` (monkey-patch
   `fitBounds`/`resize`/etc., log args + container size + timestamps) and
   compare two runs. Divergent call SEQUENCES with identical inputs means
   timing races; divergent inputs means a real regression.

## Baseline discipline

- Baselines are committed artifacts; a fresh checkout must reproduce them.
- Re-capture ONLY for intentional visual changes, in the same commit as the
  change, with a one-line note in the project's design log.
- Record the browser + version next to the baselines; re-capture when it
  revs.
