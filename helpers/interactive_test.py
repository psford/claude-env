#!/usr/bin/env python3
"""
Interactive UI Testing Helper using Playwright

Provides browser automation for testing user interactions like form submissions,
clicks, and navigation. Captures screenshots, API responses, and console messages.

Usage:
    python interactive_test.py analyze http://localhost:5000 AAPL --output result.png
    python interactive_test.py capture-api http://localhost:5000 AAPL
    python interactive_test.py console http://localhost:5000 AAPL

Commands:
    analyze     Search for a stock and take screenshot of results
    capture-api Capture all API responses during stock analysis
    console     Capture console messages during stock analysis

Examples:
    # Analyze AAPL and save screenshot
    python helpers/interactive_test.py analyze http://localhost:5000 AAPL

    # Capture API responses for debugging
    python helpers/interactive_test.py capture-api http://localhost:5000 AAPL

    # Check for console errors
    python helpers/interactive_test.py console http://localhost:5000 AAPL --filter error
"""

import argparse
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright


def analyze_stock(url: str, ticker: str, output: str = None, wait: int = 5000) -> dict:
    """
    Navigate to the app, search for a stock, and capture results.

    Args:
        url: Base URL of the Stock Analyzer app
        ticker: Stock ticker symbol to analyze
        output: Output file path for screenshot (default: {ticker}_analysis.png)
        wait: Wait time in ms after clicking Analyze

    Returns:
        dict with status, screenshot path, and any errors found
    """
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"{ticker}_analysis_{timestamp}.png"

    result = {
        "ticker": ticker,
        "screenshot": output,
        "status": "success",
        "error": None,
        "api_responses": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        # Capture API responses
        def handle_response(response):
            if '/api/' in response.url:
                result["api_responses"].append({
                    "url": response.url,
                    "status": response.status
                })

        page.on('response', handle_response)

        print(f"Loading {url}...")
        page.goto(url, wait_until="networkidle")

        # Type in search box
        print(f"Searching for {ticker}...")
        page.fill('input[placeholder*="Search"]', ticker)
        page.wait_for_timeout(500)

        # Click Analyze
        page.click('button:has-text("Analyze")')

        # Wait for results
        print(f"Waiting for results...")
        page.wait_for_timeout(wait)

        # Check for error message
        error_el = page.query_selector('text=Error Loading Stock Data')
        if error_el:
            result["status"] = "error"
            error_text_el = page.query_selector('.text-red-600, .text-red-700')
            if error_text_el:
                result["error"] = error_text_el.inner_text()

        # Take screenshot
        page.screenshot(path=output, full_page=True)
        print(f"Screenshot saved: {output}")

        browser.close()

    return result


def capture_api_responses(url: str, ticker: str) -> list:
    """
    Capture all API responses during stock analysis.

    Args:
        url: Base URL of the Stock Analyzer app
        ticker: Stock ticker symbol to analyze

    Returns:
        list of API response dicts with url, status, and body preview
    """
    responses = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        def handle_response(response):
            if '/api/' in response.url:
                try:
                    body = response.text()[:200] if response.ok else response.text()
                except:
                    body = "(unable to get body)"
                responses.append({
                    "url": response.url,
                    "status": response.status,
                    "body_preview": body
                })

        page.on('response', handle_response)

        page.goto(url, wait_until="networkidle")
        page.fill('input[placeholder*="Search"]', ticker)
        page.wait_for_timeout(500)
        page.click('button:has-text("Analyze")')
        page.wait_for_timeout(5000)

        browser.close()

    return responses


def capture_console(url: str, ticker: str, filter_type: str = None) -> list:
    """
    Capture console messages during stock analysis.

    Args:
        url: Base URL of the Stock Analyzer app
        ticker: Stock ticker symbol to analyze
        filter_type: Filter by message type (error, warning, log, info)

    Returns:
        list of console message dicts
    """
    messages = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        def handle_console(msg):
            msg_type = msg.type
            if filter_type is None or filter_type.lower() in msg_type.lower():
                messages.append({
                    "type": msg_type,
                    "text": msg.text
                })

        page.on('console', handle_console)

        page.goto(url, wait_until="networkidle")
        page.fill('input[placeholder*="Search"]', ticker)
        page.wait_for_timeout(500)
        page.click('button:has-text("Analyze")')
        page.wait_for_timeout(5000)

        browser.close()

    return messages


def main():
    parser = argparse.ArgumentParser(
        description="Interactive UI testing for Stock Analyzer"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Search for a stock and take screenshot of results"
    )
    analyze_parser.add_argument("url", help="Base URL of the app")
    analyze_parser.add_argument("ticker", help="Stock ticker symbol")
    analyze_parser.add_argument("--output", "-o", help="Output screenshot path")
    analyze_parser.add_argument(
        "--wait", "-w", type=int, default=5000,
        help="Wait time in ms after clicking Analyze"
    )

    # capture-api command
    api_parser = subparsers.add_parser(
        "capture-api",
        help="Capture all API responses during stock analysis"
    )
    api_parser.add_argument("url", help="Base URL of the app")
    api_parser.add_argument("ticker", help="Stock ticker symbol")

    # console command
    console_parser = subparsers.add_parser(
        "console",
        help="Capture console messages during stock analysis"
    )
    console_parser.add_argument("url", help="Base URL of the app")
    console_parser.add_argument("ticker", help="Stock ticker symbol")
    console_parser.add_argument(
        "--filter", "-f",
        help="Filter by message type (error, warning, log, info)"
    )

    args = parser.parse_args()

    if args.command == "analyze":
        result = analyze_stock(args.url, args.ticker, args.output, args.wait)
        print(f"\nAnalysis Result:")
        print(f"  Status: {result['status']}")
        if result['error']:
            print(f"  Error: {result['error']}")
        print(f"  API Responses:")
        for resp in result['api_responses']:
            status_marker = "OK" if resp['status'] == 200 else "FAIL"
            print(f"    [{status_marker}] {resp['status']}: {resp['url']}")

    elif args.command == "capture-api":
        responses = capture_api_responses(args.url, args.ticker)
        print(f"\nAPI Responses for {args.ticker}:")
        for resp in responses:
            status_marker = "OK" if resp['status'] == 200 else "FAIL"
            print(f"[{status_marker}] {resp['status']}: {resp['url']}")
            if resp['status'] != 200:
                print(f"  Body: {resp['body_preview']}")

    elif args.command == "console":
        messages = capture_console(args.url, args.ticker, args.filter)
        print(f"\nConsole Messages for {args.ticker}:")
        for msg in messages:
            print(f"[{msg['type'].upper()}] {msg['text']}")


if __name__ == "__main__":
    main()
