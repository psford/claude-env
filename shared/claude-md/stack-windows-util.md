# Stack: Windows PowerShell Diagnostic Utility

<!-- Canonical source: claude-env/shared/claude-md/stack-windows-util.md. -->
<!-- Shared by gpu-crash-analyzer, win-audio-analyzer, and similar single-file PS diagnostics. -->

## Language & Distribution
- **PowerShell 5.1 only** (ships with Windows; no external modules). ASCII only — non-ASCII characters break the PS 5.1 parser.
- **Zero-dependency, single-file** distribution: each analyzer is one `.ps1` for copy-and-run portability. A standalone monitor/logger script stays separate from the analyzer.

## Testing
- No test framework. Use standalone scripts with manual assertions.
- Tests dot-source the main script; guard the main block with `if ($MyInvocation.InvocationName -ne '.')` so dot-sourcing doesn't execute it.

## Diagnostic Conventions
- **Read-only**: never modify services, registry, or system settings — diagnose only.
- Enumerate every Event Viewer provider queried as an explicit whitelist with its event IDs.
- Deterministic ordering: sort events descending by `TimeCreated` after collection.
- Correlate failures to an anchor event (crash, wake) within a defined time window; state the window.
- Service-restart (SCM) events are the most trusted signal — treat as the smoking gun.

## Output
- Reports are **Markdown** (human-readable, version-controllable); structured capture may also emit JSON.
- Output dirs (`reports/`, `telemetry/`, `captures/`) are gitignored.
- A continuous monitor flushes on every write (`AppendAllText`, no buffering) so data survives a hard crash.
