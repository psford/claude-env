"""Configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

# Feed generator identity
HOSTNAME = os.environ.get("HOSTNAME", "bsky-feed.psford.com")
FEED_URI = f"at://did:web:{HOSTNAME}/app.bsky.feed.generator/clean-following"
SERVICE_DID = f"did:web:{HOSTNAME}"

# Bluesky credentials (for follow-list fetch + feed registration)
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE", "psford.com")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD", "")

# Server
PORT = int(os.environ.get("PORT", "3000"))
HOST = os.environ.get("BIND_HOST", "0.0.0.0")  # nosec B104 — intentional for Docker

# Database
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DB_PATH = DATA_DIR / "feed.db"

# Jetstream
JETSTREAM_URL = "wss://jetstream2.us-east.bsky.network/subscribe"

# Filter settings
SELF_REPOST_MAX_AGE_HOURS = int(os.environ.get("SELF_REPOST_MAX_AGE_HOURS", "24"))

# Maintenance
FOLLOW_REFRESH_INTERVAL_SECONDS = int(
    os.environ.get("FOLLOW_REFRESH_INTERVAL_SECONDS", "3600")
)  # 1 hour
DB_CLEANUP_INTERVAL_SECONDS = int(
    os.environ.get("DB_CLEANUP_INTERVAL_SECONDS", "3600")
)  # 1 hour
DB_RETENTION_HOURS = int(os.environ.get("DB_RETENTION_HOURS", "48"))

# Feed pagination
FEED_PAGE_SIZE = 50
