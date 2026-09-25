# Local ports

Nothing else records which local ports these projects use, so a collision
used to be found by something failing rather than by looking here first
(CE-2.84). Before picking a port for a new local dev server, check this
table.

| Port | Project | Where it's declared | What listens on it |
|------|---------|----------------------|---------------------|
| 5000 | stock-analyzer | `src/StockAnalyzer.Api/Properties/launchSettings.json` | ASP.NET Core Kestrel, `http` launch profile |
| 5001 | stock-analyzer | `src/StockAnalyzer.Api/Properties/launchSettings.json` | ASP.NET Core Kestrel, `https` launch profile |
| 5143 | road-trip | `src/RoadTripMap/Properties/launchSettings.json` | ASP.NET Core Kestrel, `http` launch profile — the local API |
| 5173 | omni-map | `vite.config.ts` | Vite dev server default |
| 5174 | omni-map | (no file) | Vite server for a second checkout or worktree, beside one already on 5173 |
| 7071 | photo-portfolio | `package.json`, `playwright.smoke.config.ts` | Azure Functions local host — the API the smoke test's build points at |
| 8787 | claude-harness | `dashboard/server.py` | Dashboard serve port. Also Wrangler's own default dev port — this collision is why photo-portfolio moved off it (see 9787) |
| 8788 | claude-harness | `deploy-dashboard.sh` | Smoke port for a deploy candidate, before it takes over 8787 |
| 8790-8799 | claude-harness | `plugins/psford-tickets/skills/creating-a-preview-link/SKILL.md` | Spare ports for an in-review story's preview dashboard |
| 9787 | photo-portfolio | `package.json`, `playwright.smoke.config.ts` | `wrangler dev` — the pre-push smoke test and `npm run cf:dev` |
| 10000 | road-trip | `tests/docker-compose.azurite.yml` | Azurite blob emulator for local/integration tests |
| 10001 | road-trip | `tests/docker-compose.azurite.yml` | Exposed by the same compose file |

## Checking it

`python3 helpers/port_lint.py docs/ports.md` exits 0 when every entry's
port (or port range) is exclusive, and exits 1, naming the collision on
stderr, when two entries claim the same port.
