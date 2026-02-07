"""SQLite database layer with WAL mode for concurrent reads."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from config import DB_PATH, DB_RETENTION_HOURS, FEED_PAGE_SIZE

_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    uri TEXT PRIMARY KEY,
    author_did TEXT NOT NULL,
    created_at TEXT NOT NULL,
    indexed_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_did);

CREATE TABLE IF NOT EXISTS feed_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_uri TEXT NOT NULL,
    repost_uri TEXT,
    reposter_did TEXT,
    sort_time TEXT NOT NULL,
    is_filtered INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_feed_sort ON feed_items(is_filtered, sort_time DESC);

CREATE TABLE IF NOT EXISTS follows (
    did TEXT PRIMARY KEY,
    handle TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS service_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    """Open a connection with WAL mode and foreign keys."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and indexes if they don't exist."""
    conn = get_connection()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


# --- Posts ---


def insert_post(uri: str, author_did: str, created_at: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO posts (uri, author_did, created_at) VALUES (?, ?, ?)",
            (uri, author_did, created_at),
        )
        conn.commit()
    finally:
        conn.close()


def get_post(uri: str) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM posts WHERE uri = ?", (uri,)).fetchone()
        return row
    finally:
        conn.close()


def delete_post(uri: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM posts WHERE uri = ?", (uri,))
        conn.commit()
    finally:
        conn.close()


# --- Feed items ---


def insert_feed_item(
    post_uri: str,
    sort_time: str,
    repost_uri: Optional[str] = None,
    reposter_did: Optional[str] = None,
    is_filtered: bool = False,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO feed_items (post_uri, repost_uri, reposter_did, sort_time, is_filtered)
               VALUES (?, ?, ?, ?, ?)""",
            (post_uri, repost_uri, reposter_did, sort_time, 1 if is_filtered else 0),
        )
        conn.commit()
    finally:
        conn.close()


def get_feed_skeleton(
    limit: int = FEED_PAGE_SIZE, cursor: Optional[str] = None
) -> list[dict]:
    """Return unfiltered feed items for the skeleton response.

    Cursor format: "{sort_time}::{id}" for stable pagination.
    """
    conn = get_connection()
    try:
        if cursor:
            parts = cursor.split("::")
            if len(parts) == 2:
                cursor_time, cursor_id = parts[0], int(parts[1])
                rows = conn.execute(
                    """SELECT id, post_uri, repost_uri, sort_time
                       FROM feed_items
                       WHERE is_filtered = 0
                         AND (sort_time < ? OR (sort_time = ? AND id < ?))
                       ORDER BY sort_time DESC, id DESC
                       LIMIT ?""",
                    (cursor_time, cursor_time, cursor_id, limit),
                ).fetchall()
            else:
                rows = []
        else:
            rows = conn.execute(
                """SELECT id, post_uri, repost_uri, sort_time
                   FROM feed_items
                   WHERE is_filtered = 0
                   ORDER BY sort_time DESC, id DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()

        results = []
        for row in rows:
            item = {"post": row["post_uri"]}
            if row["repost_uri"]:
                item["reason"] = {
                    "$type": "app.bsky.feed.defs#skeletonReasonRepost",
                    "repost": row["repost_uri"],
                }
            results.append(item)

        return results
    finally:
        conn.close()


def get_last_feed_item_cursor(rows: list[dict], conn: sqlite3.Connection) -> Optional[str]:
    """Build cursor from the last row returned by get_feed_skeleton."""
    # This is called externally — see server.py
    pass


def delete_feed_items_by_post(post_uri: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM feed_items WHERE post_uri = ?", (post_uri,))
        conn.commit()
    finally:
        conn.close()


def delete_feed_items_by_repost(repost_uri: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM feed_items WHERE repost_uri = ?", (repost_uri,))
        conn.commit()
    finally:
        conn.close()


# --- Follows ---


def replace_follows(follows: list[dict]) -> None:
    """Replace the entire follows table atomically."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM follows")
        conn.executemany(
            "INSERT INTO follows (did, handle) VALUES (?, ?)",
            [(f["did"], f.get("handle")) for f in follows],
        )
        conn.commit()
    finally:
        conn.close()


def get_followed_dids() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT did FROM follows").fetchall()
        return [row["did"] for row in rows]
    finally:
        conn.close()


# --- Service state ---


def get_state(key: str) -> Optional[str]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM service_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_state(key: str, value: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO service_state (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


# --- Cleanup ---


def cleanup_old_data() -> int:
    """Delete posts and feed items older than DB_RETENTION_HOURS. Returns count deleted."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=DB_RETENTION_HOURS)
    ).strftime("%Y-%m-%dT%H:%M:%S")

    conn = get_connection()
    try:
        # Delete old feed items
        cursor = conn.execute(
            "DELETE FROM feed_items WHERE sort_time < ?", (cutoff,)
        )
        feed_deleted = cursor.rowcount

        # Delete old posts
        cursor = conn.execute(
            "DELETE FROM posts WHERE created_at < ?", (cutoff,)
        )
        posts_deleted = cursor.rowcount

        conn.commit()
        return feed_deleted + posts_deleted
    finally:
        conn.close()
