# The spelling that actually occurs. Inside WSL, `wsl` is not a command —
# `wsl.exe` is. The pattern only matched `wsl ` until 2026-08-09, so the guard's
# headline case had never been able to fire.
COMMAND='wsl.exe --status 2>/dev/null'
