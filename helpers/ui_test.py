#!/usr/bin/env python3
"""
UI Testing Helper using Playwright

Provides headless browser automation for verifying UI changes.
Takes screenshots, checks element visibility, and runs basic assertions.

Usage:
    python ui_test.py screenshot http://localhost:5000 --output page.png
    python ui_test.py check http://localhost:5000 --selector "#search-btn"
    python ui_test.py smoke http://localhost:5000
    python ui_test.py verify http://localhost:5000 --selectors "#chart,#results"

Commands:
    screenshot  Take a full-page screenshot
    check       Verify an element exists and is visible
    smoke       Run basic smoke test (page loads, no JS errors)
    verify      Check multiple elements exist

Examples:
    # Take screenshot of target application
    python helpers/ui_test.py screenshot http://localhost:5000

    # Verify an element exists
    python helpers/ui_test.py check http://localhost:5000 -s "#element-id"

    # Verify multiple elements after a feature change
    python helpers/ui_test.py verify http://localhost:5000 -s "#element1,#element2"
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def take_screenshot(url: str, output: str = None, full_page: bool = True, wait: int = 2000) -> str:
    """
    Take a screenshot of a webpage.

    Args:
        url: Page URL to screenshot
        output: Output file path (default: screenshot_YYYYMMDD_HHMMSS.png)
        full_page: Capture full scrollable page
        wait: Wait time in ms after page load

    Returns:
        Path to saved screenshot
    """
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"screenshot_{timestamp}.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        print(f"Loading {url}...")
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(wait)

        print(f"Taking screenshot...")
        page.screenshot(path=output, full_page=full_page)

        browser.close()

    print(f"Screenshot saved: {output}")
    return output


def check_element(url: str, selector: str, timeout: int = 5000) -> bool:
    """
    Check if an element exists and is visible.

    Args:
        url: Page URL
        selector: CSS selector for element
        timeout: Max wait time in ms

    Returns:
        True if element found and visible
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        print(f"Loading {url}...")
        page.goto(url, wait_until="networkidle")

        try:
            print(f"Looking for: {selector}")
            element = page.wait_for_selector(selector, timeout=timeout, state="visible")
            if element:
                # Get element info
                box = element.bounding_box()
                text = element.inner_text()[:50] if element.inner_text() else "(no text)"
                print(f"  FOUND: {selector}")
                print(f"    Position: ({box['x']:.0f}, {box['y']:.0f})")
                print(f"    Size: {box['width']:.0f}x{box['height']:.0f}")
                print(f"    Text: {text}")
                browser.close()
                return True
        except PlaywrightTimeout:
            print(f"  NOT FOUND: {selector} (timeout after {timeout}ms)")
            browser.close()
            return False

        browser.close()
        return False


def verify_elements(url: str, selectors: list, timeout: int = 5000) -> dict:
    """
    Verify multiple elements exist on page.

    Args:
        url: Page URL
        selectors: List of CSS selectors
        timeout: Max wait time per element in ms

    Returns:
        Dict of selector -> found (bool)
    """
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        print(f"Loading {url}...")
        page.goto(url, wait_until="networkidle")

        for selector in selectors:
            try:
                element = page.wait_for_selector(selector, timeout=timeout, state="visible")
                results[selector] = element is not None
                status = "FOUND" if results[selector] else "NOT FOUND"
                print(f"  [{status}] {selector}")
            except PlaywrightTimeout:
                results[selector] = False
                print(f"  [NOT FOUND] {selector}")

        browser.close()

    return results


def smoke_test(url: str, timeout: int = 10000) -> dict:
    """
    Run basic smoke test on a page.

    Checks:
    - Page loads without error
    - No JavaScript console errors
    - Basic elements visible

    Args:
        url: Page URL
        timeout: Max wait time in ms

    Returns:
        Dict with test results
    """
    results = {
        "url": url,
        "loaded": False,
        "title": None,
        "js_errors": [],
        "status": "FAIL"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        # Capture console errors
        js_errors = []
        page.on("console", lambda msg: js_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: js_errors.append(str(err)))

        try:
            print(f"Loading {url}...")
            response = page.goto(url, wait_until="networkidle", timeout=timeout)

            results["loaded"] = response.ok if response else False
            results["title"] = page.title()
            results["js_errors"] = js_errors

            # Wait a bit for any delayed JS errors
            page.wait_for_timeout(2000)
            results["js_errors"] = js_errors

            if results["loaded"] and not js_errors:
                results["status"] = "PASS"
            elif results["loaded"]:
                results["status"] = "WARN"  # Loaded but has JS errors

            print(f"\nSmoke Test Results:")
            print(f"  URL: {url}")
            print(f"  Loaded: {'Yes' if results['loaded'] else 'No'}")
            print(f"  Title: {results['title']}")
            print(f"  JS Errors: {len(js_errors)}")
            for err in js_errors[:5]:  # Show first 5 errors
                print(f"    - {err[:100]}")
            print(f"  Status: {results['status']}")

        except Exception as e:
            print(f"Error during smoke test: {e}")
            results["error"] = str(e)

        browser.close()

    return results


def main():
    parser = argparse.ArgumentParser(
        description="UI Testing Helper using Playwright",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Screenshot command
    screenshot_parser = subparsers.add_parser("screenshot", help="Take a screenshot")
    screenshot_parser.add_argument("url", help="Page URL")
    screenshot_parser.add_argument("--output", "-o", help="Output file path")
    screenshot_parser.add_argument("--wait", "-w", type=int, default=2000, help="Wait time after load (ms)")
    screenshot_parser.add_argument("--no-full-page", action="store_true", help="Don't capture full page")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check if element exists")
    check_parser.add_argument("url", help="Page URL")
    check_parser.add_argument("--selector", "-s", required=True, help="CSS selector")
    check_parser.add_argument("--timeout", "-t", type=int, default=5000, help="Timeout in ms")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify multiple elements")
    verify_parser.add_argument("url", help="Page URL")
    verify_parser.add_argument("--selectors", "-s", required=True, help="Comma-separated CSS selectors")
    verify_parser.add_argument("--timeout", "-t", type=int, default=5000, help="Timeout per element in ms")

    # Smoke test command
    smoke_parser = subparsers.add_parser("smoke", help="Run smoke test")
    smoke_parser.add_argument("url", help="Page URL")
    smoke_parser.add_argument("--timeout", "-t", type=int, default=10000, help="Timeout in ms")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "screenshot":
        take_screenshot(
            url=args.url,
            output=args.output,
            full_page=not args.no_full_page,
            wait=args.wait
        )
        return 0

    elif args.command == "check":
        found = check_element(
            url=args.url,
            selector=args.selector,
            timeout=args.timeout
        )
        return 0 if found else 1

    elif args.command == "verify":
        selectors = [s.strip() for s in args.selectors.split(",")]
        results = verify_elements(
            url=args.url,
            selectors=selectors,
            timeout=args.timeout
        )
        all_found = all(results.values())
        print(f"\nResult: {'ALL FOUND' if all_found else 'SOME MISSING'}")
        return 0 if all_found else 1

    elif args.command == "smoke":
        results = smoke_test(url=args.url, timeout=args.timeout)
        return 0 if results["status"] == "PASS" else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
