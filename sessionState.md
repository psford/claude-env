# Session State

Say **"hello!"** to restore context from CLAUDE.md and this file.

---

## Environment

| Component | Status | Notes |
|-----------|--------|-------|
| Git | OK | SSH auth configured |
| GitHub | OK | Branch protection, CI/CD via Actions |
| Python | OK | 3.10+ |
| .NET | OK | .NET 8 (if building .NET apps) |
| WSL2 | OK | Linux sandbox available for development |

---

## Quick Start

```bash
# Install git hooks (after clone)
./scripts/install-hooks.sh

# Use in conjunction with app repos (stock-analyzer, road-trip, etc.)
# This is the development environment repo - it contains helpers, hooks, and setup scripts
```

---

## Where We Left Off

**Last session:** Session state cleared for standalone claude-env repo.

**Purpose:** Claude-env is the development environment containing:
- Git hooks for compliance and safety
- Helper scripts (Python, Bash, PowerShell)
- WSL2 configuration
- Reusable testing and documentation tools

**App projects use this repo's infrastructure:**
- stock-analyzer (Stock analysis .NET app)
- road-trip (Photo location mapping app)
- Other projects may bootstrap from this environment

**Say "night!"** at end of session to save state.
