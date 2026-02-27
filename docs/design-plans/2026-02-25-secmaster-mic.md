# SecurityMaster MIC Code Enrichment Design

## Summary

Replace the free-text `Exchange` column on SecurityMaster (currently storing "US" for all ~30K securities) with a proper `MicCode` foreign key to a new `MicExchange` reference table seeded with the full ISO 10383 dataset (~2,274 entries). Add an admin backfill endpoint that calls EODHD's exchange-symbol-list API to populate real MIC codes (XNYS, XNAS, ARCX, etc.) for existing securities. Update the ImportanceScore algorithm to use MIC-based lookups instead of string matching, and return both `micCode` and `exchangeName` in all API responses.

## Definition of Done

- MicExchange reference table with full ISO 10383 MIC codes (~2,500 entries), FK pattern like SourceEntity
- Rename Exchange → MicCode on SecurityMaster with FK constraint to MicExchange
- One-time backfill via EODHD exchange-symbol-list API to populate real MIC codes for US securities
- Scoring algorithm updated to use MIC codes (replacing Exchange="US" check with proper MIC-based logic)
- API responses return both micCode and exchangeName (joined from reference table)
- All DTOs, repository code, and dependent services updated for the rename
- Out of scope: daily updater automation, non-US market enrichment, ImportanceScore recalculation run

## Architecture

### Data Model

```
data.MicExchange (new reference table)
├── MicCode       char(4)         PK, natural key   -- e.g., "XNYS"
├── ExchangeName  nvarchar(200)   NOT NULL           -- e.g., "New York Stock Exchange"
├── Country       char(2)         NOT NULL           -- ISO 3166-1 alpha-2
└── IsActive      bit             NOT NULL DEFAULT 1

data.SecurityMaster (modified)
├── SecurityAlias  int            PK (unchanged)
├── MicCode        char(4)        nullable FK → MicExchange.MicCode  (replaces Exchange)
└── ... (all other columns unchanged)
```

**PK strategy:** Natural key on `MicCode` (char(4)). MIC codes are globally unique by ISO standard, self-documenting in queries, and avoid unnecessary joins for filtering. Follows industry convention for code tables.

**Nullable FK:** MicCode is nullable because some securities may not have a known exchange (OTC, delisted, or data not yet enriched). The FK constraint ensures only valid MIC codes can be stored.

### Reference Table: MicExchange

Follows the SourceEntity pattern from the existing codebase:
- Lives in `data` schema
- Simple structure: code + descriptive name + metadata
- Seeded via SQL in the EF Core migration (self-contained, deploys automatically)

Differences from SourceEntity:
- Natural key (char(4)) instead of surrogate int (ValueGeneratedNever isn't needed — the PK IS the data)
- No auto-increment, no identity column
- Includes `Country` and `IsActive` fields from ISO 10383

### SecurityMaster Column Change

The `Exchange` column (nvarchar(50), nullable) is dropped and replaced with `MicCode` (char(4), nullable FK). Since all existing data is "US" (not a valid MIC code), there is no data to migrate — the column is simply replaced. Real MIC codes are populated post-deploy via the backfill endpoint.

### API Response Changes

All endpoints returning security data will include both fields:
```json
{
  "micCode": "XNYS",
  "exchangeName": "New York Stock Exchange"
}
```

The `exchangeName` is joined from MicExchange at query time. For securities with null MicCode, both fields return null.

### ImportanceScore Algorithm Update

Current (string contains, never fires because all data = "US"):
```csharp
if (exchange.Contains("NYSE") || exchange.Contains("NASDAQ")) score += 1;
if (exchange.Contains("OTC") || exchange.Contains("PINK") || exchange.Contains("GREY")) score -= 2;
```

New (MIC-based HashSet lookup):
```csharp
var bonusMics = new HashSet<string> { "XNYS", "XNAS" };
var penaltyMics = new HashSet<string> { "OTCM", "PINX", "XOTC" };
if (mic != null && bonusMics.Contains(mic)) score += 1;
if (mic != null && penaltyMics.Contains(mic)) score -= 2;
```

This unblocks Score 10: securities on NYSE/NASDAQ will get the +1 bonus that was previously impossible with Exchange="US".

## Existing Patterns Followed

| Pattern | Source | How Applied |
|---------|--------|-------------|
| Reference table in `data` schema | `SourceEntity` / `Sources` table | MicExchange follows same schema/table pattern |
| DbContext Fluent API configuration | `StockAnalyzerDbContext.OnModelCreating` | New entity configured inline with existing entities |
| Nullable FK on SecurityMaster | CompanyBio, TrackedSecurity patterns | MicCode FK allows null for unknown exchanges |
| SQL seed in migration | `CreateCoverageTablesIfNotExist` migration | Migration embeds INSERT statements for ~2,274 MIC codes |
| Admin bulk-update endpoint | `backfill-coverage`, `calculate-importance` | New `backfill-mic-codes` endpoint follows same pattern |
| DTO record types | `SecurityMasterCreateDto`, `SecurityMasterUpdateDto` | Update DTOs to use MicCode instead of Exchange |

## Implementation Phases

### Phase 1: MicExchange Entity and Migration

Create the `MicExchangeEntity` class, configure it in DbContext, and create an EF Core migration that:
1. Creates the `data.MicExchange` table with char(4) PK
2. Seeds ~2,274 rows from ISO 10383 data
3. Adds `MicCode` column to SecurityMaster with FK constraint
4. Drops the old `Exchange` column

**Files touched:**
- `StockAnalyzer.Core/Data/Entities/MicExchangeEntity.cs` (new)
- `StockAnalyzer.Core/Data/StockAnalyzerDbContext.cs` (add DbSet + configuration)
- `StockAnalyzer.Core/Data/Migrations/` (new migration)
- `StockAnalyzer.Core/Data/Entities/SecurityMasterEntity.cs` (replace Exchange with MicCode + navigation property)

### Phase 2: DTOs and Repository Updates

Update all DTOs, models, and repository methods that reference Exchange:
1. Replace `Exchange` property with `MicCode` on all DTOs/models
2. Add `ExchangeName` (string, read-only) to response models that need display text
3. Update `SqlSecurityMasterRepository` Create/Update/UpsertMany methods
4. Update any LINQ queries to include the MicExchange join for ExchangeName

**Files touched:**
- `StockAnalyzer.Core/Models/StockInfo.cs`
- `StockAnalyzer.Core/Models/SearchResult.cs`
- `StockAnalyzer.Core/Models/CompanyProfile.cs`
- `StockAnalyzer.Core/Services/ISecurityMasterRepository.cs` (DTOs)
- `StockAnalyzer.Core/Data/SqlSecurityMasterRepository.cs`

### Phase 3: API Endpoints and Scoring Algorithm

Update API endpoints to return micCode + exchangeName, and refactor the ImportanceScore algorithm:
1. Update all security-returning endpoints to include both fields
2. Refactor `CalculateImportanceScore` to use MIC-based HashSet lookup
3. Update the SearchResult `DisplayName` computed property to use exchangeName

**Files touched:**
- `StockAnalyzer.Api/Program.cs` (endpoints + scoring algorithm)

### Phase 4: Backfill Admin Endpoint

Create the admin endpoint that calls EODHD exchange-symbol-list API:
1. `POST /api/admin/securities/backfill-mic-codes` endpoint
2. Calls EODHD `exchange-symbol-list/US` (single API call, ~30K symbols returned)
3. Maps EODHD exchange field → MIC code (lookup table: "NYSE" → "XNYS", "NASDAQ" → "XNAS", etc.)
4. Bulk updates SecurityMaster.MicCode in batches
5. Returns summary: total matched, unmatched symbols, errors

**Files touched:**
- `StockAnalyzer.Api/Program.cs` (new admin endpoint)

### Phase 5: Verification and Post-Deploy Steps

Document and verify the post-deploy operational sequence:
1. Deploy (migration auto-runs: creates MicExchange, seeds data, modifies SecurityMaster)
2. `POST /api/admin/securities/backfill-mic-codes` (populates real MIC codes)
3. `POST /api/admin/securities/calculate-importance` (recalculates with new MIC logic)
4. `POST /api/admin/securities/refresh-summary` (rebuilds coverage summary)
5. Verify Score 10 appears in heatmap
6. Verify API responses include micCode + exchangeName

## Additional Considerations

### EODHD Exchange Mapping

The EODHD `exchange-symbol-list/US` API returns symbols with exchange info. The mapping from EODHD exchange names to MIC codes:

| EODHD Exchange | MIC Code |
|----------------|----------|
| NYSE | XNYS |
| NASDAQ | XNAS |
| NYSE ARCA | ARCX |
| BATS | BATS |
| OTC | OTCM |
| PINK | PINX |

This mapping should be configurable (not hardcoded) so it can be extended as new exchanges are encountered. A dictionary in the backfill endpoint is sufficient — no need for a separate configuration file.

### DTU Impact

- Migration: One-time, creates small table (~2,274 rows) + ALTER TABLE on SecurityMaster. Low DTU impact.
- Backfill endpoint: Single EODHD API call + batch UPDATE statements. Should batch in groups of 500-1000 to avoid DTU exhaustion. Use `WITH (ROWLOCK)` hints.
- No impact on Prices table or coverage tables.

### Future Extensibility

The design is API-friendly for a future daily updater:
- MicExchange table can be refreshed via admin endpoint reading updated SWIFT CSV
- SecurityMaster.MicCode can be updated via existing `PUT /api/admin/securities/{alias}` or a new bulk-update endpoint
- Non-US markets can be enriched by calling EODHD exchange-symbol-list for other exchange codes

### Breaking Changes

- API responses change `exchange` field to `micCode` + `exchangeName`. Frontend must be updated.
- Any external consumers of the API that filter by `exchange` field will need to use `micCode` instead.
- The eodhd-loader's `ISharesConstituentService` currently writes Exchange — needs updating to write MicCode.

## Acceptance Criteria

### AC1: MicExchange Reference Table
- **AC1.1** `data.MicExchange` table exists with columns: MicCode (char(4) PK), ExchangeName (nvarchar(200)), Country (char(2)), IsActive (bit)
- **AC1.2** Table is seeded with >= 2,200 rows from ISO 10383 data
- **AC1.3** Key US exchanges present: XNYS, XNAS, ARCX, BATS, OTCM, PINX
- **AC1.4** `MicExchangeEntity` is configured in DbContext with correct schema and constraints

### AC2: SecurityMaster Schema Change
- **AC2.1** `Exchange` column no longer exists on SecurityMaster
- **AC2.2** `MicCode` column exists as char(4), nullable, FK to MicExchange
- **AC2.3** FK constraint enforces referential integrity (cannot insert invalid MIC code)
- **AC2.4** SecurityMasterEntity has `MicCode` property and `MicExchange` navigation property

### AC3: Backfill Endpoint
- **AC3.1** `POST /api/admin/securities/backfill-mic-codes` endpoint exists and is authorized
- **AC3.2** Endpoint calls EODHD exchange-symbol-list API and maps results to MIC codes
- **AC3.3** Endpoint bulk-updates SecurityMaster.MicCode in batches (500-1000)
- **AC3.4** Endpoint returns summary: matched count, unmatched count, error details
- **AC3.5 (failure)** Unknown EODHD exchange names are logged but do not fail the batch

### AC4: ImportanceScore Algorithm
- **AC4.1** Scoring uses HashSet-based MIC lookup, not string contains
- **AC4.2** XNYS and XNAS grant +1 bonus
- **AC4.3** OTCM, PINX, XOTC apply -2 penalty
- **AC4.4** Null MicCode grants no bonus and no penalty
- **AC4.5 (failure)** Invalid MIC code in SecurityMaster does not crash scoring (nullable handling)

### AC5: API Responses
- **AC5.1** All security-returning endpoints include `micCode` and `exchangeName` fields
- **AC5.2** `exchangeName` is joined from MicExchange reference table
- **AC5.3** When MicCode is null, both `micCode` and `exchangeName` return null
- **AC5.4** SearchResult DisplayName shows exchange name (not MIC code) for readability

### AC6: DTO and Repository Updates
- **AC6.1** All DTOs (Create, Update, response models) use `MicCode` instead of `Exchange`
- **AC6.2** Repository Create/Update/UpsertMany methods handle MicCode correctly
- **AC6.3** No remaining references to `Exchange` property in production code (except migration history)

## Glossary

| Term | Definition |
|------|------------|
| **MIC** | Market Identifier Code — ISO 10383 standard 4-character code uniquely identifying exchanges and trading venues |
| **Operating MIC** | Parent MIC representing the entity operating an exchange in a specific country (e.g., XNYS for NYSE) |
| **Segment MIC** | Child MIC representing a specific section/platform under an Operating MIC (e.g., ARCX under XNYS) |
| **ISO 10383** | International standard maintained by SWIFT for market identification codes |
| **EODHD** | End of Day Historical Data — the financial data API provider used for price and symbol data |
| **SecurityMaster** | The central reference table mapping security aliases to metadata (ticker, exchange, type, etc.) |
| **ImportanceScore** | Calculated 1-10 score determining data collection priority for each security |
| **Natural key** | A primary key derived from the data itself (MicCode = "XNYS") rather than an auto-generated surrogate |
