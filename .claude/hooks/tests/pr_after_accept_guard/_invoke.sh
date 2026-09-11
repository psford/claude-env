#!/usr/bin/env bash
# Exit-code hook: PASS=0 / BLOCK=2.
exec "$(dirname "$0")/../_exitcode_driver.sh" "$@"
