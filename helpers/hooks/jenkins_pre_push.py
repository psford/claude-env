#!/usr/bin/env python3
"""
Pre-push hook that triggers Jenkins build and waits for result.
Blocks push if Jenkins build fails.
"""

import os
import sys
import time
import base64
import urllib.request
import urllib.error
import json
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def load_env():
    """Load credentials from .env file."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        return None, None

    user = None
    token = None
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("JENKINS_USER="):
                user = line.split("=", 1)[1]
            elif line.startswith("JENKINS_API_TOKEN="):
                token = line.split("=", 1)[1]

    return user, token


def check_jenkins_running():
    """Check if Jenkins is accessible (403 means it's running but requires auth)."""
    try:
        urllib.request.urlopen("http://localhost:8080/", timeout=5)  # nosec B310 - localhost only
        return True
    except urllib.error.HTTPError as e:
        # 403 Forbidden means Jenkins is running but requires auth
        return e.code == 403
    except Exception:
        return False


def get_auth_header(user, token):
    """Create Basic auth header."""
    credentials = f"{user}:{token}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def get_last_build_number(headers):
    """Get the current last build number."""
    try:
        req = urllib.request.Request(
            "http://localhost:8080/job/StockAnalyzer/api/json",
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310 - localhost only
            data = json.loads(resp.read().decode())
            if data.get("lastBuild"):
                return data["lastBuild"]["number"]
            return 0
    except Exception:
        return 0


def trigger_build(headers):
    """Trigger a Jenkins build."""
    try:
        req = urllib.request.Request(
            "http://localhost:8080/job/StockAnalyzer/build",
            method="POST",
            headers=headers
        )
        urllib.request.urlopen(req, timeout=10)  # nosec B310 - localhost only
        return True
    except urllib.error.HTTPError as e:
        # 201 Created is success for build trigger
        if e.code == 201:
            return True
        return False
    except Exception:
        return False


def wait_for_build(headers, build_number, timeout=300):
    """Wait for a build to complete and return success/failure."""
    url = f"http://localhost:8080/job/StockAnalyzer/{build_number}/api/json"
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310 - localhost only
                data = json.loads(resp.read().decode())

                if data.get("building", True):
                    # Still building
                    time.sleep(5)
                    continue

                result = data.get("result")
                return result == "SUCCESS", result

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Build not started yet
                time.sleep(2)
                continue
            raise
        except Exception:
            time.sleep(2)
            continue

    return False, "TIMEOUT"


def main():
    # Check if Jenkins is running
    if not check_jenkins_running():
        print("\033[33m⚠ Jenkins not running - skipping CI check\033[0m")
        print("  Start Jenkins with: .\\helpers\\jenkins-local.ps1 start")
        return 0  # Don't block push if Jenkins isn't running

    # Load credentials
    user, token = load_env()
    if not user or not token:
        print("\033[33m⚠ Jenkins credentials not found in .env - skipping CI check\033[0m")
        return 0

    headers = get_auth_header(user, token)

    # Get current last build number
    last_build = get_last_build_number(headers)

    print("\033[36m→ Triggering Jenkins CI build...\033[0m")

    # Trigger the build
    if not trigger_build(headers):
        print("\033[31m✗ Failed to trigger Jenkins build\033[0m")
        return 1

    # Wait for new build to appear
    time.sleep(3)
    new_build = get_last_build_number(headers)

    if new_build <= last_build:
        # Build might be queued, wait a bit more
        time.sleep(5)
        new_build = get_last_build_number(headers)

    if new_build <= last_build:
        print("\033[33m⚠ Could not detect new build - push anyway\033[0m")
        return 0

    print(f"\033[36m→ Waiting for build #{new_build} to complete...\033[0m")
    print(f"  View at: http://localhost:8080/job/StockAnalyzer/{new_build}/")

    success, result = wait_for_build(headers, new_build)

    if success:
        print(f"\033[32m✓ Jenkins build #{new_build} passed\033[0m")
        return 0
    else:
        print(f"\033[31m✗ Jenkins build #{new_build} failed: {result}\033[0m")
        print(f"  View logs: http://localhost:8080/job/StockAnalyzer/{new_build}/console")
        print("\033[31m  Push blocked - fix the build before pushing\033[0m")
        return 1


if __name__ == "__main__":
    sys.exit(main())
