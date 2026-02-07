"""Fetch and manage the follow list using the public Bluesky API.

Uses the unauthenticated public API endpoint to avoid needing session tokens
for follow list reads. Authentication is only needed for feed registration.
"""

import logging

import aiohttp

import db
from config import BLUESKY_HANDLE

logger = logging.getLogger(__name__)

# Public API (no auth required for reads)
PUBLIC_API = "https://public.api.bsky.app"


async def resolve_handle_to_did(handle: str) -> str | None:
    """Resolve a Bluesky handle to a DID via public API."""
    url = f"{PUBLIC_API}/xrpc/com.atproto.identity.resolveHandle"
    params = {"handle": handle}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("did")
            else:
                logger.error("Failed to resolve handle %s: %s", handle, resp.status)
                return None


async def fetch_follows(actor_did: str) -> list[dict]:
    """Fetch the complete follow list for an actor.

    Paginates through all results. Returns list of {"did": ..., "handle": ...}.
    """
    follows = []
    cursor = None
    url = f"{PUBLIC_API}/xrpc/app.bsky.graph.getFollows"

    async with aiohttp.ClientSession() as session:
        while True:
            params = {"actor": actor_did, "limit": 100}
            if cursor:
                params["cursor"] = cursor

            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.error("Failed to fetch follows: %s", resp.status)
                    break

                data = await resp.json()
                for follow in data.get("follows", []):
                    follows.append(
                        {"did": follow["did"], "handle": follow.get("handle", "")}
                    )

                cursor = data.get("cursor")
                if not cursor:
                    break

    logger.info("Fetched %d follows for %s", len(follows), actor_did)
    return follows


async def refresh_follow_list() -> list[str]:
    """Refresh the stored follow list. Returns list of followed DIDs."""
    # Resolve our handle to DID
    my_did = await resolve_handle_to_did(BLUESKY_HANDLE)
    if not my_did:
        logger.error("Could not resolve own handle: %s", BLUESKY_HANDLE)
        return db.get_followed_dids()  # Return existing list as fallback

    # Fetch full follow list
    follows = await fetch_follows(my_did)
    if not follows:
        logger.warning("Empty follow list returned — keeping existing data")
        return db.get_followed_dids()

    # Store in DB
    db.replace_follows(follows)
    db.set_state("my_did", my_did)
    db.set_state("last_follow_refresh", __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).isoformat())

    dids = [f["did"] for f in follows]
    logger.info("Follow list refreshed: %d accounts", len(dids))
    return dids
