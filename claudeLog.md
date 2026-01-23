# Claude Terminal Log

Summary log of terminal actions and outcomes. Full history archived in `archive/claudeLog_*.md`.

---

## 01/23/2026

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
