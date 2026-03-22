# Monorepo Split Design

## Summary

The `claudeProjects` monorepo currently houses two production applications (Stock Analyzer with its EODHD data loader, and Road Trip Photo Map), plus a collection of Claude Code environment tooling — hooks, helpers, WSL2 setup scripts, and Slack integrations. All of these share a single Git history, a single GitHub Actions configuration, and partially shared Azure infrastructure (Road Trip runs against Stock Analyzer's SQL server). This design splits that monorepo into three purpose-built repositories: `psford/stock-analyzer`, `psford/road-trip`, and `psford/claude-env`.

The split is performed using `git filter-repo`, which rewrites history non-destructively on clones of the original repository, so the source monorepo remains intact until the final archival phase. Each application repo gets its own CI, branch protection, GitHub secrets, and (for Road Trip) its own Azure SQL instance and App Service Plan. The third repo, `claude-env`, is the primary long-term deliverable: it captures the reusable development environment — hooks, helpers, WSL2 scripts — and adds a new `bootstrap.sh` that can fully rebuild a working WSL2 development environment from a fresh clone, pulling secrets from Azure Key Vault at runtime so nothing sensitive is ever committed to Git.

## Definition of Done

Split the `claudeProjects` monorepo into three separate GitHub repositories — **stock-analyzer** (with eodhd-loader), **road-trip**, and **claude-env** (Claude Code environment/tooling) — with full git history preserved via `git filter-repo`. Road Trip gets its own Azure SQL instance (no more shared database). The claude-env repo includes a bootstrap script that can rebuild a WSL2 development environment from scratch (cloning app repos, installing dependencies, prompting for auth) without ever storing secrets. Shared ACR continues for now but Road Trip's deployment is designed for easy ACR migration later. `stephena-away` is archived before the split. T-Tracker and SysTTS already have their own repos and are unaffected.

**Success criteria:**
- Three independent repos with full git history preserved via `git filter-repo`
- Each app repo has its own CI, branch protection, and deployment workflows
- Road Trip fully decoupled from Stock Analyzer (own SQL instance, own Bicep)
- Claude-env repo can bootstrap a fresh WSL2 instance to working dev state (prompts for auth, never stores secrets)
- GitHub Pages docs continue working (Stock Analyzer docs site unaffected)
- Shared ACR continues for now, Road Trip designed for easy ACR migration later
- `stephena-away` archived before split

**Already done (not in scope):**
- T-Tracker already has its own repo (`psford/T-Tracker`, Cloudflare-hosted)
- SysTTS already has its own repo (`psford/SysTTS`)

**Out of scope:**
- Renaming existing Azure resource groups
- App code changes beyond connection strings and paths needed for the split

## Acceptance Criteria

### repo-split.AC1: Git history preserved via filter-repo
- **repo-split.AC1.1 Success:** `git log` in stock-analyzer shows commits that touched `projects/stock-analyzer/` with paths rewritten to root
- **repo-split.AC1.2 Success:** `git log` in road-trip shows commits that touched `projects/road-trip/` with paths rewritten to root
- **repo-split.AC1.3 Success:** `git log` in claude-env shows commits that touched helpers/, infrastructure/wsl/, .claude/, scripts/
- **repo-split.AC1.4 Success:** All branches and tags from the monorepo appear in each filtered repo (for commits relevant to that repo's content)
- **repo-split.AC1.5 Edge:** Empty commits (commits that only touched other repos' files) are pruned automatically

### repo-split.AC2: Independent CI, branch protection, and deployment
- **repo-split.AC2.1 Success:** stock-analyzer CI triggers on push to its repo and passes
- **repo-split.AC2.2 Success:** road-trip CI triggers on push to its repo and passes
- **repo-split.AC2.3 Success:** stock-analyzer deploys to psfordtaurus.com via its own workflow_dispatch
- **repo-split.AC2.4 Success:** road-trip deploys via its own workflow_dispatch
- **repo-split.AC2.5 Success:** Branch protection on main requires PR + passing CI in each app repo
- **repo-split.AC2.6 Failure:** Direct push to main is rejected in both app repos

### repo-split.AC3: Road Trip fully decoupled
- **repo-split.AC3.1 Success:** Road Trip connects to its own Azure SQL server (not Stock Analyzer's)
- **repo-split.AC3.2 Success:** Road Trip has its own App Service Plan in Bicep
- **repo-split.AC3.3 Success:** Road Trip data migrated from shared SQL to own instance
- **repo-split.AC3.4 Success:** Shared ACR (`acrstockanalyzerer34ug`) still receives road-trip images
- **repo-split.AC3.5 Edge:** Changing ACR registry in road-trip workflow requires only updating registry URL + credentials (no code changes)

### repo-split.AC4: Claude-env bootstraps fresh WSL2
- **repo-split.AC4.1 Success:** `bootstrap.sh` on fresh Ubuntu WSL2 clones all 4 app repos (stock-analyzer, road-trip, T-Tracker, SysTTS)
- **repo-split.AC4.2 Success:** `bootstrap.sh` installs .NET 8, Python, Node.js
- **repo-split.AC4.3 Success:** `bootstrap.sh` prompts for `az login` and pulls secrets into `.env`
- **repo-split.AC4.4 Success:** `bootstrap.sh` registers both plugin marketplaces and installs all plugins + hooks
- **repo-split.AC4.5 Success:** `bootstrap.sh` generates VS Code workspace file covering all repos
- **repo-split.AC4.6 Success:** Running `bootstrap.sh` a second time is a no-op (idempotent)
- **repo-split.AC4.7 Failure:** No secrets are stored in any git-tracked file after bootstrap completes

### repo-split.AC5: GitHub Pages docs unaffected
- **repo-split.AC5.1 Success:** `psford.github.io/stock-analyzer` serves docs after split
- **repo-split.AC5.2 Success:** Stock Analyzer app's docs.html fetches from new URL
- **repo-split.AC5.3 Edge:** Old URL (`psford.github.io/claudeProjects`) returns 404 or redirect after monorepo archive

### repo-split.AC6: Pre-split cleanup
- **repo-split.AC6.1 Success:** `stephena-away` and `hook-test` moved to archive/ before split
- **repo-split.AC6.2 Success:** Migration manifest documents every file's source and destination

## Glossary

- **monorepo**: A single Git repository containing multiple independent projects. Here, `claudeProjects` holds two applications and environment tooling under one history.
- **git filter-repo**: A Python tool for rewriting Git history. Used here to extract subdirectories into standalone repos while preserving commit history and pruning commits that touched only unrelated files. Replaces the deprecated `git filter-branch`.
- **`--subdirectory-filter`**: A `git filter-repo` mode that promotes a subdirectory to the repository root, rewriting all paths in history.
- **`--invert-paths`**: A `git filter-repo` flag that removes specified paths and keeps everything else — used to create `claude-env` as the "remainder" after app directories are excluded.
- **`--path-rename`**: A `git filter-repo` option that rewrites a path prefix in history, used to move `projects/stock-analyzer/` to the repo root and `projects/eodhd-loader/` to `eodhd-loader/`.
- **split point**: The commit on `main` after Phase 1 cleanup, used as the consistent baseline from which all three `git filter-repo` operations are performed.
- **eodhd-loader**: A .NET background service that fetches end-of-day stock price data from the EODHD API and bulk-inserts it into the Stock Analyzer database. Shares the `StockAnalyzer.Core` project via a `ProjectReference`.
- **ProjectReference**: A `.csproj` directive that links one .NET project directly to another by path instead of a NuGet package. The eodhd-loader references `StockAnalyzer.Core` this way; the path must be updated when the directory structure changes.
- **Road Trip Photo Map**: A .NET web application that lets users upload geotagged photos and view them on an interactive map. Currently shares Stock Analyzer's Azure SQL server.
- **claude-env**: The new third repository. Contains reusable Claude Code tooling (hooks, helpers, WSL2 scripts) and the bootstrap script — not application code.
- **bootstrap.sh**: A new idempotent shell script (to be created in Phase 6) that provisions a complete WSL2 development environment from scratch: clones all app repos, installs dependencies, authenticates with Azure, pulls secrets, and installs Claude Code plugins and hooks.
- **idempotent**: Safe to run multiple times; subsequent runs detect already-completed steps and skip them rather than re-applying changes.
- **Claude Code hooks**: Python scripts in `.claude/hooks/` that intercept Claude Code operations (commits, pushes, deploys) and enforce policy. Some hooks are application-specific (e.g., `eodhd_rebuild_guard.py`); others are general (branch guard, PR guard).
- **Claude Code plugin**: A packaged extension for the Claude Code CLI, installed from a registered marketplace. `psford/claude-config` serves as Patrick's private marketplace.
- **plugin marketplace**: A GitHub repository registered with the Claude Code CLI as a source of installable plugins. The bootstrap script registers `ed3dai/ed3d-plugins` and `psford/claude-config`.
- **WSL2**: Windows Subsystem for Linux version 2 — the Linux environment running inside Windows where Claude Code operates. Requires its own toolchain setup separate from Windows.
- **Azure SQL DTU**: Data Transfer Units — the resource quota governing Azure SQL capacity. Stock Analyzer runs on a 5-DTU tier with a 60-worker limit, making query consolidation and the Road Trip decoupling important.
- **Bicep**: Microsoft's infrastructure-as-code language for Azure resource deployment. Each app has a `main.bicep` that defines its SQL server, App Service Plan, and related resources.
- **App Service Plan**: An Azure resource that defines the compute tier (CPU, RAM, scaling) shared by one or more App Service web apps. Road Trip currently reuses Stock Analyzer's plan; Phase 4 gives it its own.
- **ACR (Azure Container Registry)**: `acrstockanalyzerer34ug.azurecr.io` — the shared Docker image registry used by both apps. Road Trip continues using it post-split, designed so the registry URL can be swapped later by changing one workflow variable.
- **GitHub Pages**: GitHub's static site hosting, used to serve the Stock Analyzer documentation site. The URL changes from `psford.github.io/claudeProjects` to `psford.github.io/stock-analyzer` after the split.
- **branch protection**: A GitHub repository setting that requires pull requests and passing CI before any commit can land on `main`, and blocks direct pushes.
- **migration manifest**: A companion document (`repo-split-migration-manifest.md`) mapping every monorepo file to its destination repository, used as a post-split audit checklist.
- **pull-secrets.sh**: An existing WSL2 helper script that authenticates with Azure Key Vault and writes API keys and connection strings into a local `.env` file that is never committed to Git.

## Architecture

**Strategy: Extract apps, remainder becomes claude-env.**

Clone the monorepo three times. Filter two clones into app repos (stock-analyzer, road-trip) using `git filter-repo`. Filter the third clone by inverting — remove app directories, leaving tooling as claude-env. Archive the original monorepo as read-only historical reference.

### Repo 1: stock-analyzer

Multi-path extraction. `projects/stock-analyzer/` becomes repo root. `projects/eodhd-loader/` moves to `eodhd-loader/` at root (ProjectReference path updates from `../../../stock-analyzer/src/StockAnalyzer.Core/...` to `../src/StockAnalyzer.Core/...`).

Contents:
- `projects/stock-analyzer/` → root (`src/`, `tests/`, `infrastructure/azure/`, `Dockerfile`, `StockAnalyzer.sln`)
- `projects/eodhd-loader/` → `eodhd-loader/`
- `docs/` → `docs/` (GitHub Pages, served at `psford.github.io/stock-analyzer`)
- SA-specific workflows: `dotnet-ci.yml`, `azure-deploy.yml`, `docs-deploy.yml` → `.github/workflows/`
- SA-specific helpers → `helpers/`: `theme_manager.py`, `theme_schema.py`, `theme_generator.py`, `test_theme_generator.py`, `test_dtu_endpoints.py`, `cloudflare_test.py`, `test_image_api.py`, `load_test.py`
- `ROADMAP.md`
- SA-specific hooks (e.g., `eodhd_rebuild_guard.py`) → `.claude/hooks/`
- New `CLAUDE.md` with SA-specific rules extracted from monorepo CLAUDE.md

Filter approach: `--path projects/stock-analyzer/ --path projects/eodhd-loader/ --path docs/` with `--path-rename` to restructure. SA-specific helpers, workflows, and hooks are copied post-filter (they share git history with non-SA files; filtering them adds complexity for negligible history value).

GitHub Pages URL changes from `psford.github.io/claudeProjects` to `psford.github.io/stock-analyzer`. The app's `docs.html` fetch URL needs a one-time update.

### Repo 2: road-trip

Simple subdirectory extraction. `projects/road-trip/` becomes repo root.

Contents:
- `projects/road-trip/` → root (`src/`, `tests/`, `infrastructure/azure/`, `Dockerfile`, `RoadTripMap.sln`)
- RT workflows: `roadtrip-ci.yml`, `roadtrip-deploy.yml` → `.github/workflows/`
- New `CLAUDE.md` with RT-specific rules

Filter approach: `--subdirectory-filter projects/road-trip/` — single operation, moves everything to root.

Infrastructure changes post-split:
- **New Azure SQL instance** — own SQL server + database via Bicep (currently shares SA's SQL server with `roadtrip` schema)
- **Own App Service Plan** — currently reuses SA's plan via `appServicePlanResourceId` parameter
- **Shared ACR continues** — `acrstockanalyzerer34ug.azurecr.io` still pushes `roadtripmap:latest`, designed for easy ACR migration later (change registry URL + credentials in workflow)
- RT workflows and GitHub secrets (`AZURE_CREDENTIALS`, `ACR_PASSWORD`) recreated in new repo

### Repo 3: claude-env

Remainder after app extraction. This is the primary deliverable — the rebuildable development environment.

Contents (what's left after removing app directories):
- `helpers/` — 9+ reusable tools: `ui_test.py`, `responsive_test.py`, `check_links.py`, `security_scan.py`, `slack_bot.py`, `slack_listener.py`, `slack_notify.py`, `slack_acknowledger.py`, `checkpoint.py`, icon generators, etc.
- `infrastructure/wsl/` — WSL2 setup scripts (`wsl-setup.sh`, `pull-secrets.sh`, `verify-setup.sh`, etc.)
- `.claude/hooks/` — general safety hooks (branch guard, PR guard, deploy guard, merged PR guard, commit guard)
- `scripts/` — install hooks, etc.
- Session files — `CLAUDE.md` (rewritten as meta environment file), `sessionState.md`, `claudeLog.md`, `whileYouWereAway.md`
- `pyproject.toml`
- `runbooks/`

Removed via `--invert-paths`:
- `projects/stock-analyzer/`, `projects/eodhd-loader/`, `projects/road-trip/`
- `projects/stephena-away/`, `projects/hook-test/` (archived before split)
- SA-specific helpers and workflows

**Bootstrap script** (new, key deliverable): An idempotent script that rebuilds a complete WSL2 development environment from scratch:
1. Clone all app repos: `psford/stock-analyzer`, `psford/road-trip`, `psford/T-Tracker`, `psford/SysTTS`
2. Install dependencies (.NET 8, Python, Node.js) — largely what `wsl-setup.sh` already does
3. Prompt for Azure auth (Key Vault access)
4. Pull secrets into `.env` via `pull-secrets.sh` — never stores secrets in git
5. Register Claude Code plugin marketplaces (`ed3dai/ed3d-plugins` from GitHub, `psford/claude-config` for patricks-local)
6. Install all plugins (9 marketplace plugins + 5 standalone hook plugins from claude-config)
7. Install Claude Code hooks into each cloned repo
8. Generate VS Code workspace file pointing at all repos

### Data flow

```
Original monorepo (claudeProjects)
    │
    ├── Clone 1 → git filter-repo (multi-path) → psford/stock-analyzer
    │                                              ├── src/ (StockAnalyzer.Api, StockAnalyzer.Core)
    │                                              ├── eodhd-loader/
    │                                              ├── docs/ (GitHub Pages)
    │                                              ├── helpers/ (SA-specific)
    │                                              └── .github/workflows/ (CI, deploy, docs)
    │
    ├── Clone 2 → git filter-repo (subdirectory) → psford/road-trip
    │                                               ├── src/ (RoadTripMap)
    │                                               ├── infrastructure/azure/ (own SQL, own plan)
    │                                               └── .github/workflows/ (CI, deploy)
    │
    └── Clone 3 → git filter-repo (invert-paths) → psford/claude-env
                                                     ├── helpers/ (reusable tools)
                                                     ├── infrastructure/wsl/
                                                     ├── .claude/hooks/
                                                     ├── scripts/
                                                     └── bootstrap.sh (NEW)
```

### GitHub secrets per repo

| Secret | stock-analyzer | road-trip | claude-env |
|--------|:-:|:-:|:-:|
| `AZURE_CREDENTIALS` | Yes | Yes | No |
| `ACR_PASSWORD` | Yes | Yes | No |
| `FINNHUB_API_KEY` | Yes | No | No |
| `EODHD_API_KEY` | Yes | No | No |

Secrets are manually created in each new GitHub repo from Azure Key Vault values. The bootstrap script handles local dev secrets only.

## Existing Patterns

### git filter-repo

`git filter-repo` is the recommended tool (replaces deprecated `git filter-branch`). Key behaviors:
- Requires fresh clone (safety feature — refuses to run on dirty repos)
- Automatically removes remote references after filtering
- `--subdirectory-filter` moves a subdirectory to root in one operation
- `--path` + `--path-rename` for multi-path extraction with restructuring
- `--invert-paths` removes specified paths, keeping everything else
- Automatically prunes empty commits and runs gc

### WSL2 environment setup

`infrastructure/wsl/wsl-setup.sh` is already idempotent and installs .NET 8, Python, Node.js, SQL tools. `pull-secrets.sh` fetches from Azure Key Vault into `.env`. The bootstrap script builds on these existing scripts rather than replacing them.

### Claude Code plugin system

Plugins are installed via `claude plugin install` from registered marketplaces. `installed_plugins.json` tracks versions and commit SHAs. The existing `psford/claude-config` repo already serves as Patrick's plugin marketplace. The bootstrap script automates the manual registration and installation steps that were done during the WSL2 setup session on 2026-03-21.

### CI workflows

Each project already has its own CI workflow with path filters (`dotnet-ci.yml` filters on `projects/stock-analyzer/**`, `roadtrip-ci.yml` filters on `projects/road-trip/**`). After the split, path filters simplify to `**` since each repo contains only its own code. Workflow structure stays the same.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Pre-Split Cleanup
**Goal:** Prepare the monorepo for a clean split by archiving dead projects and documenting the current state.

**Components:**
- Move `projects/stephena-away/` and `projects/hook-test/` to `archive/`
- Create migration manifest documenting every file's destination (already in progress via background agent)
- Audit `.claude/hooks/` to classify each hook as SA-specific, RT-specific, or general (same analysis as helpers)
- Commit cleanup to develop, merge to main via PR — this becomes the "split point"

**Dependencies:** None (first phase)

**Done when:** Monorepo contains only active projects and tooling, migration manifest exists, split point commit is on main.
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Stock Analyzer Extraction
**Goal:** Extract stock-analyzer (with eodhd-loader) into its own GitHub repo with full git history, CI, and GitHub Pages.

**Components:**
- Clone monorepo → `git filter-repo --path projects/stock-analyzer/ --path projects/eodhd-loader/ --path docs/ --path-rename projects/stock-analyzer/: --path-rename projects/eodhd-loader/:eodhd-loader/`
- Copy SA-specific helpers to `helpers/` in the filtered repo
- Copy SA-specific workflows to `.github/workflows/`
- Copy SA-specific hooks to `.claude/hooks/`
- Update eodhd-loader ProjectReference path (`../../../stock-analyzer/...` → `../src/StockAnalyzer.Core/...`)
- Update workflow path filters (remove `projects/stock-analyzer/` prefix)
- Update `docs-deploy.yml` source paths
- Create SA-specific `CLAUDE.md` from monorepo CLAUDE.md (extract SA rules, DB conventions, deployment, Azure SQL sections)
- Create `psford/stock-analyzer` on GitHub, push all branches and tags
- Enable GitHub Pages on the new repo
- Configure branch protection on `main`
- Create GitHub secrets (`AZURE_CREDENTIALS`, `ACR_PASSWORD`, `FINNHUB_API_KEY`, `EODHD_API_KEY`)
- Update `docs.html` fetch URL from `psford.github.io/claudeProjects` to `psford.github.io/stock-analyzer`

**Dependencies:** Phase 1 (clean split point on main)

**Done when:** `psford/stock-analyzer` builds and passes CI, GitHub Pages serves docs, eodhd-loader ProjectReference resolves, `dotnet build` succeeds for both StockAnalyzer.sln and eodhd-loader.
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Road Trip Extraction
**Goal:** Extract road-trip into its own GitHub repo with full git history and CI.

**Components:**
- Clone monorepo → `git filter-repo --subdirectory-filter projects/road-trip/`
- Copy RT workflows to `.github/workflows/`
- Update workflow path filters
- Create RT-specific `CLAUDE.md`
- Create `psford/road-trip` on GitHub, push all branches and tags
- Configure branch protection on `main`
- Create GitHub secrets (`AZURE_CREDENTIALS`, `ACR_PASSWORD`)

**Dependencies:** Phase 1 (clean split point on main)

**Done when:** `psford/road-trip` builds and passes CI, `dotnet build` succeeds, Dockerfile builds successfully.
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Road Trip Infrastructure Decoupling
**Goal:** Give Road Trip its own Azure SQL instance and App Service Plan, removing dependency on Stock Analyzer's infrastructure.

**Components:**
- New Bicep in `infrastructure/azure/main.bicep`: own SQL server, own database, own App Service Plan
- Update Road Trip connection strings (app code + CI + deploy workflow)
- Migrate existing `roadtrip` schema data from shared SQL server to new instance
- Update `roadtrip-deploy.yml` to use new infrastructure parameters
- Verify ACR image push still works with shared registry

**Dependencies:** Phase 3 (road-trip repo exists)

**Done when:** Road Trip deploys to its own SQL instance, no references to Stock Analyzer's SQL server remain, shared ACR continues working.
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Claude-Env Extraction
**Goal:** Create the claude-env repo from the monorepo remainder — the rebuildable development environment.

**Components:**
- Clone monorepo → `git filter-repo --invert-paths --path projects/stock-analyzer/ --path projects/eodhd-loader/ --path projects/road-trip/ --path projects/stephena-away/ --path projects/hook-test/` plus SA-specific helpers and workflows
- Remove SA-specific helpers from `helpers/`
- Remove app-specific workflows from `.github/workflows/`
- Remove app-specific hooks from `.claude/hooks/`
- Rewrite `CLAUDE.md` as environment-focused meta file (git flow conventions, principles, session protocol — not app-specific rules)
- Create `psford/claude-env` on GitHub, push
- Configure branch protection

**Dependencies:** Phase 1 (clean split point)

**Done when:** `psford/claude-env` contains only reusable tooling, no app-specific code or configuration remains.
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: Bootstrap Script
**Goal:** Create the bootstrap script that rebuilds a complete WSL2 development environment from a fresh claude-env clone.

**Components:**
- `bootstrap.sh` at claude-env repo root — idempotent, safe to re-run
- Repo cloning: `psford/stock-analyzer`, `psford/road-trip`, `psford/T-Tracker`, `psford/SysTTS` into `~/projects/`
- Dependency installation: delegates to existing `infrastructure/wsl/wsl-setup.sh`
- Azure auth: prompts for `az login`, fetches secrets via `pull-secrets.sh`
- Plugin setup: registers marketplaces (`ed3dai/ed3d-plugins`, `psford/claude-config`), installs all 9 plugins + 5 standalone hook plugins
- Hook installation: installs Claude Code hooks into each cloned repo
- Workspace file: generates VS Code `.code-workspace` file pointing at all repos
- Never stores secrets in git — `.env` files are gitignored, secrets fetched at runtime

**Dependencies:** Phase 5 (claude-env repo exists), Phase 2 (stock-analyzer exists), Phase 3 (road-trip exists)

**Done when:** Running `bootstrap.sh` on a fresh WSL2 Ubuntu instance with only `claude-env` cloned produces a fully working development environment with all repos, dependencies, plugins, hooks, and secrets configured. Second run is a no-op.
<!-- END_PHASE_6 -->

<!-- START_PHASE_7 -->
### Phase 7: Validation & Cutover
**Goal:** Validate all three repos work independently, then archive the original monorepo.

**Components:**
- Run CI on all three repos — verify builds and tests pass
- Verify GitHub Pages serves stock-analyzer docs at new URL
- Verify Road Trip deploys to its own infrastructure
- Run bootstrap script on fresh WSL2 to validate end-to-end environment setup
- Cross-reference migration manifest — verify every file landed in the right place
- Archive `psford/claudeProjects` on GitHub (mark read-only, update README to point to new repos)
- Update any external references (Slack bot configs, bookmarks, CLAUDE.md cross-references)

**Dependencies:** All previous phases

**Done when:** All repos build, deploy, and pass CI independently. Bootstrap script produces working environment. Original monorepo is archived with redirect README.
<!-- END_PHASE_7 -->

## Additional Considerations

**Migration manifest:** A comprehensive table mapping every monorepo file to its destination repo is being generated as a companion document (`docs/design-plans/repo-split-migration-manifest.md`). This serves as a post-migration audit tool.

**CLAUDE.md splitting:** The monorepo CLAUDE.md is heavily stock-analyzer-focused. After the split, it needs to be decomposed:
- `claude-env/CLAUDE.md` — git flow, principles, session protocol, environment setup
- `stock-analyzer/CLAUDE.md` — SA-specific rules (Azure SQL DTU, themes, deployment, EF Core migrations, specs)
- `road-trip/CLAUDE.md` — RT-specific rules (already partially exists at `projects/road-trip/CLAUDE.md`)

**Rollback:** If any extraction fails, the original monorepo is untouched (clone-then-filter). No destructive operations on the source until Phase 7 archival.

**Post-split workflow changes:** Developers clone `claude-env` first, run `bootstrap.sh`, then work in individual app repos. Cross-repo changes (e.g., shared hook updates) happen in `claude-env` and are pulled by re-running the bootstrap script or `git pull` in the hook directory.
