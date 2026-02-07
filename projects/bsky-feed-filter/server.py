"""Main server: aiohttp web endpoints + Jetstream consumer + periodic tasks.

Single asyncio process that runs:
1. Web server serving the 3 required feed generator endpoints
2. Jetstream WebSocket consumer indexing posts/reposts from followed accounts
3. Periodic tasks: follow list refresh, DB cleanup
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timezone

import aiohttp
from aiohttp import web
import websockets
import websockets.exceptions

import db
import filter as repost_filter
import follows
from config import (
    HOSTNAME,
    SERVICE_DID,
    FEED_URI,
    PORT,
    HOST,
    JETSTREAM_URL,
    FEED_PAGE_SIZE,
    FOLLOW_REFRESH_INTERVAL_SECONDS,
    DB_CLEANUP_INTERVAL_SECONDS,
    SELF_REPOST_MAX_AGE_HOURS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ─── Web Endpoints ────────────────────────────────────────────────────────────


async def handle_did_doc(request: web.Request) -> web.Response:
    """GET /.well-known/did.json — DID document for did:web."""
    return web.json_response(
        {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": SERVICE_DID,
            "service": [
                {
                    "id": "#bsky_fg",
                    "type": "BskyFeedGenerator",
                    "serviceEndpoint": f"https://{HOSTNAME}",
                }
            ],
        }
    )


async def handle_describe_feed_generator(request: web.Request) -> web.Response:
    """GET /xrpc/app.bsky.feed.describeFeedGenerator — feed metadata."""
    return web.json_response(
        {
            "did": SERVICE_DID,
            "feeds": [{"uri": FEED_URI}],
        }
    )


async def handle_get_feed_skeleton(request: web.Request) -> web.Response:
    """GET /xrpc/app.bsky.feed.getFeedSkeleton — paginated feed skeleton."""
    feed_param = request.query.get("feed", "")
    if feed_param != FEED_URI:
        return web.json_response(
            {"error": "UnknownFeed", "message": f"Unknown feed: {feed_param}"},
            status=400,
        )

    limit = min(int(request.query.get("limit", FEED_PAGE_SIZE)), FEED_PAGE_SIZE)
    cursor = request.query.get("cursor")

    items = db.get_feed_skeleton(limit=limit, cursor=cursor)

    response: dict = {"feed": items}

    # Build cursor from last item
    if items:
        # Re-query the last item to get its sort_time and id for cursor
        conn = db.get_connection()
        try:
            last_post_uri = items[-1]["post"]
            last_repost_uri = items[-1].get("reason", {}).get("repost") if "reason" in items[-1] else None

            if last_repost_uri:
                row = conn.execute(
                    "SELECT id, sort_time FROM feed_items WHERE repost_uri = ? ORDER BY id DESC LIMIT 1",
                    (last_repost_uri,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT id, sort_time FROM feed_items WHERE post_uri = ? AND repost_uri IS NULL ORDER BY id DESC LIMIT 1",
                    (last_post_uri,),
                ).fetchone()

            if row:
                response["cursor"] = f"{row['sort_time']}::{row['id']}"
        finally:
            conn.close()

    return web.json_response(response)


# ─── Jetstream Consumer ───────────────────────────────────────────────────────


async def consume_jetstream(followed_dids: list[str]) -> None:
    """Connect to Jetstream and process post/repost events.

    Reconnects with exponential backoff on failure.
    Sends options_update when follow list changes.
    """
    backoff = 1
    max_backoff = 60

    while True:
        try:
            params = build_jetstream_params(followed_dids)
            url = f"{JETSTREAM_URL}?{params}"

            logger.info(
                "Connecting to Jetstream with %d followed DIDs...", len(followed_dids)
            )

            async with websockets.connect(url, ping_interval=30, ping_timeout=10) as ws:
                logger.info("Jetstream connected")
                backoff = 1  # Reset on successful connection

                # Store websocket reference for follow list updates
                consume_jetstream.ws = ws

                async for raw_msg in ws:
                    try:
                        msg = json.loads(raw_msg)
                        await process_jetstream_event(msg)

                        # Save cursor periodically (every event for now — cheap)
                        time_us = msg.get("time_us")
                        if time_us:
                            db.set_state("jetstream_cursor", str(time_us))

                    except json.JSONDecodeError:
                        logger.warning("Non-JSON message from Jetstream")
                    except Exception:
                        logger.exception("Error processing Jetstream event")

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning("Jetstream connection closed: %s", e)
        except Exception:
            logger.exception("Jetstream connection error")

        logger.info("Reconnecting in %ds...", backoff)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, max_backoff)

        # Refresh follow list on reconnect
        followed_dids = db.get_followed_dids()


# Store websocket reference as function attribute
consume_jetstream.ws = None


def build_jetstream_params(followed_dids: list[str]) -> str:
    """Build query string for Jetstream WebSocket URL."""
    from urllib.parse import urlencode

    params = []

    # Collections we care about
    params.append(("wantedCollections", "app.bsky.feed.post"))
    params.append(("wantedCollections", "app.bsky.feed.repost"))

    # Filter to only followed DIDs
    for did in followed_dids:
        params.append(("wantedDids", did))

    # Resume from saved cursor if available
    cursor = db.get_state("jetstream_cursor")
    if cursor:
        params.append(("cursor", cursor))

    return urlencode(params)


async def process_jetstream_event(event: dict) -> None:
    """Route a Jetstream event to the appropriate handler."""
    kind = event.get("kind")
    if kind != "commit":
        return

    commit = event.get("commit", {})
    operation = commit.get("operation")
    collection = commit.get("collection")
    did = event.get("did", "")

    if collection == "app.bsky.feed.post":
        if operation == "create":
            await handle_post_create(did, commit, event)
        elif operation == "delete":
            handle_post_delete(did, commit)

    elif collection == "app.bsky.feed.repost":
        if operation == "create":
            await handle_repost_create(did, commit, event)
        elif operation == "delete":
            handle_repost_delete(did, commit)


async def handle_post_create(did: str, commit: dict, event: dict) -> None:
    """Handle a new post from a followed user."""
    rkey = commit.get("rkey", "")
    record = commit.get("record", {})
    created_at = record.get("createdAt", datetime.now(timezone.utc).isoformat())

    post_uri = f"at://{did}/app.bsky.feed.post/{rkey}"

    # Index the post
    db.insert_post(post_uri, did, created_at)

    # Add to feed
    db.insert_feed_item(post_uri=post_uri, sort_time=created_at)

    logger.debug("Indexed post: %s", post_uri)


def handle_post_delete(did: str, commit: dict) -> None:
    """Handle a deleted post."""
    rkey = commit.get("rkey", "")
    post_uri = f"at://{did}/app.bsky.feed.post/{rkey}"

    db.delete_post(post_uri)
    db.delete_feed_items_by_post(post_uri)

    logger.debug("Deleted post: %s", post_uri)


async def handle_repost_create(did: str, commit: dict, event: dict) -> None:
    """Handle a new repost — apply self-repost filter."""
    rkey = commit.get("rkey", "")
    record = commit.get("record", {})
    subject_uri = record.get("subject", {}).get("uri", "")
    created_at = record.get("createdAt", datetime.now(timezone.utc).isoformat())

    repost_uri = f"at://{did}/app.bsky.feed.repost/{rkey}"

    if not subject_uri:
        return

    # Apply the self-repost filter
    is_filtered = repost_filter.should_filter_repost(did, subject_uri)

    if is_filtered:
        logger.info("FILTERED self-repost: %s reposted %s", did, subject_uri)

    db.insert_feed_item(
        post_uri=subject_uri,
        repost_uri=repost_uri,
        reposter_did=did,
        sort_time=created_at,
        is_filtered=is_filtered,
    )


def handle_repost_delete(did: str, commit: dict) -> None:
    """Handle a deleted repost."""
    rkey = commit.get("rkey", "")
    repost_uri = f"at://{did}/app.bsky.feed.repost/{rkey}"

    db.delete_feed_items_by_repost(repost_uri)

    logger.debug("Deleted repost: %s", repost_uri)


# ─── Periodic Tasks ───────────────────────────────────────────────────────────


async def periodic_follow_refresh() -> None:
    """Refresh the follow list periodically and update Jetstream filter."""
    while True:
        await asyncio.sleep(FOLLOW_REFRESH_INTERVAL_SECONDS)
        try:
            new_dids = await follows.refresh_follow_list()

            # Send options_update to Jetstream if connected
            ws = consume_jetstream.ws
            if ws and not ws.closed:
                update_msg = {
                    "type": "options_update",
                    "payload": {
                        "wantedCollections": [
                            "app.bsky.feed.post",
                            "app.bsky.feed.repost",
                        ],
                        "wantedDids": new_dids,
                    },
                }
                await ws.send(json.dumps(update_msg))
                logger.info("Sent Jetstream options_update with %d DIDs", len(new_dids))

        except Exception:
            logger.exception("Error refreshing follow list")


async def periodic_db_cleanup() -> None:
    """Clean up old data periodically."""
    while True:
        await asyncio.sleep(DB_CLEANUP_INTERVAL_SECONDS)
        try:
            deleted = db.cleanup_old_data()
            if deleted > 0:
                logger.info("DB cleanup: removed %d old records", deleted)
        except Exception:
            logger.exception("Error during DB cleanup")


# ─── Main ─────────────────────────────────────────────────────────────────────


async def run() -> None:
    """Start all components."""
    # Initialize database
    db.init_db()
    logger.info("Database initialized at %s", db.DB_PATH)

    # Initial follow list fetch
    logger.info("Fetching initial follow list for @%s...", follows.BLUESKY_HANDLE)
    followed_dids = await follows.refresh_follow_list()
    logger.info("Following %d accounts", len(followed_dids))

    if not followed_dids:
        logger.error(
            "No followed accounts found. Check BLUESKY_HANDLE. Continuing anyway..."
        )

    # Set up web server
    app = web.Application()
    app.router.add_get("/.well-known/did.json", handle_did_doc)
    app.router.add_get(
        "/xrpc/app.bsky.feed.describeFeedGenerator",
        handle_describe_feed_generator,
    )
    app.router.add_get(
        "/xrpc/app.bsky.feed.getFeedSkeleton", handle_get_feed_skeleton
    )

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    logger.info("Web server listening on %s:%d", HOST, PORT)
    logger.info("Feed URI: %s", FEED_URI)
    logger.info("Service DID: %s", SERVICE_DID)
    logger.info(
        "Self-repost filter: hide reposts of own posts < %dh old",
        SELF_REPOST_MAX_AGE_HOURS,
    )

    # Start background tasks
    tasks = [
        asyncio.create_task(consume_jetstream(followed_dids)),
        asyncio.create_task(periodic_follow_refresh()),
        asyncio.create_task(periodic_db_cleanup()),
    ]

    # Handle shutdown
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Shutting down...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await runner.cleanup()
        logger.info("Goodbye")


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
