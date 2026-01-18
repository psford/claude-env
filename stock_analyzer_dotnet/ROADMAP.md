# Stock Analyzer Roadmap

Planned features and improvements for the Stock Analyzer .NET application.

> **Note:** The original Python/Streamlit version has been archived to `archive/stock_analysis_python/`. This roadmap now focuses exclusively on the .NET implementation.

---

## Completed Features

### Core Functionality

| Feature | Description | Date |
|---------|-------------|------|
| REST API | ASP.NET Core minimal API endpoints | 01/16/2026 |
| Plotly.js charts | Interactive candlestick/line charts with zoom, pan, hover | 01/16/2026 |
| Ticker search | Autocomplete with Yahoo Finance API | 01/16/2026 |
| Company identifiers | ISIN, CUSIP, SEDOL via Finnhub + OpenFIGI | 01/16/2026 |
| Chart markers | Triangle markers for significant price moves | 01/16/2026 |
| Wikipedia-style popups | Hover popups with news headlines and thumbnails | 01/16/2026 |
| Configurable threshold | Slider to adjust significant move threshold (3-10%) | 01/16/2026 |
| Technical indicators | RSI and MACD with toggle checkboxes | 01/17/2026 |
| Stock comparison | Normalized % change comparison with benchmark buttons | 01/17/2026 |
| Dark mode | Full dark mode support with localStorage persistence | 01/16/2026 |
| Watchlist | Multiple watchlists with ticker management, JSON storage, multi-user ready | 01/17/2026 |

### Image System

| Feature | Description | Date |
|---------|-------------|------|
| Cats vs Dogs toggle | Radio button to choose animal for thumbnail images | 01/16/2026 |
| Image pre-caching | Pre-load 50 cats/dogs on page load, auto-refill when low | 01/16/2026 |
| ML image processing | YOLOv8n ONNX for intelligent animal face cropping | 01/16/2026 |

### Documentation

| Feature | Description | Date |
|---------|-------------|------|
| Documentation page | Tabbed markdown viewer for specs and guidelines | 01/17/2026 |
| Architecture diagrams | Mermaid.js visualizations (7 diagrams) | 01/17/2026 |
| Fuzzy search | Fuse.js search across all documentation | 01/17/2026 |
| Scroll spy | TOC highlighting tracks current section | 01/17/2026 |

### Security & Testing

| Feature | Description | Date |
|---------|-------------|------|
| Security headers | CSP, X-Frame-Options, X-Content-Type-Options, etc. | 01/16/2026 |
| SAST scanning | SecurityCodeScan for C# code | 01/16/2026 |
| DAST scanning | OWASP ZAP API scan | 01/16/2026 |
| SRI for CDN | Subresource Integrity for Plotly.js | 01/16/2026 |
| Unit tests | xUnit test suite (77 tests) | 01/17/2026 |

### Infrastructure

| Feature | Description | Date |
|---------|-------------|------|
| Pre-commit hooks | Block commits with security issues | 01/15/2026 |
| Deployment guide | Oracle Cloud with Dockerfile and docker-compose | 01/16/2026 |

---

## Planned Features

### High Priority

| Feature | Description | Status |
|---------|-------------|--------|
| Azure deployment | Migrate hosting from Oracle Cloud to Azure | Planned |
| Bollinger Bands | Add Bollinger Bands to technical indicators | Planned |
| Stochastic Oscillator | Add Stochastic to technical indicators | Planned |
| ~~Portfolio tracker~~ | ~~Track holdings, calculate weighted returns~~ | **Completed** (as Watchlist) |

### Medium Priority

| Feature | Description | Status |
|---------|-------------|--------|
| User stories | Review roadmap and propose user stories with acceptance criteria | Planned |
| Earnings calendar | Show earnings dates on charts | Planned |
| Export to Excel | Export analysis data to .xlsx format | Planned |
| News sentiment | Sentiment scoring for news articles | Planned |

### Low Priority / Nice to Have

| Feature | Description | Status |
|---------|-------------|--------|
| Real-time streaming | WebSocket-based live price updates | Planned |
| Options chain | Options data retrieval and Greeks calculation | Planned |
| Backtesting | Simple strategy backtesting capability | Planned |

---

## Infrastructure Backlog

| Feature | Description | Status |
|---------|-------------|--------|
| Docker containerization | Dockerfile + docker-compose for deployment | Planned |
| Load testing | k6 or Locust performance benchmarks | Planned |
| Error tracking | Sentry or Application Insights integration | Planned |
| Log archiving | Auto-archive logs when size threshold exceeded | Planned |

### Recently Completed (Infrastructure)

| Feature | Description | Date |
|---------|-------------|------|
| Structured logging | Serilog with file/console output, request logging | 01/17/2026 |
| Health checks | /health, /health/live, /health/ready endpoints | 01/17/2026 |
| GitHub integration | SSH auth, remote repository | 01/17/2026 |
| GitHub Actions CI | Build + test on push/PR | 01/17/2026 |
| Jenkins pipeline | Local Docker-based CI | 01/17/2026 |
| CodeQL security | SAST for C# and Python | 01/17/2026 |
| Branch protection | PR reviews, status checks required | 01/17/2026 |
| PR templates | Standardized review checklist | 01/17/2026 |
| CODEOWNERS | Auto-assign reviewers | 01/17/2026 |
| Status dashboard | Health monitoring UI at /status.html | 01/17/2026 |
| .NET analyzers | NetAnalyzers + Roslynator for enhanced SAST | 01/17/2026 |
| Dependabot | Automated dependency vulnerability updates | 01/17/2026 |
| OWASP Dep Check | Dependency scanning in CI/CD pipeline | 01/17/2026 |

---

## Version History

| Date | Change |
|------|--------|
| 01/17/2026 | Completed: Watchlist feature with sidebar UI, 8 API endpoints, JSON storage, multi-user ready |
| 01/17/2026 | Added: .NET security analyzers, Dependabot, OWASP Dep Check |
| 01/17/2026 | Added: Status dashboard for health monitoring |
| 01/17/2026 | Reorganized roadmap: archived Python version, consolidated .NET features |
| 01/17/2026 | Completed: Documentation page with architecture diagrams, search, scroll spy |
| 01/17/2026 | Completed: Stock comparison with normalized % change |
| 01/17/2026 | Completed: RSI and MACD technical indicators |
| 01/16/2026 | Completed: Dark mode toggle with localStorage persistence |
| 01/16/2026 | Completed: ML image processing with YOLOv8n ONNX |
| 01/16/2026 | Completed: SRI for Plotly.js CDN |
| 01/16/2026 | Completed: xUnit test suite (77 tests) |
| 01/16/2026 | Completed: Image pre-caching system |
| 01/16/2026 | Completed: Oracle Cloud deployment guide |
| 01/16/2026 | Completed: Cats vs Dogs toggle |
| 01/16/2026 | Completed: Chart markers and hover popups |
| 01/16/2026 | Completed: Ticker search autocomplete, security headers |
| 01/15/2026 | Completed: Pre-commit hooks, DAST scanning |
| 01/14/2026 | Initial roadmap created |
