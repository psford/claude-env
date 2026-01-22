#!/usr/bin/env python3
"""Test all documentation tabs load correctly."""

from playwright.sync_api import sync_playwright
import sys

def test_all_tabs(url: str):
    """Test each tab in the docs page loads content."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Track errors (ignore Cloudflare analytics - intentionally blocked by CSP)
        errors = []
        ignored_patterns = ['cloudflareinsights.com', 'beacon.min.js']
        def on_console(msg):
            if msg.type == "error":
                text = msg.text
                if not any(pattern in text for pattern in ignored_patterns):
                    errors.append(text)
        page.on("console", on_console)

        page.goto(url, wait_until="networkidle")

        # Get all tab buttons
        tabs = page.query_selector_all(".tab-btn, button[data-doc]")
        tab_names = [tab.get_attribute("data-doc") or tab.inner_text() for tab in tabs]

        print(f"Found {len(tabs)} tabs: {tab_names}")

        results = []
        for i, tab in enumerate(tabs):
            tab_name = tab.get_attribute("data-doc") or tab.inner_text()
            tab.click()
            page.wait_for_timeout(2000)  # Wait for content to load

            # Check for error message in content area
            content = page.query_selector("#content, .prose, main")
            content_text = content.inner_text() if content else ""

            if "Error loading" in content_text or "not found" in content_text.lower():
                results.append((tab_name, "FAIL", content_text[:100]))
                print(f"  [{i+1}] {tab_name}: FAIL - {content_text[:50]}...")
            elif len(content_text) < 50:
                results.append((tab_name, "FAIL", "Content too short"))
                print(f"  [{i+1}] {tab_name}: FAIL - Content too short ({len(content_text)} chars)")
            else:
                results.append((tab_name, "PASS", f"{len(content_text)} chars"))
                print(f"  [{i+1}] {tab_name}: PASS ({len(content_text)} chars)")

        browser.close()

        # Summary
        passed = sum(1 for _, status, _ in results if status == "PASS")
        print(f"\nSummary: {passed}/{len(results)} tabs passed")

        if errors:
            print(f"\nConsole errors: {len(errors)}")
            for err in errors[:5]:
                print(f"  - {err[:100]}")

        return passed == len(results) and len(errors) == 0

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000/docs.html"
    success = test_all_tabs(url)
    sys.exit(0 if success else 1)
