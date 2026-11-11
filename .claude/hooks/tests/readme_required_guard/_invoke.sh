#!/usr/bin/env bash
# Judged on the exit code: PASS = 0, BLOCK = 2. The driver commits a README at the
# baseline, so every fixture starts in a repo that has one.
exec "$(dirname "$0")/../_exitcode_driver.sh" "$@"
