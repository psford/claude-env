#!/usr/bin/env bash
# Judged on exit code, and the payload has to be this fixture's own COMMAND:
# the runner's default path sends a hardcoded `git commit -m test`, which
# contains no substitution and would make every case here PASS regardless.
exec "$(dirname "$0")/../_exitcode_driver.sh" "$@"
