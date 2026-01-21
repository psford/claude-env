#!/usr/bin/env python3
"""
Slack File Download Helper

Safely downloads files from Slack without loading them into the context window.
Files are saved to disk with metadata, preventing session crashes from large files.

Usage:
    python helpers/slack_file_download.py                    # Download all pending files
    python helpers/slack_file_download.py --list             # List files in inbox
    python helpers/slack_file_download.py --id F0AACFKB4E4   # Download specific file by ID
    python helpers/slack_file_download.py --info <path>      # Get metadata for downloaded file

Requirements:
    - Slack bot must have 'files:read' scope (add via api.slack.com/apps)
    - SLACK_BOT_TOKEN in .env file

Downloaded files are saved to: slack_downloads/
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

PROJECT_ROOT = Path(__file__).parent.parent
INBOX_FILE = PROJECT_ROOT / "slack_inbox.json"
DOWNLOADS_DIR = PROJECT_ROOT / "slack_downloads"

# Maximum file size to download (10MB default)
MAX_FILE_SIZE_MB = 10


def log(message: str):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def load_inbox() -> list:
    """Load inbox messages."""
    if INBOX_FILE.exists():
        try:
            with open(INBOX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def get_pending_files() -> list:
    """Get all files from inbox that haven't been downloaded yet."""
    inbox = load_inbox()
    pending = []

    for msg in inbox:
        files = msg.get("files", [])
        for f in files:
            if not f.get("downloaded"):
                pending.append({
                    "file": f,
                    "message_id": msg.get("id"),
                    "message_ts": msg.get("timestamp"),
                    "from_user": msg.get("user")
                })

    return pending


def list_files():
    """List all files in inbox with their download status."""
    inbox = load_inbox()

    print("\n" + "=" * 70)
    print("SLACK FILES IN INBOX")
    print("=" * 70)

    file_count = 0
    for msg in inbox:
        files = msg.get("files", [])
        for f in files:
            file_count += 1
            status = "DOWNLOADED" if f.get("downloaded") else "PENDING"
            size_kb = (f.get("size") or 0) / 1024

            print(f"\n[{status}] {f.get('name', 'unknown')}")
            print(f"  ID: {f.get('id')}")
            print(f"  Type: {f.get('mimetype')}")
            print(f"  Size: {size_kb:.1f} KB")
            print(f"  From: {msg.get('user')} at {msg.get('received_at', 'unknown')}")

            if f.get("downloaded"):
                print(f"  Local path: {f.get('local_path')}")

            if f.get("is_image"):
                dims = f"{f.get('original_w', '?')}x{f.get('original_h', '?')}"
                print(f"  Dimensions: {dims}")

    if file_count == 0:
        print("\nNo files found in inbox.")
    else:
        print(f"\n{'=' * 70}")
        print(f"Total: {file_count} file(s)")

    print()


def download_file(file_info: dict, token: str) -> tuple[bool, str]:
    """
    Download a single file from Slack.

    Args:
        file_info: File metadata dict from inbox
        token: Slack bot token

    Returns:
        Tuple of (success: bool, message: str)
    """
    import requests

    file_id = file_info.get("id")
    file_name = file_info.get("name", f"file_{file_id}")
    file_size = file_info.get("size", 0)
    url = file_info.get("url_private_download") or file_info.get("url_private")

    if not url:
        return False, "No download URL available"

    # Check file size
    size_mb = file_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, f"File too large ({size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB limit)"

    # Create downloads directory
    DOWNLOADS_DIR.mkdir(exist_ok=True)

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in file_name)
    local_path = DOWNLOADS_DIR / f"{timestamp}_{safe_name}"

    # Download file
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=30)

        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"

        # Check content type
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            return False, "Got HTML instead of file - bot may need 'files:read' scope"

        # Save file
        with open(local_path, "wb") as f:
            f.write(response.content)

        # Write metadata file
        metadata = {
            "original_name": file_name,
            "file_id": file_id,
            "mimetype": file_info.get("mimetype"),
            "size": len(response.content),
            "downloaded_at": datetime.now().isoformat(),
            "slack_url": url
        }

        if file_info.get("is_image"):
            metadata["original_dimensions"] = {
                "width": file_info.get("original_w"),
                "height": file_info.get("original_h")
            }

        meta_path = str(local_path) + ".meta.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return True, str(local_path)

    except requests.RequestException as e:
        return False, f"Download failed: {e}"


def update_inbox_file_status(file_id: str, local_path: str):
    """Mark a file as downloaded in the inbox."""
    inbox = load_inbox()

    for msg in inbox:
        files = msg.get("files", [])
        for f in files:
            if f.get("id") == file_id:
                f["downloaded"] = True
                f["local_path"] = local_path
                f["downloaded_at"] = datetime.now().isoformat()

    with open(INBOX_FILE, "w", encoding="utf-8") as out:
        json.dump(inbox, out, indent=2, ensure_ascii=False)


def download_all_pending():
    """Download all pending files from inbox."""
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        print("ERROR: SLACK_BOT_TOKEN not found in .env")
        return 1

    pending = get_pending_files()

    if not pending:
        print("No pending files to download.")
        return 0

    print(f"Found {len(pending)} file(s) to download.\n")

    success_count = 0
    for item in pending:
        f = item["file"]
        file_name = f.get("name", "unknown")
        log(f"Downloading: {file_name}")

        success, result = download_file(f, token)

        if success:
            log(f"  Saved to: {result}")
            update_inbox_file_status(f.get("id"), result)
            success_count += 1
        else:
            log(f"  FAILED: {result}")

    print(f"\nDownloaded {success_count}/{len(pending)} files.")
    return 0 if success_count == len(pending) else 1


def download_by_id(file_id: str):
    """Download a specific file by its Slack file ID."""
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        print("ERROR: SLACK_BOT_TOKEN not found in .env")
        return 1

    # Find file in inbox
    inbox = load_inbox()
    target_file = None

    for msg in inbox:
        files = msg.get("files", [])
        for f in files:
            if f.get("id") == file_id:
                target_file = f
                break
        if target_file:
            break

    if not target_file:
        print(f"File ID '{file_id}' not found in inbox.")
        return 1

    log(f"Downloading: {target_file.get('name', 'unknown')}")
    success, result = download_file(target_file, token)

    if success:
        log(f"Saved to: {result}")
        update_inbox_file_status(file_id, result)
        return 0
    else:
        log(f"FAILED: {result}")
        return 1


def show_file_info(file_path: str):
    """Show metadata for a downloaded file."""
    path = Path(file_path)

    if not path.exists():
        print(f"File not found: {file_path}")
        return 1

    # Check for metadata file
    meta_path = Path(str(path) + ".meta.json")
    if meta_path.exists():
        with open(meta_path) as f:
            metadata = json.load(f)
        print("\nFile Metadata:")
        print(json.dumps(metadata, indent=2))
    else:
        print("\nNo metadata file found.")

    # Get basic file info
    import mimetypes
    mime_type, _ = mimetypes.guess_type(str(path))
    size_kb = path.stat().st_size / 1024

    print(f"\nLocal file info:")
    print(f"  Path: {path}")
    print(f"  Size: {size_kb:.1f} KB")
    print(f"  Type: {mime_type or 'unknown'}")

    # For images, try to get dimensions
    if mime_type and mime_type.startswith("image/"):
        try:
            from PIL import Image
            img = Image.open(path)
            print(f"  Dimensions: {img.size[0]}x{img.size[1]}")
            img.close()
        except Exception:
            pass

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Safely download files from Slack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all files in inbox"
    )
    parser.add_argument(
        "--id",
        type=str,
        help="Download specific file by Slack file ID"
    )
    parser.add_argument(
        "--info",
        type=str,
        metavar="PATH",
        help="Show metadata for a downloaded file"
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=MAX_FILE_SIZE_MB,
        help=f"Maximum file size in MB (default: {MAX_FILE_SIZE_MB})"
    )

    args = parser.parse_args()

    # Update max file size if specified
    if args.max_size != MAX_FILE_SIZE_MB:
        # Use a module-level update pattern instead of global
        globals()['MAX_FILE_SIZE_MB'] = args.max_size

    if args.list:
        list_files()
        return 0

    if args.info:
        return show_file_info(args.info)

    if args.id:
        return download_by_id(args.id)

    # Default: download all pending files
    return download_all_pending()


if __name__ == "__main__":
    sys.exit(main())
