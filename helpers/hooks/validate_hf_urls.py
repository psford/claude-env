#!/usr/bin/env python3
"""
Pre-commit hook: Validate HuggingFace URLs in staged files.

Rule from CLAUDE.md:
- DIAGNOSE BEFORE FIX: Diagnose root cause first. NEVER guess. Verify before reporting.
- TEST BEFORE SUGGESTING: NEVER tell user to do something without verifying it works.

This hook scans staged .py, .json, .yaml, and .yml files for HuggingFace URLs
and validates each one with a HEAD request before allowing the commit.

- 404: HARD BLOCK — model/file does not exist, commit is rejected.
- 401/403: Soft warning — model may be gated or private.
- Network error (timeout, DNS): Soft warning — could not verify, commit proceeds.
"""

import subprocess
import sys
import re
import urllib.request
import urllib.error

TIMEOUT_SECONDS = 5

HF_URL_PATTERN = re.compile(r'https://huggingface\.co/[^\s\'"<>]+')


def get_staged_file_contents(extensions: list[str]) -> dict[str, str]:
    """Get contents of staged files matching the given extensions."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return {}

    files = {}
    for path in result.stdout.splitlines():
        if not any(path.endswith(ext) for ext in extensions):
            continue
        content_result = subprocess.run(
            ['git', 'show', f':{path}'],
            capture_output=True, text=True
        )
        if content_result.returncode == 0:
            files[path] = content_result.stdout

    return files


def extract_hf_urls(content: str) -> set[str]:
    """Find all HuggingFace URLs in content, deduplicated."""
    return set(HF_URL_PATTERN.findall(content))


def check_url(url: str) -> tuple[int, str]:
    """
    Perform an HTTP HEAD request against url.

    Returns (status_code, reason). On any network error returns (0, error_message).
    """
    req = urllib.request.Request(
        url,
        method='HEAD',
        headers={'User-Agent': 'VoiceTrainer-PreCommitHook/1.0 (github.com/psford/claudeProjects)'}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:  # nosec B310 — URL pattern-matched to huggingface.co only
            return response.status, response.reason
    except urllib.error.HTTPError as exc:
        return exc.code, exc.reason
    except urllib.error.URLError as exc:
        return 0, str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def main() -> int:
    staged = get_staged_file_contents(['.py', '.json', '.yaml', '.yml'])

    # Collect all URLs and track which file each came from.
    url_to_files: dict[str, list[str]] = {}
    for path, content in staged.items():
        for url in extract_hf_urls(content):
            url_to_files.setdefault(url, []).append(path)

    if not url_to_files:
        return 0

    errors: list[tuple[str, str]] = []  # (url, file)

    for url, files in url_to_files.items():
        status, reason = check_url(url)
        file_label = files[0]  # report against the first file found

        if 200 <= status <= 399:
            # URL is reachable and valid.
            pass
        elif status == 404:
            errors.append((url, file_label))
        elif status in (401, 403):
            print(
                f"WARNING: HuggingFace URL returned {status} (may be gated/private)\n"
                f"  URL: {url}\n"
                f"  This URL may require authentication. Verify you have access."
            )
        else:
            # Network error or unexpected status — soft warn.
            print(
                f"WARNING: Could not verify HuggingFace URL (status={status}: {reason})\n"
                f"  URL: {url}\n"
                f"  This URL may require authentication. Verify you have access."
            )

    if errors:
        for url, file_label in errors:
            print(
                "\n" + "=" * 62 + "\n"
                "BLOCKED: HuggingFace URL returned 404 (Not Found)\n"
                + "=" * 62 + "\n"
                f"  URL: {url}\n"
                f"  File: {file_label}\n\n"
                "The model/file does not exist. Verify the URL before committing.\n"
                + "=" * 62
            )
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
