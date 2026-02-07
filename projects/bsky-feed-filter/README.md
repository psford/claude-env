# Bluesky Self-Repost Filter Feed

A custom Bluesky feed generator that filters out self-reposts of recent posts (< 24 hours old). Targets the engagement farming pattern where someone writes a post, then repeatedly reposts it throughout the day for fresh engagement.

Older self-reposts (> 24h) pass through — those are legitimate shares of evergreen content.

## How It Works

1. **Jetstream consumer** connects to Bluesky's firehose, filtered to only your followed accounts
2. Posts and reposts are indexed in a local SQLite database
3. When a repost arrives: is the reposter the same person as the original author? If yes, was the post created < 24h ago? If both true, it's filtered out.
4. Three web endpoints serve the feed to Bluesky's infrastructure, which hydrates it into full post objects for the app

## Architecture

```
Bluesky Firehose (Jetstream)  ──→  Python asyncio server  ──→  SQLite (WAL mode)
                                          │
                                   aiohttp web server
                                          │
Bluesky AppView  ←─────────────  Feed skeleton responses
```

Single Python process, three concurrent async tasks:
- **Web server** (port 3000) — serves feed endpoints
- **Jetstream consumer** — WebSocket connection to Bluesky's firehose
- **Periodic tasks** — follow list refresh (1h), DB cleanup (48h expiry)

## Deployment: Synology NAS + Cloudflare Tunnel

### Security Model

- **No inbound ports** — Cloudflare Tunnel creates outbound-only connections
- **Read-only container** — filesystem is immutable except for /data volume
- **No NAS access** — uses named Docker volume, not bind mount
- **Non-root** — runs as unprivileged user with all capabilities dropped
- **Isolated network** — only the feed container and cloudflared can communicate

### Prerequisites

1. Synology NAS with Docker/Container Manager
2. Cloudflare account with a domain (psford.com)
3. Bluesky app password (from https://bsky.app/settings/app-passwords)

### Setup

1. **Create Cloudflare Tunnel:**
   - Cloudflare Zero Trust → Networks → Tunnels → Create
   - Copy the tunnel token
   - Add public hostname: `bsky-feed.psford.com` → `http://bsky-feed:3000`

2. **Configure:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. **Deploy:**
   ```bash
   docker compose up -d --build
   ```

4. **Verify:**
   ```bash
   curl https://bsky-feed.psford.com/.well-known/did.json
   ```

5. **Register feed:**
   ```bash
   docker compose exec bsky-feed python publish_feed.py
   ```

6. **Pin in Bluesky app:** Go to Feeds → search "Clean Following" → Pin

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export BLUESKY_HANDLE=psford.com
export BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
export HOSTNAME=localhost
export DATA_DIR=./data

# Run
python server.py
```

Test endpoints:
```bash
curl http://localhost:3000/.well-known/did.json
curl http://localhost:3000/xrpc/app.bsky.feed.describeFeedGenerator
curl "http://localhost:3000/xrpc/app.bsky.feed.getFeedSkeleton?feed=at://did:web:localhost/app.bsky.feed.generator/clean-following"
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BLUESKY_HANDLE` | `psford.com` | Your Bluesky handle (without @) |
| `BLUESKY_APP_PASSWORD` | — | App password for authentication |
| `HOSTNAME` | `bsky-feed.psford.com` | Public hostname |
| `PORT` | `3000` | Web server port |
| `SELF_REPOST_MAX_AGE_HOURS` | `24` | Posts younger than this are filtered |
| `FOLLOW_REFRESH_INTERVAL_SECONDS` | `3600` | How often to refresh follow list |
| `DB_RETENTION_HOURS` | `48` | How long to keep data |

## Files

| File | Purpose |
|------|---------|
| `server.py` | Main entry point: web server + Jetstream + periodic tasks |
| `config.py` | Environment variable loading |
| `db.py` | SQLite schema and queries (WAL mode) |
| `filter.py` | Self-repost detection logic |
| `follows.py` | Follow list management via public API |
| `publish_feed.py` | One-time feed registration script |
| `Dockerfile` | Container build (non-root, slim base) |
| `docker-compose.yml` | NAS deployment with Cloudflare Tunnel |
