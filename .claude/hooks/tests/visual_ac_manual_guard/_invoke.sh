#!/usr/bin/env bash
# Exit-code hook: PASS=0 / BLOCK=2, with Bash and Write payloads.
exec "$(dirname "$0")/../_exitcode_driver.sh" "$@"
