#!/usr/bin/env python3
"""
Slack Notification Helper

Sends messages to Slack for remote notifications.
Part of the helpers/ tooling for Claude-to-user communication.

Usage:
    python helpers/slack_notify.py "Your message here"
    python helpers/slack_notify.py --channel general "Message to #general"
    python helpers/slack_notify.py --urgent "Critical issue!"

Arguments:
    message         The message to send
    --channel       Target channel (default: claude-notifications)
    --urgent        Add urgent emoji prefix
    --code          Format message as code block
    --title         Add a bold title above the message

Examples:
    python helpers/slack_notify.py "Build completed successfully"
    python helpers/slack_notify.py --urgent "Tests failing - need review"
    python helpers/slack_notify.py --title "Security Scan" --code "No issues found"

Environment:
    SLACK_BOT_TOKEN  Bot OAuth token (xoxb-...) in .env file
"""

import argparse
import sys
import os
from pathlib import Path

# Load environment variables from project root
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def add_reaction(channel: str, timestamp: str, emoji: str = "white_check_mark") -> dict:
    """
    Add a reaction to a Slack message.

    Args:
        channel: Channel ID (e.g., C0A8LB49E1M)
        timestamp: Message timestamp (e.g., 1768621161.846209)
        emoji: Emoji name without colons (default: white_check_mark)

    Returns:
        Slack API response dict
    """
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        raise ValueError("SLACK_BOT_TOKEN not found in environment. Check .env file.")

    client = WebClient(token=token)

    response = client.reactions_add(
        channel=channel,
        timestamp=timestamp,
        name=emoji
    )

    return response


def send_slack_message(
    message: str,
    channel: str = "claude-notifications",
    urgent: bool = False,
    code_block: bool = False,
    title: str = None
) -> dict:
    """
    Send a message to Slack.

    Args:
        message: The message content
        channel: Target channel name (without #)
        urgent: Add urgent indicator
        code_block: Format as code block
        title: Optional bold title

    Returns:
        Slack API response dict

    Raises:
        SlackApiError: If message fails to send
        ValueError: If token not configured
    """
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        raise ValueError("SLACK_BOT_TOKEN not found in environment. Check .env file.")

    client = WebClient(token=token)

    # Build message
    text_parts = []

    if urgent:
        text_parts.append(":rotating_light: *URGENT*")

    if title:
        text_parts.append(f"*{title}*")

    if code_block:
        text_parts.append(f"```{message}```")
    else:
        text_parts.append(message)

    full_message = "\n".join(text_parts)

    # Send message
    response = client.chat_postMessage(
        channel=f"#{channel}",
        text=full_message,
        mrkdwn=True
    )

    return response


def main():
    parser = argparse.ArgumentParser(
        description="Send notifications to Slack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "message",
        nargs="?",
        help="Message to send"
    )
    parser.add_argument(
        "--channel", "-c",
        default="claude-notifications",
        help="Target channel (default: claude-notifications)"
    )
    parser.add_argument(
        "--urgent", "-u",
        action="store_true",
        help="Mark as urgent"
    )
    parser.add_argument(
        "--code",
        action="store_true",
        help="Format as code block"
    )
    parser.add_argument(
        "--title", "-t",
        help="Add a title"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send a test message"
    )
    parser.add_argument(
        "--react",
        action="store_true",
        help="Add a reaction instead of sending a message"
    )
    parser.add_argument(
        "--timestamp", "-ts",
        help="Message timestamp for reaction (required with --react)"
    )
    parser.add_argument(
        "--emoji", "-e",
        default="white_check_mark",
        help="Emoji name for reaction (default: white_check_mark)"
    )

    args = parser.parse_args()

    # Handle reaction mode
    if args.react:
        if not args.timestamp:
            parser.error("--timestamp required with --react")
        try:
            # Channel needs to be ID format for reactions
            # Known channel mappings (bot may not have channels:read scope)
            CHANNEL_IDS = {
                "claude-notifications": "C0A8LB49E1M",
            }
            channel_id = args.channel.replace("#", "")
            if not channel_id.startswith("C"):
                channel_id = CHANNEL_IDS.get(channel_id)
                if not channel_id:
                    print(f"[ERROR] Channel '{args.channel}' not in known mappings. Use channel ID directly.")
                    return 1
            response = add_reaction(
                channel=channel_id,
                timestamp=args.timestamp,
                emoji=args.emoji
            )
            print(f"[OK] Added :{args.emoji}: reaction")
            return 0
        except SlackApiError as e:
            print(f"[ERROR] Slack API error: {e.response['error']}")
            return 1

    # Handle test mode
    if args.test:
        args.message = "Test message from Claude Code. Slack integration is working!"
        args.title = "Connection Test"

    if not args.message:
        parser.error("Message required (or use --test)")

    try:
        response = send_slack_message(
            message=args.message,
            channel=args.channel,
            urgent=args.urgent,
            code_block=args.code,
            title=args.title
        )
        print(f"[OK] Message sent to #{args.channel}")
        return 0

    except SlackApiError as e:
        print(f"[ERROR] Slack API error: {e.response['error']}")
        if "channel_not_found" in str(e):
            print(f"  Hint: Create #{args.channel} channel in Slack first")
        elif "not_in_channel" in str(e):
            print(f"  Hint: Invite the bot to #{args.channel}")
        return 1

    except ValueError as e:
        print(f"[ERROR] {e}")
        return 1

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
