# Monorepo Split Design

## Summary
<!-- TO BE GENERATED after body is written -->

## Definition of Done

Split the `claudeProjects` monorepo into four separate GitHub repositories — **stock-analyzer** (with eodhd-loader), **road-trip**, **claude-env** (Claude Code environment/tooling), and **t-tracker** — with full git history preserved via `git filter-repo`. Road Trip gets its own Azure SQL instance (no more shared database). The claude-env repo includes a bootstrap script that can rebuild a WSL2 development environment from scratch (cloning app repos, installing dependencies, prompting for auth) without ever storing secrets. Shared ACR continues for now but Road Trip's deployment is designed for easy ACR migration later. T-Tracker gets its own repo (served from Cloudflare, unaffected by GitHub Pages changes).

**Success criteria:**
- Four independent repos with full git history preserved via `git filter-repo`
- Each app repo has its own CI, branch protection, and deployment workflows
- Road Trip fully decoupled from Stock Analyzer (own SQL instance, own Bicep)
- Claude-env repo can bootstrap a fresh WSL2 instance to working dev state (prompts for auth, never stores secrets)
- GitHub Pages docs continue working (Stock Analyzer docs site unaffected)
- T-Tracker unaffected (Cloudflare-hosted, just needs its own repo)
- Shared ACR continues for now, Road Trip designed for easy ACR migration later

**Out of scope:**
- Renaming existing Azure resource groups
- App code changes beyond connection strings and paths needed for the split

## Acceptance Criteria
<!-- TO BE GENERATED and validated before glossary -->

## Glossary
<!-- TO BE GENERATED after body is written -->
