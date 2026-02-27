# Human Test Plan: SecurityMaster MIC Code Enrichment

## Prerequisites

- Local SQL Express running: `net start MSSQL$SQLEXPRESS`
- EF Core migration applied: `dotnet ef database update` from `projects/stock-analyzer/src/StockAnalyzer.Api/`
- API running on `localhost:5000`
- All automated tests passing: `dotnet test projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/`
- EODHD API key available in `.env`

## Automated Test Coverage (42 tests)

| Test File | Tests | Criteria |
|-----------|-------|----------|
| MicExchangeSchemaTests.cs | 12 | AC1.4, AC2.2, AC2.4 |
| SearchResultDisplayTests.cs | 8 | AC5.4 |
| SecurityMasterDtoTests.cs | 15 | AC6.1, AC6.3 |
| BackfillMicCodesTests.cs | 7 | AC3.2, AC3.4, AC3.5 |

## Phase 1: Database Schema Verification

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | `SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'data' AND TABLE_NAME = 'MicExchange' ORDER BY ORDINAL_POSITION` | 4 columns: MicCode (char, 4, NO), ExchangeName (nvarchar, 200, NO), Country (char, 2, NO), IsActive (bit, null, NO) |
| 1.2 | `SELECT COUNT(*) FROM data.MicExchange` | Count >= 2,200 |
| 1.3 | `SELECT MicCode, ExchangeName, Country FROM data.MicExchange WHERE MicCode IN ('XNYS','XNAS','ARCX','BATS','OTCM','PINX')` | 6 rows with correct exchange names |
| 1.4 | `SELECT COL_LENGTH('data.SecurityMaster', 'Exchange')` | Returns NULL (column removed) |
| 1.5 | `SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'data' AND TABLE_NAME = 'SecurityMaster' AND COLUMN_NAME = 'MicCode'` | 1 row: MicCode, char, 4, YES |
| 1.6 | `UPDATE data.SecurityMaster SET MicCode = 'ZZZZ' WHERE SecurityAlias = (SELECT TOP 1 SecurityAlias FROM data.SecurityMaster)` | FK violation error |
| 1.7 | `UPDATE data.SecurityMaster SET MicCode = NULL WHERE SecurityAlias = (SELECT TOP 1 SecurityAlias FROM data.SecurityMaster)` | Succeeds (NULL is allowed) |

## Phase 2: Backfill Endpoint

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | `POST /api/admin/securities/backfill-mic-codes` (no auth) | HTTP 401 Unauthorized |
| 2.2 | `POST /api/admin/securities/backfill-mic-codes` (with auth) | HTTP 200, JSON with matched/unmatched/unknownExchanges |
| 2.3 | Call same endpoint while running | HTTP 409 Conflict |
| 2.4 | Query: `SELECT TOP 20 sm.TickerSymbol, sm.MicCode, me.ExchangeName FROM data.SecurityMaster sm LEFT JOIN data.MicExchange me ON sm.MicCode = me.MicCode WHERE sm.MicCode IS NOT NULL` | Valid MIC codes with joined exchange names |
| 2.5 | Check API logs | Batch processing messages visible |
| 2.6 | Check API logs | Unknown exchange warnings (not errors) |

## Phase 3: API Response Verification

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | `GET /api/admin/data/securities?take=5` | JSON includes `micCode` and `exchangeName` fields |
| 3.2 | `GET /api/stock/AAPL` | Response contains `micCode` (e.g., "XNAS") and `exchangeName` |
| 3.3 | `GET /api/search?q=AAPL` | Results include `micCode`/`exchangeName`, DisplayName shows exchange name |
| 3.4 | `GET /api/stock/<ticker-with-null-mic>` | `micCode: null`, `exchangeName: null` — no errors |

## Phase 4: ImportanceScore Verification

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | `POST /api/admin/securities/calculate-importance` | Completes successfully |
| 4.2 | `SELECT TOP 5 TickerSymbol, MicCode, ImportanceScore FROM data.SecurityMaster WHERE MicCode = 'XNYS' ORDER BY ImportanceScore DESC` | NYSE securities include +1 MIC bonus |
| 4.3 | `SELECT TOP 5 TickerSymbol, MicCode, ImportanceScore FROM data.SecurityMaster WHERE MicCode IN ('OTCM','PINX','XOTC') ORDER BY ImportanceScore ASC` | OTC securities have lower scores, minimum 1 |
| 4.4 | `SELECT MicCode, AVG(CAST(ImportanceScore AS FLOAT)) as AvgScore, COUNT(*) FROM data.SecurityMaster GROUP BY MicCode ORDER BY AvgScore DESC` | XNYS/XNAS higher than OTCM/PINX |
| 4.5 | `SELECT MAX(ImportanceScore) FROM data.SecurityMaster WHERE MicCode = 'XNYS'` | Score 10 achievable |

## End-to-End Sequence

1. Confirm some securities have `MicCode = NULL`
2. Run backfill: `POST /api/admin/securities/backfill-mic-codes`
3. Verify matched/unmatched counts
4. Run importance recalculation: `POST /api/admin/securities/calculate-importance`
5. Run refresh-summary: `POST /api/admin/prices/refresh-summary`
6. Query NYSE security (e.g., AAPL) — verify micCode, exchangeName, score
7. Query OTC security — verify -2 penalty reflected
8. Search — verify DisplayName includes exchange name

## Traceability

| AC | Automated | Manual |
|----|-----------|--------|
| AC1.1 Table schema | — | 1.1 |
| AC1.2 Seed rows | — | 1.2 |
| AC1.3 Key exchanges | — | 1.3 |
| AC1.4 DbContext config | MicExchangeSchemaTests (4) | — |
| AC2.1 Exchange removed | — | 1.4 |
| AC2.2 MicCode FK | MicExchangeSchemaTests (2) | 1.5 |
| AC2.3 FK enforced | — | 1.6 |
| AC2.4 Entity nav | MicExchangeSchemaTests (4) | — |
| AC3.1 Endpoint auth | — | 2.1, 2.2 |
| AC3.2 EODHD mapping | BackfillMicCodesTests (3) | — |
| AC3.3 Batch processing | BackfillMicCodesTests (1) | 2.5 |
| AC3.4 Summary response | BackfillMicCodesTests (2) | 2.2 |
| AC3.5 Unknown exchanges | BackfillMicCodesTests (1) | 2.6 |
| AC4.1-4.5 ImportanceScore | Deferred (extraction) | 4.1-4.5 |
| AC5.1 Endpoints return fields | — | 3.1-3.4 |
| AC5.2 ExchangeName join | Deferred (repo tests) | 3.1, 3.2 |
| AC5.3 Null returns null | Deferred (repo tests) | 3.4 |
| AC5.4 DisplayName | SearchResultDisplayTests (8) | 3.3 |
| AC6.1 DTOs use MicCode | SecurityMasterDtoTests (6) | — |
| AC6.2 Repository CRUD | Deferred (repo tests) | 2.4 |
| AC6.3 No Exchange refs | SecurityMasterDtoTests (4) | — |
