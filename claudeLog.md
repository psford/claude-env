# Claude Terminal Log

Summary log of terminal actions and outcomes. Full history archived in `archive/claudeLog_*.md`.

---

## 01/22/2026

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
