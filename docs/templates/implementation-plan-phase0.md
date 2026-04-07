<!--
PHASE 0 TEMPLATE — Copy this into every implementation plan as the FIRST phase.
Complete it BEFORE writing any other phase. The plan_api_url_guard hook will
block commits of plans that reference API URLs without verification markers.
-->

## Phase 0: External Dependencies & Deployment Constraints

> Complete this phase with live network access. Do not fill in values from
> documentation or memory — fill in ONLY what you observe from actual responses.

### External APIs

For each external API this feature depends on:

| API | Purpose | Docs URL |
|-----|---------|----------|
| [Name] | [what it provides] | [link] |

#### Live Verification Checklist

- [ ] Endpoint URL confirmed reachable (HTTP 200 received)
- [ ] Response is JSON (not XML, HTML error page, or redirect)
- [ ] Field names recorded below (copied from actual response, not docs)
- [ ] Pagination / result count limits tested
- [ ] Rate limit behavior documented (429 response? Retry-After header?)
- [ ] Response saved to `docs/api-contracts/<ImporterName>.json`

#### Verified Endpoint Details

<!-- Fill ONLY after hitting the live endpoint -->

**[API Name]**
- Live URL: `https://...` (the URL that returned 200)
- Auth: [none / API key header / query param]
- Fields observed in response:
  ```
  [paste actual field names from first record]
  ```
- Pagination: [offset / cursor / page number]
- Max page size tested: [N] (larger caused: [result])
- Date verified: YYYY-MM-DD

<!-- REQUIRED by plan_api_url_guard hook: -->
<!-- API-VERIFIED: https://[url] — verified YYYY-MM-DD -->

### Deployment Constraints

<!-- Fill in based on the target infrastructure -->

- [ ] Target database tier identified: [Azure SQL Basic / Standard / Premium / local]
- [ ] Estimated data volume: [N rows, ~M MB per row]
- [ ] Command timeout adequate: [default 30s / need N seconds because...]
- [ ] Batch size appropriate for tier: [N records per SaveChanges]
- [ ] Migration creates empty table requiring seeder run: [yes/no]
- [ ] Connection string source confirmed: [env var name / az CLI lookup / appsettings]

#### Infrastructure Limits

| Constraint | Value | Source |
|-----------|-------|--------|
| DB command timeout | [30s default / custom] | [EF Core default / Program.cs] |
| Max batch size | [N] | [tested against tier] |
| nvarchar(max) column sizes | [estimated max chars] | [sample data] |
| DTU / compute tier | [Basic 5 DTU / Standard S0 / etc] | [Azure portal] |

### Post-Deploy Requirements

- [ ] Migration auto-applies on app restart: [yes/no]
- [ ] Seeder must run after deploy: [yes — command: `...` / no]
- [ ] App restart required: [yes/no]
- [ ] Data backfill needed: [yes — estimated time: N min / no]
