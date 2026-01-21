#!/usr/bin/env python3
"""
Favicon Generator

Generates all necessary favicon files from a source image.
Supports PNG, JPG, or any format Pillow can read.

Usage:
    python helpers/generate_favicon.py <source_image>
    python helpers/generate_favicon.py slack_downloads/robin_fat_bird.png
    python helpers/generate_favicon.py --from-slack  # Download latest image from Slack

Output files (in wwwroot/):
    favicon.ico          - ICO with 16, 32, 48px
    favicon-16x16.png    - PNG 16x16
    favicon-32x32.png    - PNG 32x32
    favicon-48x48.png    - PNG 48x48
    favicon-64x64.png    - PNG 64x64
    favicon-128x128.png  - PNG 128x128
    favicon-180x180.png  - PNG 180x180
    favicon-192x192.png  - PNG 192x192 (Android)
    favicon-512x512.png  - PNG 512x512 (PWA)
    apple-touch-icon.png - PNG 180x180 (iOS)
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
WWWROOT = PROJECT_ROOT / "stock_analyzer_dotnet" / "src" / "StockAnalyzer.Api" / "wwwroot"

# Standard favicon sizes
SIZES = [16, 32, 48, 64, 128, 180, 192, 512]
ICO_SIZES = [(16, 16), (32, 32), (48, 48)]


def log(message: str):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def generate_favicons(source_path: str, output_dir: Path = WWWROOT):
    """Generate all favicon files from source image."""

    # Validate source
    source = Path(source_path)
    if not source.exists():
        print(f"ERROR: Source file not found: {source_path}")
        return 1

    # Load and prepare image
    log(f"Loading source: {source}")
    img = Image.open(source)

    # Convert to RGBA for transparency support
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    log(f"Source size: {img.size[0]}x{img.size[1]}")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate PNG files at various sizes
    for size in SIZES:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        output_path = output_dir / f"favicon-{size}x{size}.png"
        resized.save(output_path, 'PNG')
        log(f"Created: favicon-{size}x{size}.png")

    # Generate ICO file with multiple sizes
    ico_images = [img.resize(s, Image.Resampling.LANCZOS) for s in ICO_SIZES]
    ico_path = output_dir / "favicon.ico"
    ico_images[0].save(ico_path, format='ICO', sizes=ICO_SIZES)
    log(f"Created: favicon.ico (16, 32, 48px)")

    # Generate apple-touch-icon
    apple_icon = img.resize((180, 180), Image.Resampling.LANCZOS)
    apple_path = output_dir / "apple-touch-icon.png"
    apple_icon.save(apple_path, 'PNG')
    log(f"Created: apple-touch-icon.png")

    # Update web manifest
    manifest_path = output_dir / "site.webmanifest"
    manifest_content = """{
  "name": "Stock Analyzer",
  "short_name": "StockAnalyzer",
  "icons": [
    {
      "src": "/favicon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/favicon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "theme_color": "#3B82F6",
  "background_color": "#ffffff",
  "display": "standalone"
}
"""
    manifest_path.write_text(manifest_content)
    log(f"Updated: site.webmanifest")

    # Archive original source
    archive_dir = PROJECT_ROOT / "archive" / "favicons"
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = archive_dir / f"{timestamp}_{source.name}"

    # Copy source to archive
    import shutil
    shutil.copy2(source, archive_path)
    log(f"Archived source: {archive_path.name}")

    print(f"\nFavicon generation complete!")
    print(f"Output directory: {output_dir}")
    print(f"\nNext steps:")
    print(f"1. Rebuild the .NET project: dotnet build")
    print(f"2. Test locally: http://localhost:5000")
    print(f"3. Deploy to production when ready")

    return 0


def download_from_slack():
    """Download the latest image from Slack and use it as favicon source."""
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / '.env')

    # Import the slack file download helper
    sys.path.insert(0, str(PROJECT_ROOT / 'helpers'))

    try:
        from slack_file_download import get_pending_files, download_file, update_inbox_file_status
    except ImportError:
        print("ERROR: slack_file_download.py not found")
        return None

    token = os.getenv('SLACK_BOT_TOKEN')
    if not token:
        print("ERROR: SLACK_BOT_TOKEN not set")
        return None

    # Get pending files
    pending = get_pending_files()
    image_files = [p for p in pending if p['file'].get('is_image')]

    if not image_files:
        print("No pending image files in Slack inbox")
        return None

    # Use the most recent image
    latest = image_files[-1]
    file_info = latest['file']

    log(f"Downloading from Slack: {file_info.get('name')}")

    success, result = download_file(file_info, token)
    if success:
        update_inbox_file_status(file_info.get('id'), result)
        return result
    else:
        print(f"ERROR: Download failed: {result}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate favicon files from source image",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'source',
        nargs='?',
        help='Path to source image'
    )
    parser.add_argument(
        '--from-slack',
        action='store_true',
        help='Download latest image from Slack'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        default=str(WWWROOT),
        help=f'Output directory (default: {WWWROOT})'
    )

    args = parser.parse_args()

    if args.from_slack:
        source = download_from_slack()
        if not source:
            return 1
    elif args.source:
        source = args.source
    else:
        parser.print_help()
        return 1

    return generate_favicons(source, Path(args.output))


if __name__ == '__main__':
    sys.exit(main())
