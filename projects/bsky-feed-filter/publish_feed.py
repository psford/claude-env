"""One-time script to register the feed generator with Bluesky.

Run this AFTER the server is deployed and reachable at the HOSTNAME.
Requires BLUESKY_HANDLE and BLUESKY_APP_PASSWORD environment variables.

Usage:
    python publish_feed.py          # Register the feed
    python publish_feed.py --delete  # Unregister the feed
"""

import argparse
import os
import sys

from atproto import Client

from config import HOSTNAME, BLUESKY_HANDLE, BLUESKY_APP_PASSWORD, FEED_URI, SERVICE_DID


def main():
    parser = argparse.ArgumentParser(description="Register/unregister the Bluesky feed")
    parser.add_argument("--delete", action="store_true", help="Unregister the feed")
    args = parser.parse_args()

    if not BLUESKY_APP_PASSWORD:
        print("ERROR: BLUESKY_APP_PASSWORD not set", file=sys.stderr)
        print("Set it in .env or as an environment variable", file=sys.stderr)
        sys.exit(1)

    # Log in
    client = Client()
    print(f"Logging in as @{BLUESKY_HANDLE}...")
    client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
    print(f"Logged in. DID: {client.me.did}")

    if args.delete:
        # Delete the feed generator record
        rkey = "clean-following"
        try:
            client.app.bsky.feed.generator.delete(client.me.did, rkey)
            print(f"Feed '{rkey}' deleted successfully")
        except Exception as e:
            print(f"Error deleting feed: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Create/update the feed generator record
        print(f"Registering feed generator...")
        print(f"  Feed URI:    {FEED_URI}")
        print(f"  Service DID: {SERVICE_DID}")
        print(f"  Hostname:    {HOSTNAME}")

        record = {
            "$type": "app.bsky.feed.generator",
            "did": SERVICE_DID,
            "displayName": "Clean Following",
            "description": (
                "Your Following feed, minus self-reposts of recent posts. "
                "Filters out when someone reposts their own post within 24 hours "
                "(engagement farming). Older self-reposts pass through."
            ),
            "createdAt": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        }

        try:
            response = client.com.atproto.repo.put_record(
                {
                    "repo": client.me.did,
                    "collection": "app.bsky.feed.generator",
                    "rkey": "clean-following",
                    "record": record,
                }
            )
            print(f"\nFeed registered successfully!")
            print(f"URI: {response.uri}")
            print(f"\nNext steps:")
            print(f"  1. Open Bluesky app")
            print(f"  2. Go to Feeds")
            print(f"  3. Search for 'Clean Following' or find it on your profile")
            print(f"  4. Pin it to your feed list")
        except Exception as e:
            print(f"Error registering feed: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
