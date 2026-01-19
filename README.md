# Stock Analyzer Dashboard

A financial data visualization application for researching publicly traded stocks through interactive charts, company metrics, and news analysis.

**Live Demo:** [psfordtaurus.com](https://psfordtaurus.com)

## Features

- **Stock Search** - Search by company name or ticker symbol with autocomplete
- **Interactive Charts** - Candlestick and line charts with zoom/pan (Plotly.js)
- **Technical Analysis** - Moving average overlays (7, 21, 50, 200-day)
- **Significant Move Markers** - Visual indicators for days with large price changes
- **News Integration** - Headlines correlated with major price movements
- **Company Metrics** - P/E ratio, dividend yield, market cap, and more
- **Watchlist** - Save stocks for quick access (persisted to database)
- **Portfolio View** - Combined chart showing all watchlist stocks

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | .NET 8, ASP.NET Core, Entity Framework Core |
| **Frontend** | Vanilla JavaScript, Plotly.js, Tailwind CSS |
| **Database** | Azure SQL Database |
| **Hosting** | Azure App Service (Linux container) |
| **CDN/WAF** | Cloudflare |
| **CI/CD** | GitHub Actions |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Cloudflare                          │
│              (DNS, TLS, DDoS protection, WAF)               │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS
┌─────────────────────────▼───────────────────────────────────┐
│                    Azure App Service                        │
│                      (Linux B1 tier)                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              .NET 8 Container                          │ │
│  │  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │ │
│  │  │ ASP.NET Core │  │ Stock APIs  │  │ Static Files │  │ │
│  │  │   Web API    │  │ (Yahoo,     │  │ (HTML, JS,   │  │ │
│  │  │              │  │  Finnhub)   │  │  CSS)        │  │ │
│  │  └──────────────┘  └─────────────┘  └──────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Azure SQL Database                       │
│                      (Basic 5 DTU)                          │
└─────────────────────────────────────────────────────────────┘
```

## Local Development

### Prerequisites

- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
- [Docker](https://www.docker.com/products/docker-desktop) (optional, for containerized runs)
- SQL Server or SQLite for local database

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/psford/claudeProjects.git
   cd claudeProjects/stock_analyzer_dotnet
   ```

2. Configure environment variables:
   ```bash
   # Create appsettings.Development.json or set environment variables
   export ConnectionStrings__DefaultConnection="your-connection-string"
   export Finnhub__ApiKey="your-finnhub-api-key"  # Optional, for news
   ```

3. Run the application:
   ```bash
   dotnet run --project src/StockAnalyzer.Api
   ```

4. Open [http://localhost:5000](http://localhost:5000) in your browser.

### Running with Docker

```bash
docker build -t stockanalyzer .
docker run -p 5000:5000 \
  -e ConnectionStrings__DefaultConnection="your-connection-string" \
  stockanalyzer
```

## Project Structure

```
stock_analyzer_dotnet/
├── src/
│   ├── StockAnalyzer.Api/       # ASP.NET Core web application
│   │   ├── Controllers/         # API endpoints
│   │   ├── wwwroot/             # Static files (HTML, JS, CSS)
│   │   └── Program.cs           # Application entry point
│   └── StockAnalyzer.Core/      # Business logic and data access
│       ├── Services/            # Stock data, news, caching
│       ├── Models/              # Domain entities
│       └── Data/                # EF Core DbContext
├── tests/                       # Unit and integration tests
├── docs/                        # Documentation
│   ├── TECHNICAL_SPEC.md        # Architecture and implementation details
│   ├── FUNCTIONAL_SPEC.md       # Feature requirements
│   ├── SECURITY_OVERVIEW.md     # Security controls
│   └── RUNBOOK.md               # Production operations guide
└── infrastructure/              # Azure Bicep templates
```

## Security

This application implements defense-in-depth security:

- **SAST**: CodeQL, SecurityCodeScan, .NET Analyzers
- **SCA**: OWASP Dependency Check, Dependabot
- **Secrets**: Azure Key Vault, pre-commit scanning
- **Runtime**: Content Security Policy, security headers, TLS encryption

See [SECURITY_OVERVIEW.md](stock_analyzer_dotnet/docs/SECURITY_OVERVIEW.md) for details.

## Privacy

This application:
- Does **not** use tracking pixels, analytics, or advertising technology
- Does **not** collect or share personal data
- Does **not** require user registration
- Processes only publicly available financial data

## Data Sources

| Data | Source | Notes |
|------|--------|-------|
| Stock prices | Yahoo Finance | ~15 minute delay |
| Company news | Finnhub | API key required |
| Company info | Yahoo Finance | Cached |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/stock/{symbol}` | Get stock price history |
| `GET /api/stock/{symbol}/info` | Get company information |
| `GET /api/stock/{symbol}/news` | Get company news |
| `GET /api/watchlist` | Get user's watchlist |
| `POST /api/watchlist/{symbol}` | Add stock to watchlist |
| `DELETE /api/watchlist/{symbol}` | Remove stock from watchlist |
| `GET /health` | Health check endpoint |

## Deployment

Production deployments are automated via GitHub Actions. See [RUNBOOK.md](stock_analyzer_dotnet/docs/RUNBOOK.md) for operational procedures.

## Documentation

- [Technical Specification](stock_analyzer_dotnet/docs/TECHNICAL_SPEC.md) - Architecture, dependencies, configuration
- [Functional Specification](stock_analyzer_dotnet/docs/FUNCTIONAL_SPEC.md) - Features and requirements
- [Security Overview](stock_analyzer_dotnet/docs/SECURITY_OVERVIEW.md) - Security controls and compliance
- [Runbook](stock_analyzer_dotnet/docs/RUNBOOK.md) - Production operations

## License

MIT License - see [LICENSE](LICENSE) for details.
