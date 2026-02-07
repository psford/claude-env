"""Self-repost detection logic.

A "self-repost" is when a user reposts their own post. We filter these
only when the original post is less than SELF_REPOST_MAX_AGE_HOURS old,
targeting the engagement-farming pattern of repeatedly bumping fresh posts.

Older self-reposts (>24h by default) pass through — those are legitimate
"throwback" or evergreen content shares.
"""

from datetime import datetime, timedelta, timezone

import db
from config import SELF_REPOST_MAX_AGE_HOURS


def parse_did_from_uri(at_uri: str) -> str | None:
    """Extract the DID from an AT URI.

    AT URI format: at://did:plc:abc123/app.bsky.feed.post/rkey
    Returns the DID portion, or None if unparseable.
    """
    if not at_uri.startswith("at://"):
        return None
    # Strip "at://" prefix, split on "/"
    path = at_uri[5:]
    parts = path.split("/", 1)
    if not parts:
        return None
    did = parts[0]
    if did.startswith("did:"):
        return did
    return None


def should_filter_repost(reposter_did: str, subject_uri: str) -> bool:
    """Decide whether a repost should be filtered from the feed.

    Returns True if this is a self-repost of a recent post (<24h).

    Args:
        reposter_did: DID of the person who reposted
        subject_uri: AT URI of the original post being reposted
    """
    # Step 1: Is this a self-repost? (reposter == original author)
    original_author = parse_did_from_uri(subject_uri)
    if original_author is None:
        return False  # Can't parse — let it through

    if reposter_did != original_author:
        return False  # Not a self-repost — let it through

    # Step 2: Is the original post recent (<24h)?
    post = db.get_post(subject_uri)
    if post is None:
        # Post not in our index — created before the service started.
        # Almost certainly >24h old. Let it through.
        return False

    try:
        # Parse the created_at timestamp
        created_str = post["created_at"]
        # Handle both formats: with and without 'Z' suffix
        if created_str.endswith("Z"):
            created_str = created_str[:-1] + "+00:00"
        created_at = datetime.fromisoformat(created_str)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        age = datetime.now(timezone.utc) - created_at
        max_age = timedelta(hours=SELF_REPOST_MAX_AGE_HOURS)

        if age < max_age:
            return True  # Recent self-repost — FILTER IT
        else:
            return False  # Old self-repost — let it through
    except (ValueError, TypeError):
        # Can't parse timestamp — let it through
        return False
