# SDLC Retrospective: Map POI Feature

**Date:** 2026-04-03
**Status:** FINDINGS COMPLETE — mitigations proposed, not yet implemented
**Scope:** 22 commits, 6 implementation phases, 3 external API integrations, 175 tests

---

## What Went Well

- Phased implementation plan with 21 acceptance criteria, clear task markers, and test-requirements.md mapping automated vs manual verification
- Code review caught real bugs: XSS single-quote escape gap, coordinate truthiness (0 treated as falsy), NPS double-fetch, race condition in pin-drop map center, duplicate UpsertPoiAsync logic
- Strong feature-to-rework ratio: 77% feature commits, 20% review fixes
- Test suite grew from 125 to 175 tests with proper WebApplicationFactory integration tests
- Commit message quality: every fix commit included criticality level, root cause, line numbers, and verification evidence

## What Went Poorly

### Theme 1: External Dependencies Never Verified (HIGHEST IMPACT)

- All 3 importers (NPS API, Overpass API, PAD-US GeoJSON) built entirely against mocked HTTP responses. Mock response formats invented from documentation — never validated against real APIs.
- NPS API key required but never obtained. Patrick doesn't have one.
- Implementation plan had zero steps for "verify real API connectivity" across all 6 phases
- Offered "Push and create PR" as the first option after automated tests passed, before any manual testing

### Theme 2: Mock/Test Quality Gaps

- Mock HTTP handlers only return 200 OK — no 429/401/503/timeout testing
- Silent failure when NPS_API_KEY missing — returns sentinel value with no visible error
- No end-to-end test that seeds via importers then queries via /api/poi
- PAD-US tests use synthetic rectangles, not real complex MultiPolygon geometries
- SQLite in-memory tests mask SQL Server behavioral differences

### Theme 3: Process Failures

- 12 of 21 ACs require human verification — none verified before completion declared
- Code review catching issues that should be structurally prevented (XSS, truthiness, null-checks)
- Initial endpoint tests used in-memory EF Core with inline LINQ — required complete rewrite

## Proposed Mitigations (15 items)

### Category 1: Automated Prevention (Hooks — claude-env)

1. **External API Smoke Test Guard** (`external_api_smoke_guard.py`) — blocks push when importer files reference external APIs but no SmokeTests.cs exists
2. **Plan External Dependency Guard** (`plan_external_dep_guard.py`) — blocks push when implementation plans have unchecked External Dependencies checkboxes
3. **PR Creation Test Gate** (`pr_creation_test_gate.py`) — blocks `gh pr create` when branch touches external APIs and no test verification JSON exists
4. **JS Coordinate Truthiness Guard** (`js_coordinate_truthiness_guard.py`) — blocks commit when JS uses truthiness checks on lat/lng variables
5. **JS XSS onclick Guard** (`js_xss_onclick_guard.py`) — blocks commit when escaped values interpolated into single-quoted onclick attributes

### Category 2: Automated Detection (Tests — road-trip)

6. **Smoke tests** for NPS, Overpass, PAD-US — opt-in via RUN_SMOKE_TESTS=1, hit real APIs
7. **API response contract fixtures** — checked-in real API response, test importer against verbatim fixture
8. **HTTP error response tests** — parameterized tests for 429/401/503/timeout
9. **End-to-end import-to-API test** — importer → DB → /api/poi endpoint verification
10. **Real PAD-US MultiPolygon fixture** — realistic geometry for centroid validation

### Category 3: Code Guards (road-trip)

11. **Seeder dry-run mode** (`--dry-run`) — validates credentials and connectivity without writing data
12. **Fail-fast on missing NPS_API_KEY** — replace silent skip with error + exit 1

### Category 4: Tooling/Templates (claude-env)

13. **Implementation plan template** with mandatory External Dependencies section
14. **Design plan external deps template** with verification commands and response shape paste areas
15. **Manual test coverage advisory** — PostToolUse hook reporting manual test step counts on push

### Priority Order

| # | Mitigation | Impact | Effort | Location |
|---|-----------|--------|--------|----------|
| 1 | Fail-fast on missing NPS_API_KEY | Prevents silent empty imports | S | road-trip |
| 2 | Seeder --dry-run mode | Validates all deps before real run | S | road-trip |
| 3 | PR creation test gate hook | Blocks premature PRs | S | claude-env |
| 4 | Implementation plan template | Prevents planning without verification | S | claude-env |
| 5 | Coordinate truthiness guard | Prevents class of JS bugs | S | claude-env |
| 6 | External API smoke guard hook | Blocks push without smoke tests | M | claude-env |
| 7 | API response contract fixtures | Catches mock/reality drift | M | road-trip |
| 8 | HTTP error response tests | Catches silent error swallowing | M | road-trip |
| 9 | NPS/Overpass/PAD-US smoke tests | Proves real APIs work | M | road-trip |
| 10 | End-to-end import-to-API test | Catches seeder→API mismatches | M | road-trip |
| 11 | XSS onclick guard | Prevents XSS class of bugs | S | claude-env |
| 12 | Plan external dep guard hook | Blocks plans with unchecked deps | S | claude-env |
| 13 | Real PAD-US geometry fixture | Catches centroid bugs on real data | S | road-trip |
| 14 | Manual test coverage advisory | Makes test gaps visible on push | S | claude-env |
| 15 | SQL Server compatibility tests | Catches SQLite/SQL Server drift | L | road-trip |

## Implementation Details

Full implementation-ready code for each mitigation was generated by research agents during this retrospective session. The code proposals are available in the conversation context and should be referenced when implementing these mitigations.

## Key Principle Established

**Design by contract for external APIs:** The contract is that the API returns data. If it doesn't — because credentials are missing, the endpoint is wrong, the response format doesn't match — the design is invalid. API keys must be secured and connectivity proven BEFORE writing implementation plans, not after.
