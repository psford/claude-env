#!/usr/bin/env bash
# Advisory hook: judged on what it SAID, not its exit code (always 0).
exec "$(dirname "$0")/../_advisory_driver.sh" "$@"
