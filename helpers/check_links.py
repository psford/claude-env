#!/usr/bin/env python3
"""
Link Checker for Markdown Files

Validates that all relative links in markdown files point to existing files.
Use this before committing documentation changes.

Usage:
    python helpers/check_links.py README.md
    python helpers/check_links.py stock_analyzer_dotnet/docs/*.md
    python helpers/check_links.py --all  # Check all .md files in repo
"""

import argparse
import re
import sys
from pathlib import Path


def find_markdown_links(content: str) -> list[tuple[str, str]]:
    """
    Extract markdown links from content.
    Returns list of (link_text, link_target) tuples.
    """
    # Match [text](url) pattern, excluding external URLs
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, content)

    # Filter to relative links only (not http/https/mailto)
    relative_links = [
        (text, target)
        for text, target in matches
        if not target.startswith(('http://', 'https://', 'mailto:', '#'))
    ]
    return relative_links


def check_file_links(filepath: Path, repo_root: Path) -> list[dict]:
    """
    Check all relative links in a markdown file.
    Returns list of broken link info dicts.
    """
    broken = []

    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return [{'file': str(filepath), 'error': f'Could not read file: {e}'}]

    links = find_markdown_links(content)
    file_dir = filepath.parent

    for link_text, link_target in links:
        # Remove any anchor from the link
        target_path = link_target.split('#')[0]
        if not target_path:
            continue  # Pure anchor link like (#section)

        # Resolve relative to the markdown file's directory
        full_path = (file_dir / target_path).resolve()

        # Also try relative to repo root (common for README links)
        repo_path = (repo_root / target_path).resolve()

        if not full_path.exists() and not repo_path.exists():
            broken.append({
                'file': str(filepath.relative_to(repo_root)),
                'link_text': link_text,
                'link_target': link_target,
                'checked_paths': [
                    str(full_path.relative_to(repo_root)) if full_path.is_relative_to(repo_root) else str(full_path),
                    str(repo_path.relative_to(repo_root)) if repo_path.is_relative_to(repo_root) else str(repo_path),
                ]
            })

    return broken


def find_all_markdown_files(repo_root: Path) -> list[Path]:
    """Find all markdown files in the repository."""
    return list(repo_root.rglob('*.md'))


def main():
    parser = argparse.ArgumentParser(description='Check markdown links for broken references')
    parser.add_argument('files', nargs='*', help='Markdown files to check')
    parser.add_argument('--all', action='store_true', help='Check all .md files in repository')
    parser.add_argument('--repo-root', type=Path, default=None, help='Repository root directory')
    args = parser.parse_args()

    # Determine repo root
    if args.repo_root:
        repo_root = args.repo_root.resolve()
    else:
        # Try to find repo root by looking for .git
        current = Path.cwd()
        while current != current.parent:
            if (current / '.git').exists():
                repo_root = current
                break
            current = current.parent
        else:
            repo_root = Path.cwd()

    # Gather files to check
    if args.all:
        files = find_all_markdown_files(repo_root)
        # Exclude archive and node_modules
        files = [f for f in files if 'archive' not in f.parts and 'node_modules' not in f.parts]
    elif args.files:
        files = [Path(f).resolve() for f in args.files]
    else:
        parser.print_help()
        sys.exit(1)

    # Check each file
    all_broken = []
    for filepath in files:
        if not filepath.exists():
            print(f"Warning: File not found: {filepath}")
            continue
        broken = check_file_links(filepath, repo_root)
        all_broken.extend(broken)

    # Report results
    if all_broken:
        print(f"\nERROR: Found {len(all_broken)} broken link(s):\n")
        for item in all_broken:
            if 'error' in item:
                print(f"  {item['file']}: {item['error']}")
            else:
                print(f"  {item['file']}:")
                print(f"    [{item['link_text']}]({item['link_target']})")
                print(f"    Checked: {item['checked_paths'][0]}")
        print()
        sys.exit(1)
    else:
        print(f"OK: All links valid in {len(files)} file(s)")
        sys.exit(0)


if __name__ == '__main__':
    main()
