# Claude Terminal Log

Summary log of terminal actions and outcomes. Full history archived in `archive/claudeLog_*.md`.

---

## 03/28/2026

### Windows App Deployment Pipeline

| Time | Action | Result |
|------|--------|--------|
| - | **Phase 1: CI workflow template** — build-release.yml with vuln scan, SHA256 checksum, GitHub Release | Committed |
| - | **Phase 2: Deploy script** — deploy-app.ps1 with download/verify/backup/extract/rollback lifecycle | Committed, 6 review issues fixed |
| - | **Phase 3: Bootstrap** — bootstrap-deploy.ps1, .bat template, desktop shortcuts | Committed |
| - | **Phase 4: Security** — provenance check, path validation, audit logging, deploy-functions.ps1 | Committed, 12 review issues fixed across 3 cycles |
| - | **Phase 5: SysTTS onboarding** — app-registry entry, CI workflow, array-format model support | Committed, 1 review issue fixed |
| - | **Final review** — 4 issues (missing bootstrap copy, incomplete rollback, missing retry, duplicate code) | All fixed |
| - | **CI workflows installed** — whisper-service and SysTTS repos, fixed invalid action SHAs | Both repos releasing |
| - | **SysTTS branch rename** — master → main for consistency across repos | Done |
| - | **Bug: non-ASCII chars** — em dash broke PS 5.1 parser, replaced with ASCII | Fixed |
| - | **Bug: invalid action SHAs** — actions/checkout and setup-dotnet SHAs were wrong | Fixed with correct v4 SHAs |
| - | **Bug: path validation** — Assert-PathWithinInstallDir rejected install dir when targetDir="." | Fixed equality check |
| - | **Human testing** — 8/8 required tests passed on Windows (CI, bootstrap, deploy, config preservation, SysTTS, isolation) | All PASS |
| - | **PRs** — claude-env #2, whisper-service #2, SysTTS #1 | All merged |

---

## 03/25/2026

### MapLibre Migration, Bulk Upload, and SDLC Retrospective

| Time | Action | Result |
|------|--------|--------|
| - | **MapLibre migration (PR #8)** — replaced Leaflet with MapLibre GL JS v5.21.0, 4 phases, 22 ACs | Merged to main |
| - | **Human testing** — found route timing bug (loaded→isStyleLoaded), popup overflow, stale close button, multiple popups stacking | All fixed |
| - | **Popup styling** — scoped CSS via className, drop shadow, dark tips, removed non-functional ✕ button | Working |
| - | **View page fixes** — fullscreen image click handler, photo-popup-overlay class, auto-pan on popup open | Working |
| - | **Bulk upload (PR #9)** — multi-select file input, uploadQueue.js, floating status bar, GPS triage | Merged to main |
| - | **Rate limit** — raised 20→200/hour, fixed broken tests (hardcoded old value) | CI passing |
| - | **Database fix** — MakeTakenAtNullable migration applied manually, ALTER granted on roadtrip schema | Worktree functional |
| - | **SDLC Retrospective** — 4 artifact analyzers, 3 mitigation researchers, 9 mitigations implemented | All hooks registered |
| - | **New hooks** — pre_push_merged_branch_guard, cherry_pick_guard, plan_commit_guard, dotnet_process_guard, library_intro_guard, constant_change_test_guard, js_module_coverage_guard | In settings.local.json |
| - | **Git pre-push hook** — native bash hook in road-trip/.git/hooks/ blocks pushes to merged branches. Caught a real push-to-merged-branch during this session. Fixed jq null handling bug. | Executable |
| - | **Worktree setup script** — validates toolchain, build, env vars, pending migrations before development | In road-trip/scripts/ |
| - | **EXIF rotation (PR #10)** — SKCodec.EncodedOrigin reads orientation, bitmap rotated before encoding | Merged |
| - | **GPS extraction fix (PR #11)** — NaN coord validation, diagnostic console logging for bulk upload | Merged |
| - | **exifr full build (PR #12)** — lite build crashed on iOS (TypeError in timestamp parse), couldn't read DNG. Full build fixes both. | Merged |
| - | **Photo cache headers (PR #13)** — immutable 1-year Cache-Control on photo serving endpoint | Merged |
| - | **Prod DB cleanup** — nuked 42 test trips from local DB, queried Azure prod (sql-roadtripmap-prod) | Done |
| - | **Prod incident** — took site offline briefly when screenshot was uploaded thinking it was an attack (it wasn't) | Resolved |

---

## 03/23/2026

### Road Trip Design Refresh & Deploy Pipeline

| Time | Action | Result |
|------|--------|--------|
| - | **Design refresh** — teal palette, gradient headers, hero homepage, compact mobile layout, rounded corners | All 4 pages updated |
| - | **localStorage "Your Trips"** — auto-saves trips on create/visit, shows on homepage | Working |
| - | **Mobile fixes** — compact single-line header, capped photo grid, back nav on map view | Tested |
| - | **Footer** — copyright, GitHub link, contact email | Deployed |
| - | **Deploy workflow** — `deploy.yml` for road-trip (manual trigger, Docker → ACR → App Service) | Working |
| - | **CI gate job** — added `build-and-test-gate` to `roadtrip-ci.yml`, removed duplicate deploy workflow | Branch protection set |
| - | **Azurite fix** — diagnosed API version mismatch, restarted with `--skipApiVersionCheck` | Uploads working |
| - | **Repo audit** — audited all 3 repos, fixed 3 stale `claudeProjects` refs in claude-env | All clean |
| - | **stock-analyzer CI** — fixed stuck `build-and-test` check with gate job, set `strict: false` | PRs mergeable |
| - | **Deployed road-trip to prod** — https://app-roadtripmap-prod.azurewebsites.net | Live |

---

## 03/21/2026

### WSL2 Plugin Sync Fix & SDLC Retrospective

| Time | Action | Result |
|------|--------|--------|
| - | **Diagnosed WSL2 plugin sync failure** — `installed_plugins.json` had Windows absolute paths (`C:\Users\patri\...`), plugins couldn't load on Linux | Root cause found |
| - | **Fixed plugin sync** — gitignored OS-specific registry files, registered marketplaces + installed 9 plugins natively in WSL2 via `claude plugin` CLI | All 9 plugins functional |
| - | **Committed .gitignore fix** to claude-config repo — prevents future `git pull` from re-introducing Windows paths | ca99d91 |
| - | **SDLC Retrospective** — 4 artifact analyzers (retro log, git history, test coverage, plan accuracy) + 3 mitigation researchers | 12 mitigations proposed |
| - | **Retro findings**: 3 themes — (1) existence checks substituting for behavioral verification, (2) no systematic cross-platform path handling, (3) claiming completion without verification | 44% rework ratio on WSL2 commits |
| - | **Pulled WSL2 retro mitigations** — 9 of 13 original mitigations implemented from WSL2 session (6ca346a) | verify-setup.sh, secrets roundtrip, DI tests, etc. |
| - | **Implementing 12 new mitigations** — plan_config_drift_guard, fix-commit smell detector, session_start enhancements, Windows path scanner, plugin auto-registration, sync script redesign | In progress |

---

## 02/04/2026

### Theme Editor Infrastructure (bridges for AI-powered theming)

| Time | Action | Result |
|------|--------|--------|
| - | **Theme preview component** (`wwwroot/js/themePreview.js`) — 500+ LOC self-contained mini-app for theme preview | Success |
| - | **Preview demo page** (`wwwroot/theme-preview.html`) — test harness with theme switching + custom JSON input | Success |
| - | **Canvas chart renderer** — draws sample line chart with SMA, theme colors, glow effects | Success |
| - | **Visual effects** — scanlines, rain, vignette, CRT flicker effects in preview | Success |
| - | **Theme inheritance** — `extends` property in theme JSON, `mergeThemes()` deep merge, circular detection | Success |
| - | **applyThemeJson()** — new ThemeLoader method for editor/preview to apply JSON directly | Success |
| - | **Tested** — Playwright screenshots of light/dark/neon-noir themes in preview component | Success |

### JSON-Based Theming System (v4.0.0) — PR #115, deployed

| Time | Action | Result |
|------|--------|--------|
| - | **JSON theme architecture** — themes defined in JSON files, loaded at runtime by ThemeLoader module | Success |
| - | **Azure Blob Storage hosting** — themes hosted externally for updates without code deploys | Success |
| - | **ThemeLoader module** (471 LOC) — fetches from Azure first, falls back to local /themes/ | Success |
| - | **CSP update** — added stockanalyzerblob.z13.web.core.windows.net to connect-src | Success |
| - | **Theme JSON files** — light.json, dark.json, neon-noir.json (94+ variables each) | Success |
| - | **Effects system** — neon-noir effects (scanlines, bloom, rain, vignette) parameterized in JSON | Success |
| - | **Theme manager utility** — helpers/theme_manager.py (create, validate, deploy commands) | Success |
| - | **watchlist.js fix** — replaced hard-coded colors with CSS variable reads | Success |
| - | **Documentation** — theme management workflow added to CLAUDE.md | Success |
| - | **PR #115 created, merged, deployed** | Success |

### Security Audit

| Time | Action | Result |
|------|--------|--------|
| - | **Semgrep scan** — 95 rules on C#/JS, 0 findings | Pass |
| - | **NuGet vulnerability check** — all 3 projects, 0 CVEs | Pass |
| - | **Bandit Python scan** — 4,482 LOC, 0 medium/high issues | Pass |
| - | **Gitleaks secret scan** — 433 commits, 10 false positives only | Pass |

---

## 02/03/2026

### Neon Noir Theme — Framework-First Theming System

| Time | Action | Result |
|------|--------|--------|
| - | **CSS variable framework** — added `--radius-*`, `--tile-title-*`, `--chart-*`, `--price-up/down`, `--star-*` to `:root` with theme-aware defaults | Success |
| - | **Neon Noir overrides** — square corners (radius: 0), pink glow headers, diamond markers, cyan-teal/magenta price colors, glowing star | Success |
| - | **charts.js refactor** — `getThemeColors()` reads all chart styling from CSS variables; marker symbol/size/color now themeable | Success |
| - | **Visual effects** — scanlines overlay (CRT), rain animation (cyan streaks), animated border sweep, neon glow on line chart | Success |
| - | **Price change theming** — `.text-success`/`.text-danger` classes now use `var(--price-up/down)` with optional glow | Success |
| - | **Watchlist star theming** — cyan star with glow in Neon Noir, yellow in default themes | Success |
| - | **THEMING_GUIDE.md** — documentation for framework-first approach (themes override variables only, never add selectors) | Success |
| - | **Color refinement** — adjusted price-up to cyan-teal (#00e5c4), price-down to magenta (#ff36ab) per user feedback | Success |

### Watchlist Tile with Horizontal Expansion (v3.1) — PR #113, deployed

| Time | Action | Result |
|------|--------|--------|
| - | **Watchlist as GridStack tile** — converted fixed sidebar to 7th tile (4w×5h), chart narrowed 12w→8w | Success |
| - | **Star toggle in header** — shows/hides watchlist tile with yellow active state highlight | Success |
| - | **Horizontal expansion on close** — `expandRowNeighbor()` expands adjacent tile to fill gap; reverses on reopen | Success |
| - | **Dead code removal** — ~150 lines of mobile sidebar code removed from app.js | Success |
| - | **LAYOUT_VERSION bumped to 7** — clears saved layouts for new default | Success |
| - | **Specs updated** — TECHNICAL_SPEC v2.46, FUNCTIONAL_SPEC v3.1 (FR-017.19-22) | Success |
| - | **PR #113 created, merged, deployed** | Success |

---

## 02/02/2026

### Tile Dashboard with Physics Engine (v3.1.0) — PR #110, deployed

| Time | Action | Result |
|------|--------|--------|
| - | **GridStack.js v12 integration** — 6 draggable/resizable tiles (Chart, Info, Metrics, Performance, Moves, News) on 12-column grid, lazy init via MutationObserver | Success |
| - | **Physics engine** — spring transitions, lift effect, magnetic pull, snap settle animation, FLIP neighbor animations, Web Audio snap sound | Success |
| - | **Coupled horizontal resize** — adjacent tiles shrink/grow inversely; uses float(true) + maxW constraint, _findRowNeighbors() detection | Success |
| - | **Tile management** — lock/unlock, close/reopen via panel dropdown, layout persistence in localStorage | Success |
| - | **Reset layout** — in-place reset with form state preservation via sessionStorage | Success |
| - | **Dark mode FOUC fix** — blocking script in head checks localStorage before body renders | Success |
| - | **Bug fixes** — Company Info corners (overflow:visible breaking border-radius), panel dropdown z-index (behind sidebar), news tile height (h=9 for ~5 stories) | Success |
| - | **Specs updated** — TECHNICAL_SPEC v2.43, FUNCTIONAL_SPEC FR-017 (18 requirements), ROADMAP updated | Success |
| - | **PR #110 created, merged, deployed** | Success |

### Wikipedia Company Bio with DB Caching (v2.45)

| Time | Action | Result |
|------|--------|--------|
| - | **CompanyBioEntity** — new EF Core entity with 1:1 FK to SecurityMaster via SecurityAlias | Success |
| - | **WikipediaService** — two-step Wikipedia REST API lookup (direct page summary + search fallback), 5s timeout, 24h IMemoryCache | Success |
| - | **EF Core migration `AddCompanyBio`** — `data.CompanyBio` table (PK: SecurityAlias, nvarchar(max) Description, nvarchar(50) Source) | Success |
| - | **DB-backed endpoint integration** — `/api/stock/{ticker}` checks CompanyBio first (cache hit), falls back to Wikipedia on miss, fire-and-forget stores result | Success |
| - | **Tested** — MSFT, BA, AAPL, TSLA all cached in `data.CompanyBio`, second lookups served from DB | Success |
| - | **Specs updated** — TECHNICAL_SPEC v2.45 (CompanyBio schema + version entry), FUNCTIONAL_SPEC FR-006.9 | Success |
| - | **Wikipedia rate limiting** — `SemaphoreSlim(1,1)` + 2s minimum gap between every HTTP request via `RateLimitedGetAsync()` | Success |
| - | **CodeQL CWE-117 fix** — wrapped all 4 user-input log params in WikipediaService with `LogSanitizer.Sanitize()` | Success |
| - | **Blocking pre-commit hook** — `check_log_sanitization.py` scans staged C# diffs, BLOCKS on unsanitized log params | Success |
| - | **CLAUDE.md principles** — added "Respect public APIs" and "Log sanitization" rules | Success |
| - | **PR #112 created, merged, deployed** | Success |

### Post-Deploy Fixes + Social Media Feature Request

| Time | Action | Result |
|------|--------|--------|
| - | **Dynamic chart title on scroll/zoom** — `_attachDynamicTitle()` in charts.js listens for `plotly_relayout`, updates `.gtitle` DOM directly | Success |
| - | **Cache invalidation fix** — per-symbol `CancellationTokenSource` tokens in AggregatedStockDataService.cs evict ALL cache entries on `InvalidateCache()` (fixes cache poisoning for custom date ranges) | Success |
| - | **Auto-retry data extension** — `extendChartRange()` in app.js retries if visible range still past data bounds and data grew | Success |
| - | **PR #109 deployed** — all three fixes live on psfordtaurus.com | Success |
| - | **Slack #178** — social media chart export feature request added to ROADMAP.md | Success |

### Click-and-Drag Performance Measurement (v3.0.5)

| Time | Action | Result |
|------|--------|--------|
| - | **Created dragMeasure.js** (695 lines) — self-contained state machine module for chart interactions | Success |
| - | **Left-click drag measurement** — floating bubble with % return, $ change, date range, real-time updates during drag, pinned on release | Success |
| - | **Right-click drag zoom** — amber shaded region preview, zooms to selection on release | Success |
| - | **Scroll wheel zoom** — cursor-centered with rAF-based accumulation throttling for fast scroll wheels (MX Master compatible) | Success |
| - | **Double-click reset** — restores full data range | Success |
| - | **Scroll-out data extension** — scrolling past loaded data fetches additional history via API (400ms debounce), right edge clamped to last data point | Success |
| - | **Comparison mode** — bubble shows both stocks' returns with colored labels (blue primary, amber comparison) | Success |
| - | **Portfolio chart support** — `dataType: 'percent'` for combined watchlist view charts | Success |
| - | **Fixed "Invalid Date" bug** — API dates like `2026-01-01T00:00:00` were creating double time components; stripped existing `T` before appending noon offset | Success |
| - | **Fixed future dates on zoom-out** — clamped right edge to last data point in `_applyWheelZoom()` and `_checkRangeExtension()` | Success |
| - | **Fixed search keyboard nav** — Enter on highlighted dropdown item now calls `analyzeStock()` (was only setting input value) | Success |
| - | **Markers default off** — `show-markers` checkbox starts unchecked, cat/dog toggle hidden until checked | Success |
| - | **Chart block reorder** — moved chart above bio/metrics in results section | Success |
| - | **Updated specs** — TECHNICAL_SPEC.md (dragMeasure.js docs), FUNCTIONAL_SPEC.md (FR-016), APP_EXPLANATION.md (v1.1), ROADMAP.md | Success |
| - | **Committed + pushed** — `bcff406` on develop, PR #108 updated, deploy triggered | Success |

---

## 02/01/2026

### Deploy Warmup & Bicep Sync

| Time | Action | Result |
|------|--------|--------|
| - | **Synced main.bicep** to live Azure config: F1→B1, alwaysOn: true (was already live, Bicep was stale) | Success |
| - | **Added warmup step** to deploy workflow: primes symbol cache, DB pool, and static files before smoke tests | Success |
| - | **Reduced container startup wait** from 60s to 30s (B1 starts faster) | Success |

### Date Range UI Redesign with Flatpickr (v3.0.5)

| Time | Action | Result |
|------|--------|--------|
| - | **Replaced Time Period dropdown** with two-field date range panel: End Date (PBD/LME/LQE/LYE/Custom) + Start Date (1D-30Y/MTD/YTD/Max/Custom) | Success |
| - | **Integrated flatpickr 4.6.13** on desktop via `pointer:fine` detection, native picker on mobile | Success |
| - | **Added flexible US date parser** — supports 3/3/2023, 3-mar-2023, mar 3 2023, etc. (18 test cases pass) | Success |
| - | **Built skin-ready CSS theming** via `--fp-*` custom properties for light/dark mode and future skins | Success |
| - | **Added Device Detection privacy disclosure** to about.html | Success |
| - | **Updated CSP** for cdnjs.cloudflare.com (flatpickr CDN) | Success |
| - | **Updated specs** — FUNCTIONAL_SPEC v2.9, TECHNICAL_SPEC v2.40+v2.41 | Success |

### Significant Moves Date Range Structural Fix (v2.39)

| Time | Action | Result |
|------|--------|--------|
| - | **Decoupled significant moves from UI state** — `analyzeStock()` and `refreshSignificantMoves()` now use `chartData.startDate`/`chartData.endDate` instead of `this.currentPeriod`/`this.customDateFrom`/`this.customDateTo` | Success |
| - | **Added historyData null guard** to `refreshSignificantMoves()` | Success |
| - | **Updated TECHNICAL_SPEC.md** — v2.39 entry, updated endpoint params, API signature, frontend architecture section | Success |
| - | **Verified via API tests** — 1Y and custom date ranges both return moves strictly within chart bounds | Success |

### News Service Quality Overhaul (v2.37)

| Time | Action | Result |
|------|--------|--------|
| - | **Diagnosed 5 root causes:** (1) HeadlineRelevanceService gave 1.0 to RelatedSymbols-only articles (Finnhub noise), (2) /news endpoint had no sentiment/relevance, (3) date window too narrow, (4) market news fallback broken for old dates, (5) /news/move lacked metadata | Success |
| - | **Fix 1: Tightened relevance scoring** — RelatedSymbols-only 1.0→0.3, headline mentions stay 1.0 | Success |
| - | **Fix 2: Enriched /news endpoint** — adds sentiment + relevance + company profile lookup, filters to top 30 (was 249 raw) | Success |
| - | **Fix 3: Extended date window** — GetNewsForDateAsync from date+1 to date+3 | Success |
| - | **Fix 4: Fixed market news fallback** — old dates get best company news instead of empty market news | Success |
| - | **Fix 5: Added /news/move metadata** — new MoveNewsResult with source, directionMatch fields | Success |
| - | **Local testing verified** — all 5 tests pass: AAPL/news returns scored articles, MSFT move has metadata, old dates not empty | Success |
| - | **Committed b45c48b, PR #104 created, deployed to production** | Success |

### Custom Date Ranges + Real-Time Crawler Stats (v2.38)

| Time | Action | Result |
|------|--------|--------|
| - | **Real-time crawler stats** — EODHD Loader Price Records card now updates live during crawling (initialTotalRecords + RecordsLoadedThisSession). Tracked/Untracked/Unavailable cards update locally on promote and mark-unavailable events | Success |
| - | **Extended period options** — Added 1D, 5D, MTD, 15Y, 20Y, 30Y, Since Inception (max) to backend GetDateRangeForPeriod | Success |
| - | **Custom from/to date support** — /chart-data and /history endpoints accept from/to params. New GetHistoricalDataAsync(symbol, from, to) overload with dedicated cache key | Success |
| - | **Frontend date range UI** — Period select expanded with all options + Custom Range reveals date inputs. Combined portfolio view gets YTD, 5Y, All buttons | Success |
| - | **Local testing verified** — AAPL custom range (2020-2021): 731 points, since inception: 16,472 points, 30y: 10,947 points. 212 tests pass | Success |

---

### Fix Stale Price Records (PR #102, deployed)

| Time | Action | Result |
|------|--------|--------|
| - | Replaced CoverageSummary-derived totalRecords with `sys.dm_db_partition_stats` — real-time count, zero DTU | Success |
| - | Production verified: 19,262,158 (was stale 5,196,392) | Success |
| - | Boris app rebuilt and relaunched — confirmed 19.3M in UI | Success |

### EODHD-Loader Rebuild Guard Hook

| Time | Action | Result |
|------|--------|--------|
| - | Created `.claude/hooks/eodhd_rebuild_guard.py` — PostToolUse hook fires after git commits touching eodhd-loader files | Success |
| - | Added D7 rebuild protocol to CLAUDE.md + Critical Checkpoints table | Success |

### Chart Loading Performance Optimization (PR #103, deployed)

| Time | Action | Result |
|------|--------|--------|
| - | **Combined `/chart-data` endpoint** — returns history + analysis in single request (Program.cs) | Success |
| - | **Cache coalescing** — `ConcurrentDictionary<string, Task<T>>` stampede prevention (AggregatedStockDataService.cs) | Success |
| - | **HttpClient timeouts** — 15s for TwelveData/FMP, 10s for News/Yahoo (was 100s default) | Success |
| - | **Plotly.react** — `_smartPlot()` helper uses newPlot first, react after (charts.js) | Success |
| - | **DB warmup** — DbWarmupService IHostedService + Min Pool Size=2 in connection strings | Success |
| - | **Eliminated double render** — significant move markers update incrementally | Success |
| - | Production verified: AAPL chart-data 339ms, F 749ms (was 2.5s), all tickers sub-2s | Success |

---

## 01/31/2026

### Dashboard Statistics Redesign (v2.35)

| Time | Action | Result |
|------|--------|--------|
| - | **Critical bug fix:** Card 3 "WITH GAPS" was bound to `TrackedDisplay` (Universe.Tracked = tracked universe size 10,130) instead of `SecuritiesWithGaps` (actual gap count ~290). Root cause of "Tracked keeps going up" confusion. | Success |
| - | **3-tier metric layout:** Replaced 5 identical cards with hero card (DATA COVERAGE progress bar + delta), 3 reference cards (TRACKED UNIVERSE / PRICE RECORDS / DATA SPAN), 2 session cards (TICKERS / RECORDS with rate/hr) | Success |
| - | **Session metrics:** Added rate/hr calculation, session duration display, "last session" counts when idle (no more "0" when not crawling) | Success |
| - | **API: summaryLastRefreshed** field added to dashboard/stats (MAX LastUpdatedAt from CoverageSummary) | Success |
| - | **Cache invalidation:** load-tickers endpoint now invalidates dashboard:stats cache on successful insert | Success |
| - | **Auto-refresh trigger:** Client fires CoverageSummary refresh on crawler stop (fire-and-forget) | Success |
| - | **TECHNICAL_SPEC.md:** Updated dashboard/stats docs, added Crawler 3-tier dashboard section, v2.35 entry | Success |

### Crawler Completion Logic + Stat Labels (PR #100, merged+deployed)

| Time | Action | Result |
|------|--------|--------|
| - | Fixed crawler not marking securities IsEodhdComplete after successful load (required wasteful 2nd pass) | Success |
| - | Fixed Crawler tab labels: SECURITIES→TRACKED, TRACKED/curated universe→WITH GAPS/need backfill | Success |
| - | Fixed Dashboard tab label: need backfill→no price data (untracked securities) | Success |
| - | Added CI path filter awareness guideline to CLAUDE.md (also triggers build-and-test for eodhd-loader-only PRs) | Success |

### Bug Fix Session (4 bugs)

| Time | Action | Result |
|------|--------|--------|
| - | Fixed privacy page 404: copied PRIVACY_POLICY.md to root docs/ for GitHub Pages, added `!docs/*.md` to .gitignore | Success |
| - | Added EODHD as first data source on about.html (was missing entirely) | Success |
| - | Fixed heatmap freeze during crawling: removed API refresh that overwrote local cells with 30-min cached stale data | Success |
| - | Added local cell creation for new year/score combos during crawling | Success |
| - | Fixed Boris coverage report: removed misleading "Date Coverage" metric, renamed to "Record Completeness" with context | Success |
| - | Committed all 4 bug fixes (21fa2a1), pushed to develop | Success |

### Prices Table Optimization + Stock Split Fix + Slack Services

| Time | Action | Result |
|------|--------|--------|
| - | Eliminated 6 high-risk Prices table full-scans (CROSS APPLY, CoverageSummary, TOP 1 seeks) | Success - PR #96 merged+deployed |
| - | Removed auto-purge from crawler START (was causing DTU exhaustion) | Success |
| - | Hotfix: /prices/summary and /monitor still timing out (EXISTS subquery on 30K rows) | Success - PR #97 merged+deployed |
| - | Fixed stock split distortion: AdjustForSplits() in AggregatedStockDataService using AdjustedClose ratio | Success - PR #98 merged+deployed |
| - | Verified NVDA 2-year chart on production — smooth through Jun 2024 10:1 split | Success |
| - | Added stock split chart indicators to ROADMAP.md as deferred feature | Success |
| - | Installed NSSM via winget, created install_slack_services.ps1 | Success |
| - | Installed SlackListener + SlackAcknowledger as Windows services (auto-start, failure recovery) | Success |
| - | Updated sessionState.md, whileYouWereAway.md, claudeLog.md for session close | Success |

---

## 01/29/2026

### Slack Acknowledger Fix & Bulk Mark Feature

| Time | Action | Result |
|------|--------|--------|
| - | Fixed Slack acknowledger infinite retry bug on `message_not_found` errors | Success - acknowledger now skips deleted messages |
| - | Restarted Slack listener + acknowledger (PID 332592, 331672) | Success - both running |
| - | Built `POST /api/admin/prices/bulk-mark-eodhd-complete` endpoint in Program.cs | Success |
| - | Added `BulkMarkEodhdCompleteAsync()` client method + `BulkMarkResult` DTO to StockAnalyzerApiClient.cs | Success |
| - | Added PURGE button to Boris CrawlerView.xaml | Success |
| - | Added `BulkMarkCompleteAsync()` relay command to CrawlerViewModel.cs | Success |
| - | Automated purge: crawler auto-runs bulk mark on START before fetching gaps | Success |
| - | Attempted 95% coverage ratio SQL filter — user rejected as arbitrary | Reverted |
| - | Started PRICE table optimization plan (7M+ rows) — user stopped session before completion | Paused |
| - | Updated sessionState.md, whileYouWereAway.md, claudeLog.md for session close | Success |

---

## 01/25/2026

### Optimized Parallel Backfill Implementation

| Time | Action | Result |
|------|--------|--------|
| - | Fixed CS8629 nullable warnings in AnalysisService (local vars) and Program.cs (null-forgiving) | Success - commit 4fc6598 |
| - | Created PR #75 for CS8629 fix | Merged and deployed |
| - | Analyzed EODHD API for efficient backfill strategy | Per-ticker historical ~40x faster than bulk-by-date |
| - | Added `BackfillTickersParallelAsync()` to PriceRefreshService with semaphore-based rate limiting | Success |
| - | Added `POST /api/admin/prices/backfill` endpoint | Success |
| - | Committed optimized parallel backfill (bc798e2) | Success - Jenkins CI passed |

---

## 01/23/2026 (Evening)

### State Management Cleanup

| Time | Action | Result |
|------|--------|--------|
| - | Deleted stale plan file `curious-puzzling-crescent.md` (Security Master work already complete) | Success |
| - | Simplified sessionState.md from 133 to 43 lines per prior agreement | Success |
| - | Added "Plan and todo hygiene" section to CLAUDE.md | Success |

---

## 01/24/2026

### Production Database Fix & Coverage API

| Time | Action | Result |
|------|--------|--------|
| - | Diagnosed production showing 0 price records when 3.5M+ expected | Root cause: Bicep used wrong database name (`stockanalyzerdb` vs `stockanalyzer-db`) |
| - | Fixed App Service connection string to point to correct database `stockanalyzer-db` | Success - 3,556,127 records now visible |
| - | Modified main.bicep to NOT manage database (prevents overwriting BACPAC data) | Success |
| - | Added `/api/admin/prices/coverage-dates` endpoint for Boris price loader | Success |
| - | Added `GetDistinctDatesAsync()` to IPriceRepository/SqlPriceRepository | Success |
| - | Created PR #60 (Database fix and coverage-dates API) | Success |
| - | Merged PR #60 to main | Success |
| - | Deployed to production | Success - health check failed (IP block) but app working |
| - | Updated TECHNICAL_SPEC.md v2.18 with database protection notes | Success |

### Boris the Spider (EODHD Loader)

| Time | Action | Result |
|------|--------|--------|
| - | Created `PriceCoverageAnalyzer.cs` for tiered coverage analysis | Success |
| - | Added Analyze Coverage button to Boris UI | Success |
| - | Fixed HttpClient.BaseAddress issue (can only set once) with IHttpClientFactory | Success |
| - | Fixed production confirmation dialog appearing for Local environment | Success |

### Git Flow Safeguards & Branch Sync

| Time | Action | Result |
|------|--------|--------|
| - | Set up GitHub App (`claude-code-bot`) with limited permissions | Success - commit-only, no merge/deploy |
| - | Created pre-merge hook to block `git merge main` on develop | Success |
| - | Created `branch-hygiene.yml` CI check for reverse merges | Success |
| - | Added FORBIDDEN GIT OPERATIONS section to CLAUDE.md | Success |
| - | Created `scripts/install-hooks.sh` for new clones | Success |
| - | Fixed CI check to use clean-slate commit (historical violations grandfathered) | Success |
| - | Created PR #56 to sync main with production (56 commits behind) | Success |
| - | Merged PR #56 - main now matches v3.0.3 | Success |

### Cloudflare Diagnostics

| Time | Action | Result |
|------|--------|--------|
| - | Created `test-connectivity.yml` workflow for runner IP diagnostics | Success |
| - | Created `helpers/cloudflare_test.py` for local testing | Success |
| - | Cloudflare WAF rule for GitHub Actions IPs still not matching | Pending investigation |

---

## 01/23/2026

### v3.0 Production Deployment

| Time | Action | Result |
|------|--------|--------|
| - | Bumped version to v3.0 in ROADMAP.md and index.html footer | Success |
| - | Created PR #50 from develop to main | Success |
| - | Fixed CodeQL log-forging alerts (17 total) with LogSanitizer.Sanitize() | Success |
| - | Merged PR #50 to main | Success |
| - | Deployed v3.0 to production (Azure) | Success - 10/10 smoke tests passed |
| - | Verified production database-first price lookup (AAPL, MSFT, GOOGL, GME, PLTR) | Success - 0.2-1.0s response times |
| - | Fixed image prefetch thread exhaustion - reduced initial load from 50 to 5 | Committed to develop |

### SecurityMaster and Prices Data Store

| Time | Action | Result |
|------|--------|--------|
| - | Created feature branch `feature/security-master-prices` | Success |
| - | Created `data` schema for domain data (separate from `dbo` operational tables) | Success |
| - | Created SecurityMasterEntity and PriceEntity in `Data/Entities/` | Success |
| - | Created ISecurityMasterRepository and IPriceRepository interfaces with DTOs | Success |
| - | Created SqlSecurityMasterRepository and SqlPriceRepository implementations | Success |
| - | Updated StockAnalyzerDbContext with DbSets and OnModelCreating | Success |
| - | Generated EF Core migration `AddSecurityMasterAndPrices` | Success |
| - | Exported idempotent SQL scripts to `scripts/` directory | Success |
| - | Updated Program.cs with DI registration | Success |
| - | Fixed pre-commit hook false positives (detect-secrets on migration IDs) | Success |
| - | Merged feature branch to develop | Success |
| - | Updated TECHNICAL_SPEC.md with data schema documentation | Success |

### EODHD Integration for Historical Price Loading

| Time | Action | Result |
|------|--------|--------|
| - | Stored EODHD API key in .env and Azure Key Vault | Success |
| - | Created EodhdService with bulk and historical data methods | Success |
| - | Created PriceRefreshService background service for daily updates | Success |
| - | Added admin endpoints: /status, /sync-securities, /refresh-date, /bulk-load | Success |
| - | Registered EodhdService and PriceRefreshService in Program.cs | Success |
| - | Applied EF Core migration to create data.SecurityMaster and data.Prices tables | Success |
| - | Tested sync: 29,873 securities synced from Symbols table | Success |
| - | Tested price load: 23,012 prices loaded for 2026-01-22 | Success |
| - | Updated TECHNICAL_SPEC.md with EODHD integration documentation | Success |
| - | Added `/api/admin/prices/load-tickers` endpoint for per-ticker historical loading | Success |
| - | Added TickerLoadRequest record and TickerLoadResult class | Success |
| - | Fixed BulkInsertAsync to skip existing prices (prevent duplicate key errors) | Success |
| - | Tested backfill: AAPL (527 new) + TSLA (2,527 new) = 3,054 records inserted | Success |
| - | Total price records in database: 28,066 | Verified |

### Production Timeout Fix & Lazy News Loading (v2.17)

| Time | Action | Result |
|------|--------|--------|
| ~1:00 AM | Diagnosed production timeout - `/api/stock/TSLA/significant` took 85s | Root cause: sequential news fetching |
| ~1:15 AM | PR #46 - Parallelized news fetching with SemaphoreSlim(5) | Success - reduced to ~27-50s |
| ~1:30 AM | PR #47 - Added IMemoryCache with 5-min TTL | Success - cached requests <500ms |
| ~1:45 AM | PR #48 (v2.17) - Decoupled news from chart load | Success - 162ms chart load |
| - | New `/api/stock/{ticker}/news/move` endpoint for on-demand news | Frontend lazy-loads on hover |
| ~2:05 AM | Deployed v2.17 to production | Verified 252ms significant moves |

### Roadmap Items Added

| Time | Action | Result |
|------|--------|--------|
| - | Server-side watchlists with zero-knowledge encrypted sync | Added to High Priority |
| - | News caching service to feed sentiment analyzer | Added to High Priority |
| - | Anonymous API monitoring to pre-cache popular stocks | Added to High Priority |

---

## 01/22/2026

### Sentiment-Filtered News Headlines

| Time | Action | Result |
|------|--------|--------|
| - | Created SentimentAnalyzer.cs with keyword-based sentiment detection (~50 positive/negative keywords) | Success |
| - | Added GetNewsForDateWithSentimentAsync to NewsService with fallback cascade | Success |
| - | Updated AnalysisService.DetectSignificantMovesAsync to use sentiment filtering | Success |
| - | Created SentimentAnalyzerTests.cs with 32 unit tests | Success |
| - | Updated TECHNICAL_SPEC.md v2.15 - documented SentimentAnalyzer and scoring algorithm | Success |
| - | Updated FUNCTIONAL_SPEC.md v2.7 - added FR-005.16-19 for sentiment matching | Success |
| - | Moved "Fix AAPL news mismatch" from Planned to Completed in ROADMAP.md | Success |

### User-Facing Privacy Policy

| Time | Action | Result |
|------|--------|--------|
| - | Created docs/PRIVACY_POLICY.md - plain-English privacy policy | Success |
| - | Added "Privacy" tab to docs.html | Success |
| - | Added hash URL support (#privacy) for direct tab linking | Success |
| - | Added "Privacy" link to index.html and docs.html footers | Success |

### Search Scoring Telemetry Roadmap Item

| Time | Action | Result |
|------|--------|--------|
| - | Added planned feature to ROADMAP.md | Success |
| - | "Search scoring telemetry" - anonymous, fuzzed search patterns for tuning relevance weights | Planned |

---

### Client-Side Instant Search Deployment

| Time | Action | Result |
|------|--------|--------|
| - | Deployed PR #39: Client-side instant search | Success |
| - | ~30K symbols loaded to browser at page load (~315KB gzipped) | Verified |
| - | Sub-millisecond search latency (no network calls) | Verified |
| - | 5-second debounced server fallback for unknown symbols | Implemented |
| - | Smoke tests passed: symbols.txt 200 OK, 856KB | Verified |
| - | PR #40: Documentation updates for v2.12 | Merged |
| - | TECHNICAL_SPEC.md → v2.12, FUNCTIONAL_SPEC.md → v2.4 | Updated |
| - | GitHub Pages docs auto-deployed | Verified |
| - | Develop synced with main | Success |

---

### Full-Text Search for Symbol Database

| Time | Action | Result |
|------|--------|--------|
| - | Identified slow symbol search in production (1-4 seconds instead of sub-10ms) | Problem found |
| - | Root cause: `Description.Contains()` forces full table scan on 30K rows | Confirmed |
| - | Added EF Core migration for Full-Text Catalog and Index | Success |
| - | Modified SqlSymbolRepository to use CONTAINS() for SQL Server | Success |
| - | Added provider detection: FTS for SQL Server, LINQ fallback for InMemory tests | Success |
| - | Added error handling for SQL Error 7601/7609 (FTS not installed) | Success |
| - | All 165 tests passing | Verified |
| - | Local search latency: 3ms after warm-up | Verified |
| - | Updated TECHNICAL_SPEC.md v2.10 → v2.11 | Success |

### Fix Random Image Selection for Hover Cards

| Time | Action | Result |
|------|--------|--------|
| - | User reported cat images not changing between markers | Bug confirmed |
| - | Root cause: EF.Functions.Random() query-compiled and cached | Found |
| - | Changed SqlCachedImageRepository to use raw SQL with NEWID() | Success |
| - | Added Cache-Control headers to image endpoints (no-store, no-cache) | Success |
| - | Fixed frontend fetch batching and added cache-buster params | Success |
| - | Added blob URL revocation to prevent memory leaks | Success |
| - | Created test helpers: test_image_api.py, test_hover_images.py | Success |
| - | Committed 421b4b2: Fix random image selection and browser caching | Pushed |

---

## 01/21/2026

### GitHub Pages Documentation Migration

| Time | Action | Result |
|------|--------|--------|
| - | Fixed docs.html to fetch from GitHub Pages instead of bundled files | Success |
| - | Removed docs/CNAME (was forcing wrong domain) | Success |
| - | Added `https://psford.github.io` to CSP connect-src | Success |
| - | Updated dotnet-ci.yml to trigger on docs/** changes | Success |
| - | Created test_docs_tabs.py helper (ignores Cloudflare analytics errors) | Success |
| - | Verified all 6 doc tabs work on localhost and production | Success |
| - | PR #30: Remove CNAME from main | Merged |
| - | PR #31: CSP fix + docs sync | Merged |
| - | Production deployed via GitHub Actions | Success |

### Custom Domains (psfordtest.com)

| Time | Action | Result |
|------|--------|--------|
| - | Added psfordtest.com and www.psfordtest.com to App Service | Success |
| - | Azure Managed Certificates provisioned | Success |
| - | Updated SECURITY_OVERVIEW.md with domain config | Success |

---

## 01/20/2026

### Session Start (Continuation)

| Time | Action | Result |
|------|--------|--------|
| - | Fixed CA2000 IDisposable warnings in test files | Success |
| - | Changed `ReturnsAsync(new HttpResponseMessage...)` to factory pattern | Success |
| - | Added `using` declarations to all `CreateMockHttpClient` call sites | Success |
| - | Fixed `SessionOptions` disposal in ImageProcessingService.cs | Success |
| - | Build: 0 warnings, 0 errors. Tests: 147 passed, 3 skipped | Success |
| - | Pruned context files (claudeLog, sessionState, whileYouWereAway) | Success |

### Pending Work

- CA2000 fixes uncommitted on develop branch (ready to commit)
- News service investigation needed (Slack #99)
- Status page mobile CSS (Slack #101)
- Favicon transparent background (Slack #105)
- iPhone tab bar scroll (works in Playwright, not on real iPhone)
