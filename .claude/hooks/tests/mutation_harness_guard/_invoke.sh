#!/usr/bin/env bash
# This guard judges Write/Edit payloads, so fixtures declare TOOL_NAME,
# FILE_PATH and CONTENT rather than COMMAND. The shared exit-code driver
# already builds exactly that payload; delegating keeps one builder.
#
# Without this file the runner falls back to its default path, which sends a
# hardcoded `git commit -m test` Bash payload -- so every fixture here returned
# 0 and the four BLOCK cases "failed" while the four PASS cases passed
# vacuously. That is the trap _exitcode_driver.sh documents at the top.
exec bash "$(dirname "$0")/../_exitcode_driver.sh" "$@"
