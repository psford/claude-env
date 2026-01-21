#!/usr/bin/env python3
"""
Responsive UI Testing Helper

Tests web pages at three viewport sizes:
- Mobile (390x844) - iPhone 12/13/14 size
- Tablet (768x1024) - iPad portrait
- Desktop (1400x900) - Standard laptop

Usage:
    python helpers/responsive_test.py <url> [--output-dir <dir>] [--prefix <name>]
    python helpers/responsive_test.py http://localhost:5000/docs.html
    python helpers/responsive_test.py http://localhost:5000/docs.html --prefix docs
    python helpers/responsive_test.py http://localhost:5000/ --output-dir screenshots

The script saves screenshots for each viewport and reports any JavaScript errors.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: playwright not installed. Run: pip install playwright && playwright install")
    sys.exit(1)


VIEWPORTS = {
    'mobile': {'width': 390, 'height': 844, 'device_scale_factor': 2},
    'tablet': {'width': 768, 'height': 1024, 'device_scale_factor': 2},
    'desktop': {'width': 1400, 'height': 900, 'device_scale_factor': 1},
}


def test_responsive(url: str, output_dir: str = '.', prefix: str = None, verbose: bool = True):
    """
    Test a URL at all three viewport sizes.

    Args:
        url: The URL to test
        output_dir: Directory to save screenshots
        prefix: Optional prefix for screenshot filenames
        verbose: Print progress messages

    Returns:
        dict with results for each viewport
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate prefix from URL if not provided
    if not prefix:
        # Extract page name from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if path:
            prefix = path.replace('/', '_').replace('.html', '').replace('.', '_')
        else:
            prefix = 'index'

    results = {}
    js_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        for viewport_name, viewport_config in VIEWPORTS.items():
            if verbose:
                print(f"Testing {viewport_name} ({viewport_config['width']}x{viewport_config['height']})...")

            context = browser.new_context(
                viewport={'width': viewport_config['width'], 'height': viewport_config['height']},
                device_scale_factor=viewport_config.get('device_scale_factor', 1)
            )
            page = context.new_page()

            # Collect JavaScript errors
            viewport_errors = []
            page.on('pageerror', lambda err: viewport_errors.append(str(err)))
            page.on('console', lambda msg: viewport_errors.append(f"Console {msg.type}: {msg.text}") if msg.type == 'error' else None)

            try:
                page.goto(url, wait_until='networkidle', timeout=30000)

                # Take screenshot
                screenshot_name = f"{prefix}_{viewport_name}.png"
                screenshot_path = output_path / screenshot_name
                page.screenshot(path=str(screenshot_path), full_page=False)

                # Get page title for verification
                title = page.title()

                results[viewport_name] = {
                    'status': 'success',
                    'screenshot': str(screenshot_path),
                    'title': title,
                    'viewport': f"{viewport_config['width']}x{viewport_config['height']}",
                    'js_errors': viewport_errors if viewport_errors else None
                }

                if viewport_errors:
                    js_errors.extend([(viewport_name, err) for err in viewport_errors])

                if verbose:
                    print(f"  [OK] Screenshot saved: {screenshot_path}")
                    if viewport_errors:
                        print(f"  [WARN] {len(viewport_errors)} JS error(s) detected")

            except Exception as e:
                results[viewport_name] = {
                    'status': 'error',
                    'error': str(e),
                    'viewport': f"{viewport_config['width']}x{viewport_config['height']}"
                }
                if verbose:
                    print(f"  [FAIL] Error: {e}")

            finally:
                context.close()

        browser.close()

    # Summary
    if verbose:
        print("\n" + "=" * 50)
        print("RESPONSIVE TEST SUMMARY")
        print("=" * 50)
        success_count = sum(1 for r in results.values() if r['status'] == 'success')
        print(f"Passed: {success_count}/{len(VIEWPORTS)}")

        if js_errors:
            print(f"\nJavaScript Errors ({len(js_errors)}):")
            for viewport, error in js_errors:
                print(f"  [{viewport}] {error[:100]}...")

        print(f"\nScreenshots saved to: {output_path.absolute()}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Test responsive design at mobile, tablet, and desktop viewport sizes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s http://localhost:5000/docs.html
  %(prog)s http://localhost:5000/ --prefix homepage
  %(prog)s https://psfordtaurus.com/docs.html --output-dir ./screenshots
        """
    )
    parser.add_argument('url', help='URL to test')
    parser.add_argument('--output-dir', '-o', default='.', help='Directory to save screenshots (default: current)')
    parser.add_argument('--prefix', '-p', help='Prefix for screenshot filenames (auto-generated from URL if not specified)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress progress output')

    args = parser.parse_args()

    results = test_responsive(
        url=args.url,
        output_dir=args.output_dir,
        prefix=args.prefix,
        verbose=not args.quiet
    )

    # Exit with error code if any tests failed
    if any(r['status'] == 'error' for r in results.values()):
        sys.exit(1)

    # Exit with warning code if JS errors detected
    if any(r.get('js_errors') for r in results.values()):
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
