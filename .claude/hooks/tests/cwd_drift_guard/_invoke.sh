#!/usr/bin/env bash
# Blocking hook: judged by exit code (BLOCK=2, PASS=0).
exec "$(dirname "$0")/../_exitcode_driver.sh" "$@"
