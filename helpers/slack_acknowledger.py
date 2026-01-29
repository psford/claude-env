#!/usr/bin/env python3
"""
Slack Acknowledger - Async Message Acknowledgment Service

Watches slack_inbox.json for messages marked as "read" and sends
acknowledgment reactions to Slack. Runs independently from other processes.

Usage:
    python helpers/slack_acknowledger.py           # Run continuously
    python helpers/slack_acknowledger.py --once    # Process once and exit
    python helpers/slack_acknowledger.py --status  # Show pending acknowledgments

The acknowledger tracks which messages have been acknowledged via a separate
file (slack_acknowledged.json) to avoid duplicate reactions.

Environment:
    SLACK_BOT_TOKEN   Bot OAuth token (xoxb-...)
    SLACK_CHANNEL_ID  Channel ID (default: C0A8LB49E1M)
"""

import json
import sys
import os
import argparse
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
INBOX_FILE = PROJECT_ROOT / "slack_inbox.json"
ACK_FILE = PROJECT_ROOT / "slack_acknowledged.json"
LOG_FILE = PROJECT_ROOT / "slack_acknowledger.log"

# Default channel
DEFAULT_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "C0A8LB49E1M")


def log(message: str, also_print: bool = True):
    """Write to log file and optionally print."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"

    if also_print:
        print(log_line, flush=True)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def load_inbox() -> list:
    """Load inbox messages."""
    if INBOX_FILE.exists():
        try:
            with open(INBOX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def load_acknowledged() -> set:
    """Load set of already-acknowledged message timestamps."""
    if ACK_FILE.exists():
        try:
            with open(ACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("acknowledged", []))
        except json.JSONDecodeError:
            return set()
    return set()


def save_acknowledged(timestamps: set):
    """Save the set of acknowledged timestamps."""
    with open(ACK_FILE, "w", encoding="utf-8") as f:
        json.dump({"acknowledged": list(timestamps), "updated_at": datetime.now().isoformat()}, f, indent=2)


def get_pending_acknowledgments() -> list:
    """Get messages that are read but not yet acknowledged in Slack."""
    inbox = load_inbox()
    acknowledged = load_acknowledged()

    pending = []
    for msg in inbox:
        # Skip unread messages
        if not msg.get("read", False):
            continue

        # Skip already acknowledged
        ts = msg.get("timestamp")
        if ts and ts in acknowledged:
            continue

        # Skip system messages (joins, renames, etc.)
        text = msg.get("text", "")
        if "has joined the channel" in text or "has renamed the channel" in text:
            continue

        pending.append(msg)

    return pending


def acknowledge_message(client: WebClient, channel_id: str, timestamp: str) -> bool:
    """Add acknowledgment reaction to a message."""
    try:
        # Add white_check_mark reaction
        client.reactions_add(
            channel=channel_id,
            timestamp=timestamp,
            name="white_check_mark"
        )
        return True
    except SlackApiError as e:
        if "already_reacted" in str(e):
            # Already has reaction, that's fine
            return True
        if "message_not_found" in str(e):
            # Message was deleted from Slack - mark as acknowledged to stop retrying
            log(f"[WARN] Message {timestamp} not found in Slack (likely deleted), skipping")
            return True
        log(f"[ERROR] Failed to acknowledge {timestamp}: {e}")
        return False
    except Exception as e:
        log(f"[ERROR] Unexpected error acknowledging {timestamp}: {e}")
        return False


def process_acknowledgments(client: WebClient, channel_id: str) -> int:
    """Process all pending acknowledgments. Returns count of newly acknowledged."""
    pending = get_pending_acknowledgments()

    if not pending:
        return 0

    acknowledged = load_acknowledged()
    new_count = 0

    for msg in pending:
        ts = msg.get("timestamp")
        if not ts:
            continue

        # Extract channel ID from the message or use default
        msg_channel = msg.get("channel", "")
        # Channel might be stored as "#C0A8LB49E1M" format
        if msg_channel.startswith("#"):
            msg_channel = msg_channel[1:]
        if not msg_channel or not msg_channel.startswith("C"):
            msg_channel = channel_id

        if acknowledge_message(client, msg_channel, ts):
            acknowledged.add(ts)
            new_count += 1
            log(f"Acknowledged message {msg.get('id')}: {msg.get('text', '')[:40]}...")

    if new_count > 0:
        save_acknowledged(acknowledged)

    return new_count


def run_continuous(interval: int = 5, channel_id: str = None):
    """Run continuously, checking for messages to acknowledge."""
    channel_id = channel_id or DEFAULT_CHANNEL_ID
    bot_token = os.getenv("SLACK_BOT_TOKEN")

    if not bot_token:
        log("[ERROR] SLACK_BOT_TOKEN not found in .env")
        return 1

    client = WebClient(token=bot_token)

    log(f"Starting acknowledger (checking every {interval}s)")
    log("Press Ctrl+C to stop")
    log("-" * 40)

    last_status = datetime.now()

    try:
        while True:
            new_count = process_acknowledgments(client, channel_id)

            # Print status every minute if no activity
            now = datetime.now()
            if new_count == 0 and (now - last_status).seconds >= 60:
                print(f"[{now.strftime('%H:%M:%S')}] Watching for read messages...", flush=True)
                last_status = now

            time.sleep(interval)

    except KeyboardInterrupt:
        log("\nAcknowledger stopped by user.")
        return 0


def show_status():
    """Display acknowledgment status."""
    inbox = load_inbox()
    acknowledged = load_acknowledged()
    pending = get_pending_acknowledgments()

    read_count = sum(1 for m in inbox if m.get("read", False))

    print(f"\n{'='*60}")
    print("SLACK ACKNOWLEDGMENT STATUS")
    print(f"{'='*60}")
    print(f"Total messages in inbox: {len(inbox)}")
    print(f"Read messages: {read_count}")
    print(f"Acknowledged in Slack: {len(acknowledged)}")
    print(f"Pending acknowledgment: {len(pending)}")
    print(f"{'='*60}\n")

    if pending:
        print("PENDING ACKNOWLEDGMENTS:\n")
        for msg in pending:
            print(f"  [{msg.get('id')}] {msg.get('text', '')[:60]}...")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Slack acknowledgment service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process pending acknowledgments once and exit"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show acknowledgment status"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=5,
        help="Check interval in seconds (default: 5)"
    )
    parser.add_argument(
        "--channel",
        type=str,
        default=None,
        help="Channel ID (default: from env or C0A8LB49E1M)"
    )

    args = parser.parse_args()

    if args.status:
        show_status()
        return 0

    channel_id = args.channel or DEFAULT_CHANNEL_ID
    bot_token = os.getenv("SLACK_BOT_TOKEN")

    if not bot_token:
        print("[ERROR] SLACK_BOT_TOKEN not found in .env")
        return 1

    client = WebClient(token=bot_token)

    if args.once:
        new_count = process_acknowledgments(client, channel_id)
        print(f"Acknowledged {new_count} message(s)")
        return 0

    return run_continuous(interval=args.interval, channel_id=channel_id)


if __name__ == "__main__":
    sys.exit(main())
