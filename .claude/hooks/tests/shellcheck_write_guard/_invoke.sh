#!/usr/bin/env bash
# Judged on exit code; needs its own payload shape, not the runner default.
exec "$(dirname "$0")/../_exitcode_driver.sh" "$@"
