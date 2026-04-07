# SDLC Retrospective Mitigations — Map POI Feature

**Date:** 2026-04-03
**Session:** Map POI implementation (22 commits, 6 phases)

<!-- area-tags: js-map, js-layer, js-cache, js-coord, js-xss, external-api, dotnet-test -->

## Status

1 of 15 mitigations implemented:
- [x] #1 API integration test gate (implemented 2026-04-06)
- [ ] #2 Seeder --dry-run mode
- [ ] #3 PR creation test gate hook
- [ ] #4 Implementation plan template with External Dependencies section
- [ ] #5 Coordinate truthiness guard (js_coordinate_truthiness_guard.py)
- [ ] #6 External API smoke guard hook (external_api_smoke_guard.py)
- [ ] #7 API response contract fixtures (NPS, Overpass, PAD-US)
- [ ] #8 HTTP error response tests (429/401/503/timeout)
- [ ] #9 NPS/Overpass/PAD-US smoke tests (RUN_SMOKE_TESTS=1)
- [ ] #10 End-to-end import-to-API test (seeder -> DB -> /api/poi)
- [ ] #11 XSS onclick guard (js_xss_onclick_guard.py)
- [ ] #12 Plan external dependency guard hook (plan_external_dep_guard.py)
- [ ] #13 Real PAD-US MultiPolygon geometry fixture
- [ ] #14 Manual test coverage advisory hook
- [ ] #15 SQL Server compatibility tests (SQLite/SQL Server drift)
