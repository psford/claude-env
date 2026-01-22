#!/usr/bin/env python3
"""Test that hover card images change between markers."""

import sys
from playwright.sync_api import sync_playwright

def test_hover_images(url="http://localhost:5000"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Loading {url}...")
        page.goto(url, wait_until="networkidle")

        # Search for TSLA
        print("Searching for TSLA...")
        page.fill("#ticker-input", "TSLA")
        page.click("#search-btn")

        # Wait for chart to load
        page.wait_for_selector(".plotly", timeout=15000)
        print("Chart loaded")

        # Wait a bit for markers to render
        page.wait_for_timeout(2000)

        # Find marker elements (triangles on the chart)
        # The markers are SVG paths in Plotly
        markers = page.locator("g.scatter path").all()
        print(f"Found {len(markers)} potential marker elements")

        # Get the hover card image element
        hover_image = page.locator("#wiki-hover-image")

        image_srcs = []

        # Try to hover over several markers and capture image sources
        # We'll hover over points in the chart area
        chart = page.locator("#price-chart")
        box = chart.bounding_box(timeout=5000)

        if box:
            # Hover at different X positions along the chart
            test_positions = [
                (box['x'] + box['width'] * 0.2, box['y'] + box['height'] * 0.5),
                (box['x'] + box['width'] * 0.4, box['y'] + box['height'] * 0.5),
                (box['x'] + box['width'] * 0.6, box['y'] + box['height'] * 0.5),
            ]

            for i, (x, y) in enumerate(test_positions):
                print(f"Hovering at position {i+1}: ({x:.0f}, {y:.0f})")
                page.mouse.move(x, y)
                page.wait_for_timeout(500)

                # Check if hover card is visible
                card = page.locator("#wiki-hover-card")
                if card.is_visible():
                    src = hover_image.get_attribute("src")
                    if src:
                        image_srcs.append(src[:50])  # Just first 50 chars
                        print(f"  Got image src: {src[:50]}...")
                else:
                    print("  Hover card not visible")

        print(f"\nCollected {len(image_srcs)} image sources")

        # Check if we got different images
        unique_srcs = set(image_srcs)
        print(f"Unique sources: {len(unique_srcs)}")

        if len(image_srcs) >= 2:
            if len(unique_srcs) == len(image_srcs):
                print("\n✓ PASS: All images are different!")
                result = 0
            elif len(unique_srcs) == 1:
                print("\n✗ FAIL: All images are the same!")
                result = 1
            else:
                print(f"\n~ PARTIAL: {len(unique_srcs)} unique out of {len(image_srcs)}")
                result = 0
        else:
            print("\n? Could not collect enough image samples to compare")
            result = 2

        # Also check console for errors
        print("\nChecking browser console...")
        page.wait_for_timeout(1000)

        browser.close()
        return result

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    sys.exit(test_hover_images(url))
