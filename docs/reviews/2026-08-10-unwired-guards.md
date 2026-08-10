# Unwired guards — the rules I am now responsible for keeping

**2026-08-10.** These 28 hooks were wired in `.claude/settings.local.json` to an
interpreter that does not exist on this machine (`python`, not `python3`). They have
never executed. The configuration asserted protection that was not there.

They are unwired here rather than activated. Each is an unfinished feature, not a
switch: the seven that were turned on this week each needed real debugging before
they were safe, and one of them blocked three legitimate commands within ten
minutes of going live. Finishing 28 more of these buys protection nobody has
demonstrated the value of.

**The files are kept.** Nothing is deleted. Any one can be finished properly later,
with a fixture proving what it refuses and what it must not, which is what
'finished' means for a guard.

**This register exists so the RULES survive the enforcement.** Every line below is
something that used to be someone's intent to prevent. With the hook unwired, the
only thing preventing it is me. Patrick, 2026-08-10: *"If you break any rule these
unwired hooks were designed to stop, the next thing you get to do is write a new
fucking hook."*

| | count |
|---|---|
| could have refused work (exit 2) | 27 |
| advisory only | 1 |
| **total unwired** | **28** |

## Also removed: 7 dead duplicate entries

`deploy_guard`, `deprecation_guard`, `git_commit_guard`, `main_branch_guard`,
`merged_pr_guard`, `post_push_pr_check` and `session_start` each had TWO wirings:
a live one in `~/.claude/settings.json` and a dead `python` one in this repo's
`settings.local.json`. All seven still run, from the global file. The dead
duplicates were removed because they asserted a second, non-existent activation.

**Result: zero dead-wired hooks remain. 36 run; nothing claims to run and
doesn't.**

## How to check this stays true

    python3 - <<'EOF'
    import json, os, re, glob
    H = ".claude/hooks"
    hooks = [n[:-3] for n in os.listdir(H) if n.endswith(".py") and not n.startswith("_")]
    dead = set()
    for p in glob.glob(".claude/settings*.json") + glob.glob(os.path.expanduser("~/.claude/settings*.json")):
        for ev, gs in (json.load(open(p)).get("hooks") or {}).items():
            for g in gs:
                for h in g.get("hooks", []):
                    c = h.get("command", "")
                    for n in hooks:
                        if re.search(rf'\b{n}\.py\b', c) and "python3 " not in c:
                            dead.add(n)
    print("dead-wired:", sorted(dead) or "none")
    EOF

Anything it prints is the configuration lying again.

## Could have refused work

### `api_integration_test_gate`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  API integration test gate. Fires on git commit. When staged files include
  importer source files (anything under */Importers/*.cs or
  */Seeder/*Importer*.cs), runs the live PAD-US integration test. If the test
  fails or the API is unreachable, the commit is blocked. Exit codes: 0 =
  allow commit 2 = block commit (with stderr message)

### `azure_sp_identity_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Azure Service Principal identity guard. Blocks Azure CLI operations when the
  logged-in service principal doesn't match the repo's expected service
  principal. This prevents accidents like running deployment against the wrong
  Azure tenant or service principal, which could cause cross-project
  infrastructure issues. Hook event: PreToolUse (fires BEFORE tool executes)
  Matcher: Bash (only Azure CLI commands) Exit code: 0 (allow), 2 (block with
  error) Timeout: 20s (az account show can be slow)

### `bicep_infra_task_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Bicep infrastructure task guard. Blocks plan phase file commits that
  reference Bicep/KeyVault/RBAC infrastructure without a corresponding
  deployment task in the plan. This prevents implementation plans from
  documenting infrastructure changes without planning how they will actually
  be deployed. Hook event: PreToolUse (fires BEFORE tool executes) Matcher:
  Bash (only git commit commands) Exit code: 0 (allow), 2 (block with error)

### `bicep_kv_name_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Bicep Key Vault name guard. Fires on git commit. Scans staged endpoints.json
  for keyvault source entries (prod only), reads all *.bicep files in repo,
  checks that each vault name appears literally in bicep content. Blocks if a
  name is absent. Exit codes: 0 = allow commit 2 = block commit (with stderr
  message)

### `browser_compat_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Browser compatibility guard. Fires on git commit. When staged
  wwwroot/js/*.js files contain Node.js-only APIs, blocks the commit (exit 2).
  Blocked APIs: setImmediate / clearImmediate process.env / process.argv
  __dirname / __filename Buffer.from / Buffer.alloc require('...')
  module.exports Skip lines annotated with // BROWSER-COMPAT: or that contain
  typeof guards. Exit codes: 0 = allow commit 2 = block commit (with stderr
  message)

### `cherry_pick_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Block cherry-picks of commits already on the current branch. Exit code 2 =
  hard block.

### `constant_change_test_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Constant change test guard. Blocks commit when a C# numeric constant changes
  but the test file isn't staged. Exit code 2 = hard block.

### `develop_pr_state_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Develop PR state guard. Fires on git push. Blocks push to develop when the
  most recent PR from develop to main is merged AND develop has commits ahead
  of origin/main. Uses gh pr list to check PR state. Exit codes: 0 = allow
  push 2 = block push (with stderr message)

### `dotnet_process_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Verify correct dotnet process is serving. Exit code 2 = hard block.

### `endpoint_registry_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Endpoint registry guard. Fires on git commit. Scans staged files for
  hardcoded connection strings and direct env var reads for known endpoint
  keys. Blocks commits that contain these patterns (except in endpoints.json
  itself). Exit codes: 0 = allow commit 2 = block commit (with stderr message)

### `endpoint_schema_validator`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Endpoint schema validator. Fires on git commit. Validates endpoints.json
  against its schema when the file is being committed. Standard library only —
  no external dependencies. Exit codes: 0 = allow commit 2 = block commit
  (with stderr message)

### `engines_node_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Block `npm install` in Node projects that have no version pinning.
  Background: Node version drift between local dev and CI has bitten multiple
  companion projects. stock-analyzer pins NODE_VERSION='20.x' in GH Actions
  but has no .nvmrc and no engines.node in package.json. road-trip similarly.
  photo-portfolio also lacks both. The result is "works on my machine"
  lockfile regenerations, peer-dep skew, and silent install failures when CI
  runner Node major version drifts. What this hook does: - Fires on Bash `npm
  install` / `npm i` / `npm ci` / `pnpm install` / `yarn install` commands. -
  Walks up from the current directory to find the nearest package.json. -
  Blocks (exit 2) if BOTH of the following are true: - package.json has no
  `"engines": {"node": "..."}` entry - the package.json's directory (or any
  parent up to a .git root) has no `.nvmrc` or `.node-version` file - Escape
  hatch: set `ENGINES_NODE_OK=1` in the env (e.g. when installing in a tooling
  repo that genuinely doesn't need a pin), or pass `--ignore-engines` to the
  command.

### `env_contract_coverage_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Environment contract coverage guard. Fires on git commit. Extracts every
  "key" from "source": "env" entries in the dev environment block of
  endpoints.json, then checks all *.cs test files under tests/ for matching
  SetEnvironmentVariable calls. Blocks if any key is missing from tests. Exit
  codes: 0 = allow commit 2 = block commit (with stderr message)

### `js_coordinate_truthiness_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  JS coordinate truthiness guard. Fires on git commit. Blocks when staged
  wwwroot/js/*.js files use truthiness checks on coordinate variables, which
  treat 0 as falsy and silently fall back to wrong values. Detected patterns:
  lat || fallback (OR-fallback — 0 is falsy) lat ? x : y (ternary — not ??
  which is correct) if (lat) (truthiness guard) if (!lng) (negated truthiness
  guard) Coordinate variable names checked: lat, lng, lon, longitude,
  latitude, centroidLat, centroidLng, minLat, maxLat, minLng, maxLng, south,
  north, east, west Skip lines annotated with // COORD-TRUTHY-OK: The correct
  operator is ?? (nullish coalescing), which only falls back on null/undefined
  — not on 0. Exit codes: 0 = allow commit 2 = block commit (with stderr
  message)

### `js_dead_assignment_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  JavaScript dead assignment guard. Fires on git commit. Scans staged
  wwwroot/js/*.js files for patterns where the result of an async call to a
  meaningful-return function is captured in a `const` but never used again
  before the next closing brace at the same indentation level. Meaningful-
  return function name patterns: get, fetch, getIds, find, load, read, query,
  search (prefix or suffix match on the camelCase function name) Skip lines
  annotated with // IGNORE-RETURN: Exit codes: 0 = allow commit 2 = block
  commit (with stderr message)

### `js_module_coverage_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  JS module coverage guard. Blocks commit of new JS source modules >50 LOC
  without test coverage. Exit code 2 = hard block.

### `keyvault_secret_name_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Key Vault secret name guard. Fires on git commit. Validates KV secret names
  conform to Azure naming rules (^[a-zA-Z0-9-]{1,127}$). Checks all "secret"
  fields in keyvault entries across all environments. Exit codes: 0 = allow
  commit 2 = block commit (with stderr message)

### `library_intro_guard`

- **was wired:** PreToolUse/Write (in settings.local.json)
- **rule it encoded:**

  Library introduction research gate. Blocks Write of HTML/csproj that adds a
  new CDN script or NuGet package without a corresponding design-plan or
  research doc. Exit code 2 = hard block.

### `manifest_completeness_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Block commits that add or rename a hook / helper file without a
  corresponding entry in tooling-manifest.json. Background: tooling-
  manifest.json is the public contract that claude-mac-env's setup.sh consumes
  to drive tiered feature selection. On 2026-06-08, audit found .claude/hooks/
  contained 54 Python scripts but the manifest declared only 8 — 46 tools were
  invisible to bootstrap. Patrick's intent for claude-env is that it BE the
  source of shared tooling knowledge for new projects; that requires the
  manifest to be complete. What this hook does: - Fires on `git commit` Bash
  invocations from inside the claude-env repo. - Identifies staged
  additions/renames under: - .claude/hooks/*.py - helpers/*.{py,sh,ps1} -
  helpers/hooks/*.py - Cross-references each against tooling-manifest.json's
  `tools[].source`. - Blocks (exit 2) if any new file is missing an entry. -
  Escape hatch: a `<!-- MANIFEST-EXEMPT: reason -->` in the commit command, or
  `MANIFEST_EXEMPT=1` in the env.

### `mock_test_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Mock-only test guard. Fires on git commit. Detects new C# test files that
  use only mocks (Mock<T>, Substitute.For<T>) without constructing real
  objects. Pure mock tests give false confidence — they validate wiring, not
  behavior. Blocks commit (exit 2) when detected. Allowlist: // MOCK-ONLY:
  annotation, files in /Unit/ directories.

### `plan_api_url_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Plan API URL guard. Fires on git commit. When NEWLY ADDED markdown files in
  docs/implementation-plans/ or docs/design-plans/ contain external API URLs
  (ArcGIS, nationalmap.gov, usgs.gov/arcgis, developer.nps.gov/api, overpass-
  api.de), the commit is blocked unless: - The file contains an <!-- API-
  VERIFIED: ... --> annotation, OR - The file contains an <!-- API-URL-
  UNVERIFIED-OK: ... --> annotation, OR - A corresponding docs/api-
  contracts/*.json contract file exists. Exit codes: 0 = allow commit 2 =
  block commit (with stderr message)

### `plan_branch_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Block phase plan commits that hardcode already-merged or non-existent branch
  names. Background: phase plans frequently include commands like git push -u
  origin feat/visual-design gh pr create --base main ... After the named
  branch merges, the next phase reads the same plan and the hardcoded
  reference is stale. Phase 2 of photo-portfolio's visual-design plan hit this
  — plan said `feat/visual-design`, but that branch was already merged from
  Phase 1, so execution had to deviate to a fresh branch. What this hook does:
  - Fires on `git commit` Bash invocations. - Scans staged
  `docs/implementation-plans/.../phase_*.md` files for branch-like patterns
  (`feat/`, `fix/`, `chore/`, `refactor/`, `docs/`, `test/`, `style/`,
  `perf/`). - For each match, checks whether the named branch is already
  merged into main, or doesn't exist at all. - Blocks (exit 2) if any matches
  qualify. Lists violations with file path, line number, and offending branch
  name. - Escape hatch: a `<!-- BRANCH-OK: reason -->` comment on the same
  line suppresses the check (e.g. when intentionally referencing historical
  context).

### `plan_commit_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Block git push when plan docs are untracked. Exit code 2 = hard block.

### `plan_config_drift_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Plan-config drift guard. Fires on git commit. Scans staged diff for two
  anti-patterns: 1. EXISTENCE-ONLY VERIFICATION in test/verify scripts 2.
  PLACEHOLDER .py files committed to hook directories Allowlist: # EXISTENCE-
  CHECK-OK: reason or # PLACEHOLDER-OK: reason

### `pre_push_merged_branch_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Block git push when the current branch's PR is already merged/closed. Exit
  code 2 = hard block.

### `prices_scan_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Prices table full-scan guard. Fires on git commit. Scans staged diff for
  newly added code that introduces data.Prices table scans — the root cause of
  12 DTU exhaustion incidents on Azure SQL Basic tier (5 DTU / 60 workers).
  Blocks commit (exit 2) when detected. BLOCKED patterns (cause full table
  scan or high DTU): - COUNT(*) on Prices without SecurityAlias filter -
  SELECT DISTINCT on Prices - GROUP BY on Prices without SecurityAlias in the
  key - .CountAsync()/.ToListAsync()/.SumAsync() on _context.Prices without
  Where SAFE patterns (suppressed): - WHERE SecurityAlias = @x -
  SecurityPriceCoverage / CoverageSummary references - TOP 1 ORDER BY - //
  DTU-OK: or -- DTU-OK: annotation

### `workaround_guard`

- **was wired:** PreToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  Workaround-instead-of-root-cause-fix guard. Fires on git commit. Scans
  staged diff for two workaround smells: 1. New Python file in
  helpers/scripts/ duplicating C# business logic 2. C# hard-cap (Math.Min,
  Math.Clamp) at sentinel values without diagnostic comment Blocks commit
  (exit 2) when detected. Allowlist: lines with "# WORKAROUND:" or "// Root
  cause:" comments.

## Advisory only

### `branch_churn_guard`

- **was wired:** PostToolUse/Bash (in settings.local.json)
- **rule it encoded:**

  branch churn / thrash advisory (NEVER blocks). Background: 2026-06-26.
  Approaches tried-then-abandoned within a branch (a commit adds code a later
  commit deletes) are a forensic signal of thrash. This surfaces that after a
  commit, as a nudge. It is ADVISORY ONLY (exit 0) — refactors and normal
  iteration produce the same pattern, so the false-positive rate is high. The
  real control for "stop freelancing" is the pass/fail contract; this is just
  visibility. Lowest-value of the retro mitigations. Signals (advisory): -
  COMMIT COUNT: branch has > COMMIT_WARN commits vs the base branch. - FILE
  REVERSAL: a file's net lines gained on the branch dropped > REVERSAL of its
  peak in a later commit. Exit: always 0.
