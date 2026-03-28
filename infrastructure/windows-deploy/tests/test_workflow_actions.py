#!/usr/bin/env python3
"""
Test suite for Windows App Deployment Pipeline workflow YAML validation.

Tests:
  AC1.5 - Verify vulnerability-scan job exists in workflow and is a dependency of build-and-release
  AC1.6 - Verify all GitHub Actions uses statements are pinned by commit SHA
"""

import os
import re
import sys
import yaml
from pathlib import Path


def load_workflow_yaml(workflow_path):
    """Load and parse the build-release.yml workflow file."""
    if not os.path.exists(workflow_path):
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    with open(workflow_path, 'r') as f:
        return yaml.safe_load(f)


def test_ac1_5_vulnerability_scan_job_exists(workflow_data):
    """
    AC1.5: Verify vulnerability-scan job exists in workflow YAML.

    Assertions:
    - vulnerability-scan job exists in jobs section
    - build-and-release job has vulnerability-scan in its needs list
    """
    print("\n[AC1.5] Testing vulnerability-scan job exists and is a dependency...")

    jobs = workflow_data.get('jobs', {})

    # Check that vulnerability-scan job exists
    if 'vulnerability-scan' not in jobs:
        raise AssertionError("vulnerability-scan job not found in workflow jobs")

    print("  ✓ vulnerability-scan job exists")

    # Check that build-and-release job has vulnerability-scan as a dependency
    build_and_release = jobs.get('build-and-release', {})
    needs = build_and_release.get('needs', [])

    # needs can be a string or a list
    if isinstance(needs, str):
        needs = [needs]

    if 'vulnerability-scan' not in needs:
        raise AssertionError(
            f"build-and-release job does not have vulnerability-scan in needs. "
            f"Found needs: {needs}"
        )

    print("  ✓ build-and-release job depends on vulnerability-scan")
    return True


def test_ac1_6_actions_pinned_by_sha(workflow_data):
    """
    AC1.6: Verify all GitHub Actions are pinned by commit SHA.

    Assertions:
    - All uses statements match pattern: owner/action@<40-char-hex-sha>
    - No uses statements use tags, branches, or unpinned references
    """
    print("\n[AC1.6] Testing all GitHub Actions are pinned by commit SHA...")

    # SHA pattern: exactly 40 hex characters (SHA1)
    sha_pattern = re.compile(r'^[a-f0-9]{40}$')

    # Pattern to extract action and SHA from uses statement
    uses_pattern = re.compile(r'^([a-z0-9\-]+/[a-z0-9\-]+)@([a-zA-Z0-9]+)$')

    unpinned_actions = []
    pinned_count = 0

    jobs = workflow_data.get('jobs', {})

    for job_name, job_config in jobs.items():
        steps = job_config.get('steps', [])

        for step_idx, step in enumerate(steps):
            uses = step.get('uses')

            if not uses:
                # step without uses (run command) is OK
                continue

            # Parse the uses statement
            match = uses_pattern.match(uses)
            if not match:
                unpinned_actions.append({
                    'job': job_name,
                    'step': step_idx,
                    'uses': uses,
                    'reason': 'Invalid format (not owner/action@ref)'
                })
                continue

            action, ref = match.groups()

            # Check if ref is a 40-character hex (commit SHA)
            if sha_pattern.match(ref):
                print(f"  ✓ {action}@{ref[:8]}...")
                pinned_count += 1
            else:
                unpinned_actions.append({
                    'job': job_name,
                    'step': step_idx,
                    'uses': uses,
                    'reason': f'Not pinned by SHA (got "{ref}", expected 40-char hex)'
                })

    if unpinned_actions:
        error_msg = f"Found {len(unpinned_actions)} unpinned action(s):\n"
        for action in unpinned_actions:
            error_msg += (
                f"  - Job: {action['job']}, Step {action['step']}\n"
                f"    uses: {action['uses']}\n"
                f"    Issue: {action['reason']}\n"
            )
        raise AssertionError(error_msg)

    print(f"  ✓ All {pinned_count} GitHub Actions are pinned by commit SHA")
    return True


def main():
    """Run all workflow tests."""
    # Determine the path to the workflow file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workflow_path = os.path.join(script_dir, '..', 'build-release.yml')

    try:
        print("=" * 70)
        print("Windows App Deployment Pipeline - Workflow YAML Tests")
        print("=" * 70)

        # Load the workflow
        workflow_data = load_workflow_yaml(workflow_path)
        print(f"\nLoaded workflow from: {workflow_path}")

        # Run tests
        test_ac1_5_vulnerability_scan_job_exists(workflow_data)
        test_ac1_6_actions_pinned_by_sha(workflow_data)

        print("\n" + "=" * 70)
        print("✓ All tests PASSED")
        print("=" * 70)
        return 0

    except FileNotFoundError as e:
        print(f"\n✗ ERROR: {e}", file=sys.stderr)
        return 1
    except AssertionError as e:
        print(f"\n✗ TEST FAILED:\n{e}", file=sys.stderr)
        return 1
    except yaml.YAMLError as e:
        print(f"\n✗ YAML PARSE ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
