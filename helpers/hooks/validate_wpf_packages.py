#!/usr/bin/env python3
"""
Pre-commit hook: Validate WPF .csproj files with pre-release packages.

Rule from CLAUDE.md:
- WPF projects that reference pre-release (alpha/beta/rc) NuGet packages must
  include <IncludePackageReferencesDuringMarkupCompilation>true</...> in a
  PropertyGroup, or XAML markup compilation will silently fail to resolve types
  from those packages.

This hook BLOCKS commits where a WPF .csproj has pre-release PackageReferences
but is missing the required property. No bypass except --no-verify.
"""

import subprocess
import sys
import re
import xml.etree.ElementTree as ET


def get_staged_csproj_files() -> list[str]:
    """Return list of staged .csproj file paths (added, copied, modified, renamed)."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '--', '*.csproj'],
        capture_output=True, text=True
    )
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return files


def is_wpf_project(content: str) -> bool:
    """Return True if the .csproj content defines a WPF project.

    Checks for <UseWPF>true</UseWPF> or <UseWpf>true</UseWpf> in any
    PropertyGroup element, case-insensitively on the element name.
    """
    try:
        root = ET.fromstring(content)  # nosec B314 — local git-staged .csproj, not untrusted XML
    except ET.ParseError:
        return False

    # Strip namespace prefix from tags for robust matching
    for elem in root.iter():
        local = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if local.lower() == 'usewpf' and (elem.text or '').strip().lower() == 'true':
            return True
    return False


def has_prerelease_packages(content: str) -> list[str]:
    """Return list of pre-release package names found in the .csproj content.

    A package is considered pre-release if its Version attribute contains a
    hyphen (e.g. '1.0.0-alpha', '2.3.0-rc.1', '0.1.0-preview.7').
    """
    try:
        root = ET.fromstring(content)  # nosec B314 — local git-staged .csproj, not untrusted XML
    except ET.ParseError:
        return []

    prerelease = []
    for elem in root.iter():
        local = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if local == 'PackageReference':
            include = elem.get('Include') or elem.get('include') or ''
            version = elem.get('Version') or elem.get('version') or ''
            if '-' in version and include:
                prerelease.append(include)
    return prerelease


def has_markup_compilation_property(content: str) -> bool:
    """Return True if the .csproj contains the required markup compilation property.

    Looks for:
        <IncludePackageReferencesDuringMarkupCompilation>true</...>
    in any PropertyGroup.
    """
    try:
        root = ET.fromstring(content)  # nosec B314 — local git-staged .csproj, not untrusted XML
    except ET.ParseError:
        return False

    for elem in root.iter():
        local = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if (local == 'IncludePackageReferencesDuringMarkupCompilation'
                and (elem.text or '').strip().lower() == 'true'):
            return True
    return False


def main() -> int:
    staged = get_staged_csproj_files()
    if not staged:
        return 0

    failed = False

    for path in staged:
        # Read the staged version of the file (index, not working tree)
        result = subprocess.run(
            ['git', 'show', f':{path}'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            # File may be deleted or unreadable — skip
            continue

        content = result.stdout

        if not is_wpf_project(content):
            continue

        prerelease = has_prerelease_packages(content)
        if not prerelease:
            continue

        if not has_markup_compilation_property(content):
            if not failed:
                print("\n" + "=" * 62)
                print("BLOCKED: WPF project has pre-release packages without markup compilation fix")
                print("=" * 62)
            print(f"{path}")
            print(f"  Pre-release packages: {prerelease}")
            print(
                "  Missing: <IncludePackageReferencesDuringMarkupCompilation>"
                "true</IncludePackageReferencesDuringMarkupCompilation>"
            )
            print()
            failed = True

    if failed:
        print("Fix: Add the property to a PropertyGroup in the .csproj file.")
        print("=" * 62 + "\n")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
