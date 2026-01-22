# Claude Terminal Log

Summary log of terminal actions and outcomes. Full history archived in `archive/claudeLog_*.md`.

---

## 01/22/2026

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
