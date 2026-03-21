#!/usr/bin/env python3
"""AC (Acceptance Criteria) verification status tracker for WSL2 sandbox setup."""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(SCRIPT_DIR, "ac-status.json")

# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"
BOLD = "\033[1m"


def load_status():
    with open(STATUS_FILE, "r") as f:
        return json.load(f)


def save_status(data):
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def color_status(status, verified_at=None, stale_days=30):
    if status == "verified":
        if verified_at:
            try:
                verified_date = datetime.fromisoformat(verified_at)
                if datetime.now() - verified_date > timedelta(days=stale_days):
                    return YELLOW + "stale" + RESET
            except ValueError:
                pass
        return GREEN + "verified" + RESET
    return RED + "unverified" + RESET


def cmd_status(args):
    data = load_status()
    criteria = data["criteria"]

    print(f"\n{BOLD}AC Verification Status{RESET} (v{data['version']}, updated {data['last_updated']})\n")
    print(f"  {'AC':<8} {'Status':<22} {'Verified By':<14} {'Verified At':<14} Description")
    print(f"  {'─'*8} {'─'*12} {'─'*14} {'─'*14} {'─'*40}")

    for ac_id, ac in sorted(criteria.items()):
        status_display = color_status(ac["status"], ac.get("verified_at"))
        verified_by = ac.get("verified_by") or "—"
        verified_at = ac.get("verified_at") or "—"
        print(f"  {ac_id:<8} {status_display:<22} {verified_by:<14} {verified_at:<14} {ac['description']}")

    verified = sum(1 for ac in criteria.values() if ac["status"] == "verified")
    total = len(criteria)
    print(f"\n  {verified}/{total} verified\n")


def cmd_verify(args):
    data = load_status()
    ac_id = args.ac_id.upper()

    if ac_id not in data["criteria"]:
        print(f"Error: {ac_id} not found in criteria", file=sys.stderr)
        sys.exit(1)

    data["criteria"][ac_id]["status"] = "verified"
    data["criteria"][ac_id]["verified_by"] = "patrick"
    data["criteria"][ac_id]["verified_at"] = datetime.now().strftime("%Y-%m-%d")
    save_status(data)
    print(f"Marked {ac_id} as verified by patrick")


def cmd_stale(args):
    data = load_status()
    criteria = data["criteria"]
    stale_days = args.days
    cutoff = datetime.now() - timedelta(days=stale_days)
    stale = []

    for ac_id, ac in sorted(criteria.items()):
        if ac["status"] == "verified" and ac.get("verified_at"):
            try:
                verified_date = datetime.fromisoformat(ac["verified_at"])
                if verified_date < cutoff:
                    days_ago = (datetime.now() - verified_date).days
                    stale.append((ac_id, ac, days_ago))
            except ValueError:
                pass

    if not stale:
        print(f"No ACs are stale (threshold: {stale_days} days)")
        return

    print(f"\n{YELLOW}{BOLD}Stale ACs{RESET} (verified more than {stale_days} days ago)\n")
    for ac_id, ac, days_ago in stale:
        print(f"  {ac_id:<8} {ac['description']:<45} verified {days_ago} days ago")
    print()


def cmd_reset(args):
    data = load_status()
    ac_id = args.ac_id.upper()

    if ac_id not in data["criteria"]:
        print(f"Error: {ac_id} not found in criteria", file=sys.stderr)
        sys.exit(1)

    data["criteria"][ac_id]["status"] = "unverified"
    data["criteria"][ac_id]["verified_by"] = None
    data["criteria"][ac_id]["verified_at"] = None
    save_status(data)
    print(f"Reset {ac_id} to unverified")


def main():
    parser = argparse.ArgumentParser(description="AC verification status tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Print table of all ACs with status")

    verify_parser = subparsers.add_parser("verify", help="Mark an AC as verified")
    verify_parser.add_argument("ac_id", help="AC identifier (e.g., AC1.1)")

    stale_parser = subparsers.add_parser("stale", help="List ACs verified more than N days ago")
    stale_parser.add_argument("--days", type=int, default=30, help="Staleness threshold in days (default: 30)")

    reset_parser = subparsers.add_parser("reset", help="Mark an AC back to unverified")
    reset_parser.add_argument("ac_id", help="AC identifier (e.g., AC1.1)")

    args = parser.parse_args()

    commands = {
        "status": cmd_status,
        "verify": cmd_verify,
        "stale": cmd_stale,
        "reset": cmd_reset,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
