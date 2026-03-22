# Repo Split Migration Manifest

Generated: 2026-03-22
Source monorepo: `psford/claudeProjects`
Tool: exhaustive filesystem enumeration (516 files, excluding .git/, node_modules/, bin/, obj/, __pycache__/)

---

## Destination Repos

| ID | Repo | Purpose |
|----|------|---------|
| **SA** | `psford/stock-analyzer` | Stock Analyzer app + EODHD Loader + GitHub Pages docs |
| **RT** | `psford/road-trip` | Road Trip Photo Map app |
| **CE** | `psford/claude-env` | Claude Code environment: hooks, helpers, infra, session files |
| **ARCH** | *(deleted before split)* | Deprecated projects and archived content — not migrated |

---

## 1. Master Table

> Sorted by source path. All paths are relative from monorepo root.

| Source Path (monorepo) | Dest Repo | Destination Path | Notes |
|------------------------|-----------|-----------------|-------|
| `.claude/hooks/ac_staleness_guard.py` | CE | `.claude/hooks/ac_staleness_guard.py` | |
| `.claude/hooks/artifact_path_guard.py` | CE | `.claude/hooks/artifact_path_guard.py` | |
| `.claude/hooks/assert_verify_guard.py` | CE | `.claude/hooks/assert_verify_guard.py` | |
| `.claude/hooks/deploy_guard.py` | CE | `.claude/hooks/deploy_guard.py` | |
| `.claude/hooks/deprecation_guard.py` | CE | `.claude/hooks/deprecation_guard.py` | |
| `.claude/hooks/ef_migration_guard.py` | CE | `.claude/hooks/ef_migration_guard.py` | |
| `.claude/hooks/eodhd_rebuild_guard.py` | CE | `.claude/hooks/eodhd_rebuild_guard.py` | References `projects/eodhd-loader/` path → update to `eodhd-loader/` |
| `.claude/hooks/fix_commit_smell_guard.py` | CE | `.claude/hooks/fix_commit_smell_guard.py` | |
| `.claude/hooks/git_commit_guard.py` | CE | `.claude/hooks/git_commit_guard.py` | |
| `.claude/hooks/js_test_theater_guard.py` | CE | `.claude/hooks/js_test_theater_guard.py` | |
| `.claude/hooks/main_branch_guard.py` | CE | `.claude/hooks/main_branch_guard.py` | |
| `.claude/hooks/merged_pr_guard.py` | CE | `.claude/hooks/merged_pr_guard.py` | |
| `.claude/hooks/mock_test_guard.py` | CE | `.claude/hooks/mock_test_guard.py` | |
| `.claude/hooks/plan_config_drift_guard.py` | CE | `.claude/hooks/plan_config_drift_guard.py` | |
| `.claude/hooks/plan_phase_count_guard.py` | CE | `.claude/hooks/plan_phase_count_guard.py` | |
| `.claude/hooks/post_push_pr_check.py` | CE | `.claude/hooks/post_push_pr_check.py` | |
| `.claude/hooks/prices_scan_guard.py` | CE | `.claude/hooks/prices_scan_guard.py` | |
| `.claude/hooks/retro_trigger_guard.py` | CE | `.claude/hooks/retro_trigger_guard.py` | |
| `.claude/hooks/session_start.py` | CE | `.claude/hooks/session_start.py` | |
| `.claude/hooks/shellcheck_write_guard.py` | CE | `.claude/hooks/shellcheck_write_guard.py` | |
| `.claude/hooks/spec_staleness_guard.py` | CE | `.claude/hooks/spec_staleness_guard.py` | `SPEC_PATH` hardcoded to `projects/stock-analyzer/docs/TECHNICAL_SPEC.md` → update to `docs/TECHNICAL_SPEC.md` (SA repo) or remove |
| `.claude/hooks/stderr_suppression_guard.py` | CE | `.claude/hooks/stderr_suppression_guard.py` | |
| `.claude/hooks/workaround_guard.py` | CE | `.claude/hooks/workaround_guard.py` | |
| `.claude/settings.local.json` | CE | `.claude/settings.local.json` | Windows paths referencing `claudeProjects` → update to new repo path |
| `.env` | CE | `.env` | Not committed — copy manually; gitignored in all repos |
| `.github/CODEOWNERS` | CE | `.github/CODEOWNERS` | |
| `.github/PULL_REQUEST_TEMPLATE.md` | CE | `.github/PULL_REQUEST_TEMPLATE.md` | Also copy to SA and RT repos |
| `.github/dependabot.yml` | CE | `.github/dependabot.yml` | Monorepo paths → update per repo |
| `.github/workflows/azure-deploy.yml` | SA | `.github/workflows/azure-deploy.yml` | Remove `projects/stock-analyzer/` path prefix throughout |
| `.github/workflows/branch-guard.yml` | CE | `.github/workflows/branch-guard.yml` | Repo-agnostic; also copy to SA and RT |
| `.github/workflows/branch-hygiene.yml` | CE | `.github/workflows/branch-hygiene.yml` | Repo-agnostic; also copy to SA and RT |
| `.github/workflows/codeql.yml` | CE | `.github/workflows/codeql.yml` | Split: SA gets C# analysis; CE gets Python analysis; RT gets its own |
| `.github/workflows/docs-deploy.yml` | SA | `.github/workflows/docs-deploy.yml` | Remove monorepo path prefixes; sources now at repo root |
| `.github/workflows/dotnet-ci.yml` | SA | `.github/workflows/dotnet-ci.yml` | Remove `projects/stock-analyzer/` path prefix; update SOLUTION_PATH |
| `.github/workflows/roadtrip-ci.yml` | RT | `.github/workflows/roadtrip-ci.yml` | Remove `projects/road-trip/` prefix; update SOLUTION_PATH |
| `.github/workflows/roadtrip-deploy.yml` | RT | `.github/workflows/roadtrip-deploy.yml` | Remove `projects/road-trip/` prefix |
| `.github/workflows/test-connectivity.yml` | SA | `.github/workflows/test-connectivity.yml` | Stock Analyzer specific |
| `.gitignore` | CE | `.gitignore` | Also create repo-specific .gitignores for SA and RT |
| `.pre-commit-config.yaml` | CE | `.pre-commit-config.yaml` | |
| `.secrets.baseline` | CE | `.secrets.baseline` | |
| `CLAUDE.md` | CE | `CLAUDE.md` | Remove stock-analyzer-specific sections that move to SA repo's CLAUDE.md |
| `Jenkinsfile` | CE | `Jenkinsfile` | |
| `LICENSE` | CE | `LICENSE` | Also copy to SA and RT |
| `README.md` | CE | `README.md` | Update to describe claude-env repo purpose |
| `archive/claude_backups/CLAUDE_v1_original.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01132026-1.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01132026-2.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01132026-3.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01132026-4.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01132026-5.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01132026-6.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01132026-7.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01142026-1.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01142026-2.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01142026-3.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01142026-4.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01152026-1.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01152026-2.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01162026-1.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01162026-2.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01172026-1.md` | ARCH | *(deleted)* | |
| `archive/claude_backups/claude_01172026-2.md` | ARCH | *(deleted)* | |
| `archive/docs/DEPLOYMENT_ORACLE.md` | ARCH | *(deleted)* | |
| `archive/stock_analysis_python/app.py` | ARCH | *(deleted)* | Deprecated Python stock analysis |
| `archive/stock_analysis_python/dependencies.md` | ARCH | *(deleted)* | |
| `archive/stock_analysis_python/stock_analyzer.py` | ARCH | *(deleted)* | |
| `claudeLog.md` | CE | `claudeLog.md` | Session log |
| `claudeProjects.code-workspace` | CE | `claude-env.code-workspace` | Rename; update workspace folder paths to new repos |
| `docs/APP_EXPLANATION.md` | SA | `docs/APP_EXPLANATION.md` | GitHub Pages content for stock-analyzer |
| `docs/CI_CD_SECURITY_PLAN.md` | SA | `docs/CI_CD_SECURITY_PLAN.md` | Stock Analyzer CI/CD specific |
| `docs/CI_CD_SETUP.md` | SA | `docs/CI_CD_SETUP.md` | References `github.com/psford/claudeProjects` → update to SA repo URL |
| `docs/DEPLOYMENT_AZURE.md` | SA | `docs/DEPLOYMENT_AZURE.md` | |
| `docs/FUNCTIONAL_SPEC.md` | SA | `docs/FUNCTIONAL_SPEC.md` | GitHub Pages; synced from `projects/stock-analyzer/docs/FUNCTIONAL_SPEC.md` |
| `docs/PRIVACY_POLICY.md` | SA | `docs/PRIVACY_POLICY.md` | |
| `docs/SECURITY_OVERVIEW.md` | SA | `docs/SECURITY_OVERVIEW.md` | |
| `docs/TECHNICAL_SPEC.md` | SA | `docs/TECHNICAL_SPEC.md` | GitHub Pages URL references → update to new repo |
| `docs/claude_disp.md` | SA | `docs/claude_disp.md` | GitHub Pages content |
| `docs/design-plans/2026-02-23-pipeline-dtu-fix.md` | SA | `docs/design-plans/2026-02-23-pipeline-dtu-fix.md` | Stock Analyzer design plan |
| `docs/design-plans/2026-02-25-secmaster-mic.md` | SA | `docs/design-plans/2026-02-25-secmaster-mic.md` | |
| `docs/design-plans/2026-03-19-road-trip-map.md` | RT | `docs/design-plans/2026-03-19-road-trip-map.md` | Road Trip design plan |
| `docs/design-plans/2026-03-20-wsl2-claude-sandbox.md` | CE | `docs/design-plans/2026-03-20-wsl2-claude-sandbox.md` | Claude env design plan |
| `docs/design-plans/2026-03-22-repo-split.md` | CE | `docs/design-plans/2026-03-22-repo-split.md` | |
| `docs/design-plans/repo-split-migration-manifest.md` | CE | `docs/design-plans/repo-split-migration-manifest.md` | This file |
| `docs/diagrams/api-endpoints.mmd` | SA | `docs/diagrams/api-endpoints.mmd` | GitHub Pages diagrams |
| `docs/diagrams/data-flow.mmd` | SA | `docs/diagrams/data-flow.mmd` | |
| `docs/diagrams/domain-models.mmd` | SA | `docs/diagrams/domain-models.mmd` | |
| `docs/diagrams/frontend-architecture.mmd` | SA | `docs/diagrams/frontend-architecture.mmd` | |
| `docs/diagrams/image-pipeline.mmd` | SA | `docs/diagrams/image-pipeline.mmd` | |
| `docs/diagrams/project-structure.mmd` | SA | `docs/diagrams/project-structure.mmd` | |
| `docs/diagrams/service-architecture.mmd` | SA | `docs/diagrams/service-architecture.mmd` | |
| `docs/implementation-plans/2026-02-22-ishares-constituent-loader/phase_01.md` | SA | `docs/implementation-plans/2026-02-22-ishares-constituent-loader/phase_01.md` | EODHD Loader implementation plan |
| `docs/implementation-plans/2026-02-22-ishares-constituent-loader/phase_02.md` | SA | `docs/implementation-plans/2026-02-22-ishares-constituent-loader/phase_02.md` | |
| `docs/implementation-plans/2026-02-22-ishares-constituent-loader/phase_03.md` | SA | `docs/implementation-plans/2026-02-22-ishares-constituent-loader/phase_03.md` | |
| `docs/implementation-plans/2026-02-22-ishares-constituent-loader/phase_04.md` | SA | `docs/implementation-plans/2026-02-22-ishares-constituent-loader/phase_04.md` | Contains `C:\Users\patri\Documents\claudeProjects\...` absolute paths — historical, no update needed |
| `docs/implementation-plans/2026-02-22-ishares-constituent-loader/test-requirements.md` | SA | `docs/implementation-plans/2026-02-22-ishares-constituent-loader/test-requirements.md` | |
| `docs/implementation-plans/2026-02-22-ishares-constituent-loader/test-validation-report.md` | SA | `docs/implementation-plans/2026-02-22-ishares-constituent-loader/test-validation-report.md` | Contains historical absolute paths — no update needed |
| `docs/index.html` | SA | `docs/index.html` | GitHub Pages index; references `psford.github.io/claudeProjects/` → update to new Pages URL |
| `docs/retrospectives/2026-02-25-heatmap-fix.md` | SA | `docs/retrospectives/2026-02-25-heatmap-fix.md` | |
| `docs/retrospectives/2026-03-22-wsl2-sandbox-retro-mitigations.md` | CE | `docs/retrospectives/2026-03-22-wsl2-sandbox-retro-mitigations.md` | WSL infra retrospective |
| `docs/test-plans/2026-02-22-ishares-constituent-loader.md` | SA | `docs/test-plans/2026-02-22-ishares-constituent-loader.md` | |
| `docs/test-plans/2026-02-23-pipeline-dtu-fix.md` | SA | `docs/test-plans/2026-02-23-pipeline-dtu-fix.md` | |
| `docs/test-plans/2026-02-25-secmaster-mic.md` | SA | `docs/test-plans/2026-02-25-secmaster-mic.md` | |
| `helpers/Invoke-SpeechToText.ps1` | CE | `helpers/Invoke-SpeechToText.ps1` | Generic helper |
| `helpers/archive_logs.py` | CE | `helpers/archive_logs.py` | |
| `helpers/check_links.py` | CE | `helpers/check_links.py` | |
| `helpers/checkpoint.py` | CE | `helpers/checkpoint.py` | |
| `helpers/cloudflare_test.py` | SA | `helpers/cloudflare_test.py` | Stock Analyzer specific (psfordtaurus.com) |
| `helpers/generate_favicon.py` | CE | `helpers/generate_favicon.py` | Generic icon generation |
| `helpers/generate_minimal_icons.py` | CE | `helpers/generate_minimal_icons.py` | |
| `helpers/generate_solid_icons.py` | CE | `helpers/generate_solid_icons.py` | |
| `helpers/generate_stream_deck_icons.py` | CE | `helpers/generate_stream_deck_icons.py` | |
| `helpers/hooks/block_main_commits.py` | CE | `helpers/hooks/block_main_commits.py` | Git hook helpers |
| `helpers/hooks/check_log_sanitization.py` | CE | `helpers/hooks/check_log_sanitization.py` | |
| `helpers/hooks/check_md_table_totals.py` | CE | `helpers/hooks/check_md_table_totals.py` | |
| `helpers/hooks/check_responsive_tests.py` | CE | `helpers/hooks/check_responsive_tests.py` | |
| `helpers/hooks/check_spec_updates.py` | CE | `helpers/hooks/check_spec_updates.py` | Contains `projects/hook-test/` exclusion → clean up after split |
| `helpers/hooks/commit_atomicity_guard.py` | CE | `helpers/hooks/commit_atomicity_guard.py` | |
| `helpers/hooks/jenkins_pre_push.py` | CE | `helpers/hooks/jenkins_pre_push.py` | |
| `helpers/hooks/validate_doc_links.py` | CE | `helpers/hooks/validate_doc_links.py` | |
| `helpers/hooks/validate_hf_urls.py` | CE | `helpers/hooks/validate_hf_urls.py` | User-Agent references `github.com/psford/claudeProjects` → update to CE repo URL |
| `helpers/hooks/validate_wpf_packages.py` | CE | `helpers/hooks/validate_wpf_packages.py` | |
| `helpers/interactive_test.py` | CE | `helpers/interactive_test.py` | |
| `helpers/load-env.sh` | CE | `helpers/load-env.sh` | |
| `helpers/load_test.py` | SA | `helpers/load_test.py` | Stock Analyzer load test |
| `helpers/responsive_test.py` | CE | `helpers/responsive_test.py` | |
| `helpers/security_scan.py` | CE | `helpers/security_scan.py` | |
| `helpers/slack_acknowledger.py` | CE | `helpers/slack_acknowledger.py` | |
| `helpers/slack_bot.py` | CE | `helpers/slack_bot.py` | |
| `helpers/slack_file_download.py` | CE | `helpers/slack_file_download.py` | |
| `helpers/slack_listener.py` | CE | `helpers/slack_listener.py` | |
| `helpers/slack_notify.py` | CE | `helpers/slack_notify.py` | |
| `helpers/test_docs_tabs.py` | CE | `helpers/test_docs_tabs.py` | |
| `helpers/test_dtu_endpoints.py` | SA | `helpers/test_dtu_endpoints.py` | Stock Analyzer specific |
| `helpers/test_hover_images.py` | CE | `helpers/test_hover_images.py` | |
| `helpers/test_image_api.py` | SA | `helpers/test_image_api.py` | Stock Analyzer specific |
| `helpers/test_theme_generator.py` | SA | `helpers/test_theme_generator.py` | Stock Analyzer theming |
| `helpers/theme_generator.py` | SA | `helpers/theme_generator.py` | |
| `helpers/theme_manager.py` | SA | `helpers/theme_manager.py` | Hardcoded path `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes` → update to `src/StockAnalyzer.Api/wwwroot/themes` |
| `helpers/theme_schema.py` | SA | `helpers/theme_schema.py` | |
| `helpers/ui_test.py` | CE | `helpers/ui_test.py` | |
| `helpers/zap_scan.py` | CE | `helpers/zap_scan.py` | |
| `infrastructure/wsl/CLAUDE.md` | CE | `infrastructure/wsl/CLAUDE.md` | |
| `infrastructure/wsl/ac-status.json` | CE | `infrastructure/wsl/ac-status.json` | |
| `infrastructure/wsl/ac-tracker.py` | CE | `infrastructure/wsl/ac-tracker.py` | |
| `infrastructure/wsl/install-claude-config-hooks.sh` | CE | `infrastructure/wsl/install-claude-config-hooks.sh` | |
| `infrastructure/wsl/populate-keyvault.ps1` | CE | `infrastructure/wsl/populate-keyvault.ps1` | |
| `infrastructure/wsl/pull-secrets.sh` | CE | `infrastructure/wsl/pull-secrets.sh` | Hardcoded `$HOME/projects/claudeProjects` path → update to new CE repo path |
| `infrastructure/wsl/script-audit.md` | CE | `infrastructure/wsl/script-audit.md` | |
| `infrastructure/wsl/test-secrets-roundtrip.sh` | CE | `infrastructure/wsl/test-secrets-roundtrip.sh` | Hardcoded `$HOME/projects/claudeProjects/.env` → update to CE repo path |
| `infrastructure/wsl/verify-setup.sh` | CE | `infrastructure/wsl/verify-setup.sh` | |
| `infrastructure/wsl/wsl-setup.sh` | CE | `infrastructure/wsl/wsl-setup.sh` | Hardcoded `git clone git@github.com:psford/claudeProjects.git` → update to CE repo URL |
| `projects/eodhd-loader/CLAUDE.md` | SA | `eodhd-loader/CLAUDE.md` | Domain contract doc |
| `projects/eodhd-loader/Directory.Build.props` | SA | `eodhd-loader/Directory.Build.props` | |
| `projects/eodhd-loader/EodhdLoader.sln` | SA | `eodhd-loader/EodhdLoader.sln` | No cross-project refs in sln (EodhdLoader.csproj handles the ProjectReference) |
| `projects/eodhd-loader/README.md` | SA | `eodhd-loader/README.md` | |
| `projects/eodhd-loader/docs/TECHNICAL_SPEC.md` | SA | `eodhd-loader/docs/TECHNICAL_SPEC.md` | |
| `projects/eodhd-loader/scripts/README.md` | SA | `eodhd-loader/scripts/README.md` | |
| `projects/eodhd-loader/scripts/backfill-checkpoint.json` | SA | `eodhd-loader/scripts/backfill-checkpoint.json` | |
| `projects/eodhd-loader/src/EodhdLoader/App.xaml` | SA | `eodhd-loader/src/EodhdLoader/App.xaml` | |
| `projects/eodhd-loader/src/EodhdLoader/App.xaml.cs` | SA | `eodhd-loader/src/EodhdLoader/App.xaml.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/AssemblyInfo.cs` | SA | `eodhd-loader/src/EodhdLoader/AssemblyInfo.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Controls/CoverageHeatmapControl.cs` | SA | `eodhd-loader/src/EodhdLoader/Controls/CoverageHeatmapControl.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Controls/HeatmapV2Control.cs` | SA | `eodhd-loader/src/EodhdLoader/Controls/HeatmapV2Control.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Converters.cs` | SA | `eodhd-loader/src/EodhdLoader/Converters.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/CrawlerWindow.xaml` | SA | `eodhd-loader/src/EodhdLoader/CrawlerWindow.xaml` | |
| `projects/eodhd-loader/src/EodhdLoader/CrawlerWindow.xaml.cs` | SA | `eodhd-loader/src/EodhdLoader/CrawlerWindow.xaml.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj` | SA | `eodhd-loader/src/EodhdLoader/EodhdLoader.csproj` | **ProjectReference path changes** — see Section 3 |
| `projects/eodhd-loader/src/EodhdLoader/MainWindow.xaml` | SA | `eodhd-loader/src/EodhdLoader/MainWindow.xaml` | |
| `projects/eodhd-loader/src/EodhdLoader/MainWindow.xaml.cs` | SA | `eodhd-loader/src/EodhdLoader/MainWindow.xaml.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Models/EtfConfig.cs` | SA | `eodhd-loader/src/EodhdLoader/Models/EtfConfig.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Models/ISharesHolding.cs` | SA | `eodhd-loader/src/EodhdLoader/Models/ISharesHolding.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Models/IngestProgress.cs` | SA | `eodhd-loader/src/EodhdLoader/Models/IngestProgress.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Resources/ishares_etf_configs.json` | SA | `eodhd-loader/src/EodhdLoader/Resources/ishares_etf_configs.json` | |
| `projects/eodhd-loader/src/EodhdLoader/Services/BorisService.cs` | SA | `eodhd-loader/src/EodhdLoader/Services/BorisService.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Services/BulkFillService.cs` | SA | `eodhd-loader/src/EodhdLoader/Services/BulkFillService.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Services/ConfigurationService.cs` | SA | `eodhd-loader/src/EodhdLoader/Services/ConfigurationService.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Services/DataAnalysisService.cs` | SA | `eodhd-loader/src/EodhdLoader/Services/DataAnalysisService.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Services/HolidayForwardFillService.cs` | SA | `eodhd-loader/src/EodhdLoader/Services/HolidayForwardFillService.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Services/IISharesConstituentService.cs` | SA | `eodhd-loader/src/EodhdLoader/Services/IISharesConstituentService.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Services/ISharesConstituentService.cs` | SA | `eodhd-loader/src/EodhdLoader/Services/ISharesConstituentService.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Services/PriceCoverageAnalyzer.cs` | SA | `eodhd-loader/src/EodhdLoader/Services/PriceCoverageAnalyzer.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Services/ProdSyncService.cs` | SA | `eodhd-loader/src/EodhdLoader/Services/ProdSyncService.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Services/StockAnalyzerApiClient.cs` | SA | `eodhd-loader/src/EodhdLoader/Services/StockAnalyzerApiClient.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Services/UsMarketCalendar.cs` | SA | `eodhd-loader/src/EodhdLoader/Services/UsMarketCalendar.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Utilities/DateUtilities.cs` | SA | `eodhd-loader/src/EodhdLoader/Utilities/DateUtilities.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/ViewModels/BorisViewModel.cs` | SA | `eodhd-loader/src/EodhdLoader/ViewModels/BorisViewModel.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/ViewModels/BulkFillViewModel.cs` | SA | `eodhd-loader/src/EodhdLoader/ViewModels/BulkFillViewModel.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/ViewModels/CrawlerViewModel.cs` | SA | `eodhd-loader/src/EodhdLoader/ViewModels/CrawlerViewModel.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/ViewModels/DashboardViewModel.cs` | SA | `eodhd-loader/src/EodhdLoader/ViewModels/DashboardViewModel.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/ViewModels/IndexManagerViewModel.cs` | SA | `eodhd-loader/src/EodhdLoader/ViewModels/IndexManagerViewModel.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/ViewModels/MainViewModel.cs` | SA | `eodhd-loader/src/EodhdLoader/ViewModels/MainViewModel.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/ViewModels/ViewModelBase.cs` | SA | `eodhd-loader/src/EodhdLoader/ViewModels/ViewModelBase.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/BorisView.xaml` | SA | `eodhd-loader/src/EodhdLoader/Views/BorisView.xaml` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/BorisView.xaml.cs` | SA | `eodhd-loader/src/EodhdLoader/Views/BorisView.xaml.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/BulkFillView.xaml` | SA | `eodhd-loader/src/EodhdLoader/Views/BulkFillView.xaml` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/BulkFillView.xaml.cs` | SA | `eodhd-loader/src/EodhdLoader/Views/BulkFillView.xaml.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/CrawlerView.xaml` | SA | `eodhd-loader/src/EodhdLoader/Views/CrawlerView.xaml` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/CrawlerView.xaml.cs` | SA | `eodhd-loader/src/EodhdLoader/Views/CrawlerView.xaml.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/DashboardView.xaml` | SA | `eodhd-loader/src/EodhdLoader/Views/DashboardView.xaml` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/DashboardView.xaml.cs` | SA | `eodhd-loader/src/EodhdLoader/Views/DashboardView.xaml.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/HeatmapTestWindow.xaml` | SA | `eodhd-loader/src/EodhdLoader/Views/HeatmapTestWindow.xaml` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/HeatmapTestWindow.xaml.cs` | SA | `eodhd-loader/src/EodhdLoader/Views/HeatmapTestWindow.xaml.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/IndexManagerView.xaml` | SA | `eodhd-loader/src/EodhdLoader/Views/IndexManagerView.xaml` | |
| `projects/eodhd-loader/src/EodhdLoader/Views/IndexManagerView.xaml.cs` | SA | `eodhd-loader/src/EodhdLoader/Views/IndexManagerView.xaml.cs` | |
| `projects/eodhd-loader/src/EodhdLoader/spider.ico` | SA | `eodhd-loader/src/EodhdLoader/spider.ico` | |
| `projects/eodhd-loader/tests/EodhdLoader.Tests/EodhdLoader.Tests.csproj` | SA | `eodhd-loader/tests/EodhdLoader.Tests/EodhdLoader.Tests.csproj` | ProjectReference is relative within eodhd-loader — no change needed |
| `projects/eodhd-loader/tests/EodhdLoader.Tests/Integration/PipelineParityTests.cs` | SA | `eodhd-loader/tests/EodhdLoader.Tests/Integration/PipelineParityTests.cs` | |
| `projects/eodhd-loader/tests/EodhdLoader.Tests/Integration/RateLimitingTests.cs` | SA | `eodhd-loader/tests/EodhdLoader.Tests/Integration/RateLimitingTests.cs` | |
| `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceDownloadTests.cs` | SA | `eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceDownloadTests.cs` | |
| `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceParsingTests.cs` | SA | `eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceParsingTests.cs` | |
| `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServicePersistenceTests.cs` | SA | `eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServicePersistenceTests.cs` | |
| `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceStalenessTests.cs` | SA | `eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceStalenessTests.cs` | |
| `projects/eodhd-loader/tests/EodhdLoader.Tests/TestData/format_a_sample.json` | SA | `eodhd-loader/tests/EodhdLoader.Tests/TestData/format_a_sample.json` | |
| `projects/eodhd-loader/tests/EodhdLoader.Tests/TestData/format_b_sample.json` | SA | `eodhd-loader/tests/EodhdLoader.Tests/TestData/format_b_sample.json` | |
| `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/CrawlerViewModelConstituentTests.cs` | SA | `eodhd-loader/tests/EodhdLoader.Tests/ViewModels/CrawlerViewModelConstituentTests.cs` | |
| `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/IndexManagerViewModelTests.cs` | SA | `eodhd-loader/tests/EodhdLoader.Tests/ViewModels/IndexManagerViewModelTests.cs` | |
| `archive/hook-test/test_hooks.py` | ARCH | *(deleted)* | Hook test project — archived before split |
| `projects/road-trip/.dockerignore` | RT | `.dockerignore` | |
| `projects/road-trip/.gitignore` | RT | `.gitignore` | |
| `projects/road-trip/CLAUDE.md` | RT | `CLAUDE.md` | |
| `projects/road-trip/Dockerfile` | RT | `Dockerfile` | Contains `projects/road-trip/` context path in roadtrip-deploy.yml — Dockerfile itself is clean |
| `projects/road-trip/RoadTripMap.sln` | RT | `RoadTripMap.sln` | Solution paths are relative — no change needed |
| `projects/road-trip/docs/FUNCTIONAL_SPEC.md` | RT | `docs/FUNCTIONAL_SPEC.md` | |
| `projects/road-trip/docs/TECHNICAL_SPEC.md` | RT | `docs/TECHNICAL_SPEC.md` | |
| `projects/road-trip/infrastructure/azure/main.bicep` | RT | `infrastructure/azure/main.bicep` | |
| `projects/road-trip/infrastructure/azure/parameters.json` | RT | `infrastructure/azure/parameters.json` | |
| `projects/road-trip/src/RoadTripMap/Data/DesignTimeDbContextFactory.cs` | RT | `src/RoadTripMap/Data/DesignTimeDbContextFactory.cs` | |
| `projects/road-trip/src/RoadTripMap/Data/RoadTripDbContext.cs` | RT | `src/RoadTripMap/Data/RoadTripDbContext.cs` | |
| `projects/road-trip/src/RoadTripMap/Entities/GeoCacheEntity.cs` | RT | `src/RoadTripMap/Entities/GeoCacheEntity.cs` | |
| `projects/road-trip/src/RoadTripMap/Entities/PhotoEntity.cs` | RT | `src/RoadTripMap/Entities/PhotoEntity.cs` | |
| `projects/road-trip/src/RoadTripMap/Entities/TripEntity.cs` | RT | `src/RoadTripMap/Entities/TripEntity.cs` | |
| `projects/road-trip/src/RoadTripMap/Helpers/SlugHelper.cs` | RT | `src/RoadTripMap/Helpers/SlugHelper.cs` | |
| `projects/road-trip/src/RoadTripMap/Migrations/20260320032254_InitialCreate.Designer.cs` | RT | `src/RoadTripMap/Migrations/20260320032254_InitialCreate.Designer.cs` | |
| `projects/road-trip/src/RoadTripMap/Migrations/20260320032254_InitialCreate.cs` | RT | `src/RoadTripMap/Migrations/20260320032254_InitialCreate.cs` | |
| `projects/road-trip/src/RoadTripMap/Migrations/20260321220822_AddViewToken.Designer.cs` | RT | `src/RoadTripMap/Migrations/20260321220822_AddViewToken.Designer.cs` | |
| `projects/road-trip/src/RoadTripMap/Migrations/20260321220822_AddViewToken.cs` | RT | `src/RoadTripMap/Migrations/20260321220822_AddViewToken.cs` | |
| `projects/road-trip/src/RoadTripMap/Migrations/RoadTripDbContextModelSnapshot.cs` | RT | `src/RoadTripMap/Migrations/RoadTripDbContextModelSnapshot.cs` | |
| `projects/road-trip/src/RoadTripMap/Models/CreateTripRequest.cs` | RT | `src/RoadTripMap/Models/CreateTripRequest.cs` | |
| `projects/road-trip/src/RoadTripMap/Models/CreateTripResponse.cs` | RT | `src/RoadTripMap/Models/CreateTripResponse.cs` | |
| `projects/road-trip/src/RoadTripMap/Models/PhotoResponse.cs` | RT | `src/RoadTripMap/Models/PhotoResponse.cs` | |
| `projects/road-trip/src/RoadTripMap/Models/TripResponse.cs` | RT | `src/RoadTripMap/Models/TripResponse.cs` | |
| `projects/road-trip/src/RoadTripMap/Program.cs` | RT | `src/RoadTripMap/Program.cs` | |
| `projects/road-trip/src/RoadTripMap/Properties/launchSettings.json` | RT | `src/RoadTripMap/Properties/launchSettings.json` | |
| `projects/road-trip/src/RoadTripMap/RoadTripMap.csproj` | RT | `src/RoadTripMap/RoadTripMap.csproj` | |
| `projects/road-trip/src/RoadTripMap/Services/IAuthStrategy.cs` | RT | `src/RoadTripMap/Services/IAuthStrategy.cs` | |
| `projects/road-trip/src/RoadTripMap/Services/IGeocodingService.cs` | RT | `src/RoadTripMap/Services/IGeocodingService.cs` | |
| `projects/road-trip/src/RoadTripMap/Services/INominatimRateLimiter.cs` | RT | `src/RoadTripMap/Services/INominatimRateLimiter.cs` | |
| `projects/road-trip/src/RoadTripMap/Services/IPhotoService.cs` | RT | `src/RoadTripMap/Services/IPhotoService.cs` | |
| `projects/road-trip/src/RoadTripMap/Services/NominatimGeocodingService.cs` | RT | `src/RoadTripMap/Services/NominatimGeocodingService.cs` | |
| `projects/road-trip/src/RoadTripMap/Services/NominatimRateLimiter.cs` | RT | `src/RoadTripMap/Services/NominatimRateLimiter.cs` | |
| `projects/road-trip/src/RoadTripMap/Services/PhotoService.cs` | RT | `src/RoadTripMap/Services/PhotoService.cs` | |
| `projects/road-trip/src/RoadTripMap/Services/SecretTokenAuthStrategy.cs` | RT | `src/RoadTripMap/Services/SecretTokenAuthStrategy.cs` | |
| `projects/road-trip/src/RoadTripMap/Services/UploadRateLimiter.cs` | RT | `src/RoadTripMap/Services/UploadRateLimiter.cs` | |
| `projects/road-trip/src/RoadTripMap/appsettings.Development.json` | RT | `src/RoadTripMap/appsettings.Development.json` | |
| `projects/road-trip/src/RoadTripMap/appsettings.json` | RT | `src/RoadTripMap/appsettings.json` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/create.html` | RT | `src/RoadTripMap/wwwroot/create.html` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/css/styles.css` | RT | `src/RoadTripMap/wwwroot/css/styles.css` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/index.html` | RT | `src/RoadTripMap/wwwroot/index.html` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/js/api.js` | RT | `src/RoadTripMap/wwwroot/js/api.js` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/js/exifUtil.js` | RT | `src/RoadTripMap/wwwroot/js/exifUtil.js` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/js/mapService.js` | RT | `src/RoadTripMap/wwwroot/js/mapService.js` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/js/mapUI.js` | RT | `src/RoadTripMap/wwwroot/js/mapUI.js` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/js/postService.js` | RT | `src/RoadTripMap/wwwroot/js/postService.js` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/js/postUI.js` | RT | `src/RoadTripMap/wwwroot/js/postUI.js` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/lib/exifr/lite.umd.js` | RT | `src/RoadTripMap/wwwroot/lib/exifr/lite.umd.js` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/post.html` | RT | `src/RoadTripMap/wwwroot/post.html` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/robots.txt` | RT | `src/RoadTripMap/wwwroot/robots.txt` | |
| `projects/road-trip/src/RoadTripMap/wwwroot/trips.html` | RT | `src/RoadTripMap/wwwroot/trips.html` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Endpoints/GeocodeEndpointTests.cs` | RT | `tests/RoadTripMap.Tests/Endpoints/GeocodeEndpointTests.cs` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Endpoints/IntegrationTests.cs` | RT | `tests/RoadTripMap.Tests/Endpoints/IntegrationTests.cs` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Endpoints/PhotoEndpointTests.cs` | RT | `tests/RoadTripMap.Tests/Endpoints/PhotoEndpointTests.cs` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Endpoints/TripEndpointTests.cs` | RT | `tests/RoadTripMap.Tests/Endpoints/TripEndpointTests.cs` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Endpoints/TripViewEndpointTests.cs` | RT | `tests/RoadTripMap.Tests/Endpoints/TripViewEndpointTests.cs` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Endpoints/ValidationTests.cs` | RT | `tests/RoadTripMap.Tests/Endpoints/ValidationTests.cs` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Helpers/SlugHelperTests.cs` | RT | `tests/RoadTripMap.Tests/Helpers/SlugHelperTests.cs` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Middleware/SecurityHeaderTests.cs` | RT | `tests/RoadTripMap.Tests/Middleware/SecurityHeaderTests.cs` | |
| `projects/road-trip/tests/RoadTripMap.Tests/RoadTripMap.Tests.csproj` | RT | `tests/RoadTripMap.Tests/RoadTripMap.Tests.csproj` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Services/GeocodingServiceTests.cs` | RT | `tests/RoadTripMap.Tests/Services/GeocodingServiceTests.cs` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Services/PhotoServiceTests.cs` | RT | `tests/RoadTripMap.Tests/Services/PhotoServiceTests.cs` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Services/SecretTokenAuthStrategyTests.cs` | RT | `tests/RoadTripMap.Tests/Services/SecretTokenAuthStrategyTests.cs` | |
| `projects/road-trip/tests/RoadTripMap.Tests/Services/UploadRateLimiterTests.cs` | RT | `tests/RoadTripMap.Tests/Services/UploadRateLimiterTests.cs` | |
| `archive/stephena-away/README.md` | ARCH | *(deleted)* | |
| `archive/stephena-away/content-v1.1.js` | ARCH | *(deleted)* | |
| `archive/stephena-away/content.js` | ARCH | *(deleted)* | |
| `archive/stephena-away/icons/create_icon.py` | ARCH | *(deleted)* | |
| `archive/stephena-away/icons/icon-48.svg` | ARCH | *(deleted)* | |
| `archive/stephena-away/icons/icon-96.svg` | ARCH | *(deleted)* | |
| `archive/stephena-away/manifest-v1.1.json` | ARCH | *(deleted)* | |
| `archive/stephena-away/manifest.json` | ARCH | *(deleted)* | |
| `archive/stephena-away/onion_headlines.json` | ARCH | *(deleted)* | |
| `projects/stock-analyzer/.editorconfig` | SA | `.editorconfig` | |
| `projects/stock-analyzer/.gitignore` | SA | `.gitignore` | |
| `projects/stock-analyzer/Dockerfile` | SA | `Dockerfile` | |
| `projects/stock-analyzer/ROADMAP.md` | SA | `ROADMAP.md` | |
| `projects/stock-analyzer/StockAnalyzer.sln` | SA | `StockAnalyzer.sln` | Solution paths are relative — no change needed |
| `projects/stock-analyzer/docker-compose.yml` | SA | `docker-compose.yml` | |
| `projects/stock-analyzer/docs/APP_EXPLANATION.md` | SA | `projects/stock-analyzer/docs/APP_EXPLANATION.md` | Stays in SA under same path (source for docs-deploy sync) |
| `projects/stock-analyzer/docs/CI_CD_SECURITY_PLAN.md` | SA | `projects/stock-analyzer/docs/CI_CD_SECURITY_PLAN.md` | |
| `projects/stock-analyzer/docs/DEPLOYMENT_AZURE.md` | SA | `projects/stock-analyzer/docs/DEPLOYMENT_AZURE.md` | |
| `projects/stock-analyzer/docs/DOTNET_SECURITY_EVALUATION.md` | SA | `projects/stock-analyzer/docs/DOTNET_SECURITY_EVALUATION.md` | |
| `projects/stock-analyzer/docs/FUNCTIONAL_SPEC.md` | SA | `projects/stock-analyzer/docs/FUNCTIONAL_SPEC.md` | Source synced to `docs/FUNCTIONAL_SPEC.md` by docs-deploy workflow |
| `projects/stock-analyzer/docs/PRIVACY_POLICY.md` | SA | `projects/stock-analyzer/docs/PRIVACY_POLICY.md` | |
| `projects/stock-analyzer/docs/PROJECT_OVERVIEW.md` | SA | `projects/stock-analyzer/docs/PROJECT_OVERVIEW.md` | |
| `projects/stock-analyzer/docs/RELEASE_NOTES_2.4.md` | SA | `projects/stock-analyzer/docs/RELEASE_NOTES_2.4.md` | |
| `projects/stock-analyzer/docs/RUNBOOK.md` | SA | `projects/stock-analyzer/docs/RUNBOOK.md` | |
| `projects/stock-analyzer/docs/SECURITY_OVERVIEW.md` | SA | `projects/stock-analyzer/docs/SECURITY_OVERVIEW.md` | |
| `projects/stock-analyzer/docs/TECHNICAL_SPEC.md` | SA | `projects/stock-analyzer/docs/TECHNICAL_SPEC.md` | Source synced to `docs/TECHNICAL_SPEC.md` by docs-deploy |
| `projects/stock-analyzer/docs/THEMING_GUIDE.md` | SA | `projects/stock-analyzer/docs/THEMING_GUIDE.md` | |
| `projects/stock-analyzer/helpers/test_bloomberg_ux.py` | SA | `projects/stock-analyzer/helpers/test_bloomberg_ux.py` | SA-internal helper |
| `projects/stock-analyzer/infrastructure/azure/deploy.ps1` | SA | `projects/stock-analyzer/infrastructure/azure/deploy.ps1` | |
| `projects/stock-analyzer/infrastructure/azure/main-aci.bicep` | SA | `projects/stock-analyzer/infrastructure/azure/main-aci.bicep` | |
| `projects/stock-analyzer/infrastructure/azure/main.bicep` | SA | `projects/stock-analyzer/infrastructure/azure/main.bicep` | Referenced by azure-deploy.yml |
| `projects/stock-analyzer/infrastructure/azure/parameters.json` | SA | `projects/stock-analyzer/infrastructure/azure/parameters.json` | |
| `projects/stock-analyzer/infrastructure/database/README.md` | SA | `projects/stock-analyzer/infrastructure/database/README.md` | |
| `projects/stock-analyzer/research/README.md` | SA | `projects/stock-analyzer/research/README.md` | |
| `projects/stock-analyzer/research/vaporwave-concepts.html` | SA | `projects/stock-analyzer/research/vaporwave-concepts.html` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/MLModels/export_finbert.py` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/MLModels/export_finbert.py` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/MLModels/yolov8n.onnx` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/MLModels/yolov8n.onnx` | Binary file |
| `projects/stock-analyzer/src/StockAnalyzer.Api/Program.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/Program.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/Properties/launchSettings.json` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/Properties/launchSettings.json` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/StockAnalyzer.Api.csproj` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/StockAnalyzer.Api.csproj` | ProjectReference to Core is relative — no change |
| `projects/stock-analyzer/src/StockAnalyzer.Api/StockAnalyzer.Api.http` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/StockAnalyzer.Api.http` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/appsettings.json` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/appsettings.json` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/package-lock.json` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/package-lock.json` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/package.json` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/package.json` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/src/input.css` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/src/input.css` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/tailwind.config.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/tailwind.config.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/about.html` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/about.html` | References `github.com/psford/claudeProjects` → update to SA repo URL |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/apple-touch-icon.png` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/apple-touch-icon.png` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/css/base.css` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/css/base.css` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/css/styles.css` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/css/styles.css` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/docs.html` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/docs.html` | `docsBaseUrl` hardcoded to `psford.github.io/claudeProjects/` → update to new Pages URL |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-128x128.png` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-128x128.png` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-16x16.png` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-16x16.png` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-180x180.png` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-180x180.png` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-192x192.png` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-192x192.png` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-32x32.png` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-32x32.png` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-48x48.png` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-48x48.png` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-512x512.png` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-512x512.png` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-64x64.png` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon-64x64.png` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon.ico` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/favicon.ico` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/index.html` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/index.html` | References `github.com/psford/claudeProjects` → update to SA repo URL |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/api.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/api.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/app.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/app.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/canvasEffects.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/canvasEffects.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/charts.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/charts.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/dragMeasure.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/dragMeasure.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/storage.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/storage.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/symbolSearch.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/symbolSearch.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/themeAudio.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/themeAudio.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/themeEditor.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/themeEditor.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/themeLoader.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/themeLoader.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/themePreview.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/themePreview.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/tileDashboard.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/tileDashboard.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/vaporwaveAudio.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/vaporwaveAudio.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/watchlist.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/js/watchlist.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/lib/gridstack/gridstack-all.min.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/lib/gridstack/gridstack-all.min.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/lib/gridstack/gridstack.min.css` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/lib/gridstack/gridstack.min.css` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/package-lock.json` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/package-lock.json` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/package.json` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/package.json` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/prototypes/grimdark-space-opera.html` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/prototypes/grimdark-space-opera.html` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/prototypes/tile-dashboard.html` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/prototypes/tile-dashboard.html` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/site.webmanifest` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/site.webmanifest` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/status.html` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/status.html` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/tests/chartSeries.test.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/tests/chartSeries.test.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/tests/portfolio.test.js` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/tests/portfolio.test.js` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/theme-editor.html` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/theme-editor.html` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/theme-preview.html` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/theme-preview.html` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes/dark.json` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes/dark.json` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes/grimdark-space-opera.json` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes/grimdark-space-opera.json` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes/light.json` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes/light.json` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes/manifest.json` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes/manifest.json` | |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes/neon-noir.json` | SA | `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes/neon-noir.json` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/DesignTimeDbContextFactory.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/DesignTimeDbContextFactory.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/BusinessCalendarEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/BusinessCalendarEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/CachedImageEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/CachedImageEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/CachedSentimentEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/CachedSentimentEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/CompanyBioEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/CompanyBioEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/CoverageSummaryEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/CoverageSummaryEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/IndexConstituentEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/IndexConstituentEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/IndexDefinitionEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/IndexDefinitionEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/MicExchangeEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/MicExchangeEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/PriceEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/PriceEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/PriceStagingEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/PriceStagingEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityIdentifierEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityIdentifierEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityIdentifierHistEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityIdentifierHistEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityMasterEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityMasterEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityPriceCoverageByYearEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityPriceCoverageByYearEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityPriceCoverageEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityPriceCoverageEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SourceEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SourceEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SymbolEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SymbolEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/TrackedSecurityEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/TrackedSecurityEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/WatchlistEntity.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/WatchlistEntity.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260118021021_InitialCreate.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260118021021_InitialCreate.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260118021021_InitialCreate.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260118021021_InitialCreate.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122022358_AddSymbolsTable.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122022358_AddSymbolsTable.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122022358_AddSymbolsTable.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122022358_AddSymbolsTable.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122035832_AddCachedImagesTable.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122035832_AddCachedImagesTable.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122035832_AddCachedImagesTable.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122035832_AddCachedImagesTable.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122044720_AddFullTextSearchOnSymbols.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122044720_AddFullTextSearchOnSymbols.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122044720_AddFullTextSearchOnSymbols.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260122044720_AddFullTextSearchOnSymbols.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260123043827_AddCachedSentiments.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260123043827_AddCachedSentiments.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260123043827_AddCachedSentiments.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260123043827_AddCachedSentiments.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260123182425_AddSecurityMasterAndPrices.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260123182425_AddSecurityMasterAndPrices.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260123182425_AddSecurityMasterAndPrices.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260123182425_AddSecurityMasterAndPrices.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260124052414_AddSecurityMasterCountryCurrencyIsin.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260124052414_AddSecurityMasterCountryCurrencyIsin.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260124052414_AddSecurityMasterCountryCurrencyIsin.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260124052414_AddSecurityMasterCountryCurrencyIsin.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125014811_AddSourcesAndBusinessCalendar.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125014811_AddSourcesAndBusinessCalendar.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125014811_AddSourcesAndBusinessCalendar.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125014811_AddSourcesAndBusinessCalendar.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125021351_AddIsHolidayToBusinessCalendar.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125021351_AddIsHolidayToBusinessCalendar.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125021351_AddIsHolidayToBusinessCalendar.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125021351_AddIsHolidayToBusinessCalendar.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125175942_AddTrackedSecurities.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125175942_AddTrackedSecurities.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125175942_AddTrackedSecurities.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260125175942_AddTrackedSecurities.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260126061435_AddPriceStagingTable.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260126061435_AddPriceStagingTable.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260126061435_AddPriceStagingTable.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260126061435_AddPriceStagingTable.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260126232958_AddIsEodhdUnavailable.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260126232958_AddIsEodhdUnavailable.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260126232958_AddIsEodhdUnavailable.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260126232958_AddIsEodhdUnavailable.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260127034243_AddImportanceScoreToSecurityMaster.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260127034243_AddImportanceScoreToSecurityMaster.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260127034243_AddImportanceScoreToSecurityMaster.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260127034243_AddImportanceScoreToSecurityMaster.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260127142152_AddCoverageSummaryTable.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260127142152_AddCoverageSummaryTable.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260127142152_AddCoverageSummaryTable.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260127142152_AddCoverageSummaryTable.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260128070730_AddIsEodhdCompleteToSecurityMaster.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260128070730_AddIsEodhdCompleteToSecurityMaster.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260128070730_AddIsEodhdCompleteToSecurityMaster.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260128070730_AddIsEodhdCompleteToSecurityMaster.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260203023640_AddCompanyBio.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260203023640_AddCompanyBio.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260203023640_AddCompanyBio.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260203023640_AddCompanyBio.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260223034707_MapIndexAttributionTables.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260223034707_MapIndexAttributionTables.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260223034707_MapIndexAttributionTables.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260223034707_MapIndexAttributionTables.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260223232008_CreateIndexTablesIfNotExist.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260223232008_CreateIndexTablesIfNotExist.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260223232008_CreateIndexTablesIfNotExist.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260223232008_CreateIndexTablesIfNotExist.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260224051341_CreateCoverageTablesIfNotExist.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260224051341_CreateCoverageTablesIfNotExist.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260224051341_CreateCoverageTablesIfNotExist.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260224051341_CreateCoverageTablesIfNotExist.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260227013220_AddMicExchangeTable.Designer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260227013220_AddMicExchangeTable.Designer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260227013220_AddMicExchangeTable.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260227013220_AddMicExchangeTable.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/StockAnalyzerDbContextModelSnapshot.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/StockAnalyzerDbContextModelSnapshot.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlCachedImageRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlCachedImageRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlPriceRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlPriceRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlSecurityMasterRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlSecurityMasterRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlSentimentCacheRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlSentimentCacheRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlSymbolRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlSymbolRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlWatchlistRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlWatchlistRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Data/StockAnalyzerDbContext.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Data/StockAnalyzerDbContext.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Helpers/LogSanitizer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Helpers/LogSanitizer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Models/CompanyProfile.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Models/CompanyProfile.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Models/HistoricalData.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Models/HistoricalData.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Models/NewsItem.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Models/NewsItem.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Models/SearchResult.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Models/SearchResult.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Models/SignificantMove.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Models/SignificantMove.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Models/StockInfo.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Models/StockInfo.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Models/TechnicalIndicators.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Models/TechnicalIndicators.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Models/Watchlist.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Models/Watchlist.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/AggregatedNewsService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/AggregatedNewsService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/AggregatedStockDataService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/AggregatedStockDataService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/AnalysisService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/AnalysisService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/DbWarmupService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/DbWarmupService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/EodhdService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/EodhdService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/FinBertSentimentService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/FinBertSentimentService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/FmpService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/FmpService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/HeadlineRelevanceService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/HeadlineRelevanceService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ICachedImageRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ICachedImageRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/IPriceRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/IPriceRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/IPriceStagingRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/IPriceStagingRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ISecurityMasterRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ISecurityMasterRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ISentimentCacheRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ISentimentCacheRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/IStockDataProvider.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/IStockDataProvider.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ISymbolRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ISymbolRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/IWatchlistRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/IWatchlistRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ImageCacheService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ImageCacheService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ImageProcessingService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/ImageProcessingService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/JsonWatchlistRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/JsonWatchlistRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/MarketauxService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/MarketauxService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/NewsService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/NewsService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/PriceRefreshService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/PriceRefreshService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/RateLimitTracker.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/RateLimitTracker.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/SentimentAnalyzer.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/SentimentAnalyzer.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/SentimentCacheService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/SentimentCacheService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/SqlPriceStagingRepository.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/SqlPriceStagingRepository.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/StockDataService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/StockDataService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/SymbolCache.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/SymbolCache.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/SymbolRefreshService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/SymbolRefreshService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/TwelveDataService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/TwelveDataService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/UsMarketCalendar.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/UsMarketCalendar.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/VaderSentimentService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/VaderSentimentService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/WatchlistService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/WatchlistService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/WikipediaService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/WikipediaService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/Services/YahooFinanceService.cs` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/Services/YahooFinanceService.cs` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/StockAnalyzer.Core.csproj` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/StockAnalyzer.Core.csproj` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/scripts/001_CreateDataSchema.sql` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/scripts/001_CreateDataSchema.sql` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/scripts/002_AddSecurityMasterAndPrices.sql` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/scripts/002_AddSecurityMasterAndPrices.sql` | |
| `projects/stock-analyzer/src/StockAnalyzer.Core/scripts/seed_index_attribution.sql` | SA | `projects/stock-analyzer/src/StockAnalyzer.Core/scripts/seed_index_attribution.sql` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/CoverageIntegrationTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/CoverageIntegrationTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/IndexSearchSchemaTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/IndexSearchSchemaTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/MicExchangeSchemaTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/MicExchangeSchemaTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/SchemaValidationTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/SchemaValidationTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/SecurityMasterDtoTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/SecurityMasterDtoTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/SqlPriceRepositoryCoverageTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Data/SqlPriceRepositoryCoverageTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Integration/ProgramDiWiringTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Integration/ProgramDiWiringTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Models/ModelCalculationTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Models/ModelCalculationTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Models/SearchResultDisplayTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Models/SearchResultDisplayTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/AggregatedNewsServiceTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/AggregatedNewsServiceTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/AnalysisServiceTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/AnalysisServiceTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/BackfillMicCodesTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/BackfillMicCodesTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/HeadlineRelevanceServiceTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/HeadlineRelevanceServiceTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/MarketauxServiceTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/MarketauxServiceTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/NewsServiceTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/NewsServiceTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/SentimentAnalyzerTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/SentimentAnalyzerTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/SqlSymbolRepositoryTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/SqlSymbolRepositoryTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/StockDataServiceTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/StockDataServiceTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/WatchlistServiceTests.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Services/WatchlistServiceTests.cs` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/StockAnalyzer.Core.Tests.csproj` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/StockAnalyzer.Core.Tests.csproj` | |
| `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/TestHelpers/TestDataFactory.cs` | SA | `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/TestHelpers/TestDataFactory.cs` | |
| `pyproject.toml` | CE | `pyproject.toml` | Update `targets` from `["stock_analysis", "helpers"]` to `["helpers"]` |
| `runbooks/BRANCH_RENAME_RUNBOOK.md` | CE | `runbooks/BRANCH_RENAME_RUNBOOK.md` | |
| `scripts/install-hooks.sh` | CE | `scripts/install-hooks.sh` | |
| `sessionState.md` | CE | `sessionState.md` | |
| `slack_last_sync.txt` | CE | `slack_last_sync.txt` | Runtime state file |
| `swearJar.json` | CE | `swearJar.json` | |
| `whileYouWereAway.md` | CE | `whileYouWereAway.md` | |

---

## 2. Reverse Lookup by Destination Repo

### stock-analyzer (SA) — 339 files

**Repo root (from `projects/stock-analyzer/`):**
`.editorconfig`, `.gitignore`, `Dockerfile`, `ROADMAP.md`, `StockAnalyzer.sln`, `docker-compose.yml`

**`eodhd-loader/` (from `projects/eodhd-loader/`):**
All 52 files under `projects/eodhd-loader/` mapped to `eodhd-loader/` at repo root.

**`docs/` (GitHub Pages — from monorepo `docs/`):**
`APP_EXPLANATION.md`, `CI_CD_SECURITY_PLAN.md`, `CI_CD_SETUP.md`, `DEPLOYMENT_AZURE.md`, `FUNCTIONAL_SPEC.md`, `PRIVACY_POLICY.md`, `SECURITY_OVERVIEW.md`, `TECHNICAL_SPEC.md`, `claude_disp.md`, `index.html`, all diagrams (7), all design-plans (2), all implementation-plans (6), all retrospectives (1), all test-plans (3).

**`helpers/` (from monorepo `helpers/` — SA-bespoke tools):**
`cloudflare_test.py`, `load_test.py`, `test_dtu_endpoints.py`, `test_image_api.py`, `test_theme_generator.py`, `theme_generator.py`, `theme_manager.py`, `theme_schema.py`

**`.github/workflows/`:**
`azure-deploy.yml`, `docs-deploy.yml`, `dotnet-ci.yml`, `test-connectivity.yml`

**`projects/stock-analyzer/` (internal structure unchanged):**
All remaining SA source files (docs, infrastructure, src, tests) remain under `projects/stock-analyzer/` within the SA repo.

---

### road-trip (RT) — 63 files

All files from `projects/road-trip/` mapped to repo root (strip `projects/road-trip/` prefix).

**`.github/workflows/`:** `roadtrip-ci.yml`, `roadtrip-deploy.yml`

---

### claude-env (CE) — 97 files

`.claude/hooks/` (23 hooks) + `.claude/settings.local.json`
`.github/workflows/branch-guard.yml`, `branch-hygiene.yml`, `codeql.yml`
`.github/CODEOWNERS`, `PULL_REQUEST_TEMPLATE.md`, `dependabot.yml`
`.gitignore`, `.pre-commit-config.yaml`, `.secrets.baseline`
`CLAUDE.md`, `Jenkinsfile`, `LICENSE`, `README.md`
`claudeLog.md`, `sessionState.md`, `whileYouWereAway.md`, `slack_last_sync.txt`, `swearJar.json`
`claudeProjects.code-workspace` (renamed `claude-env.code-workspace`)
`pyproject.toml`
`helpers/` — 29 reusable tools + 10 hook helpers
`infrastructure/wsl/` — 10 files
`scripts/install-hooks.sh`
`runbooks/BRANCH_RENAME_RUNBOOK.md`
`docs/design-plans/2026-03-20-wsl2-claude-sandbox.md`, `2026-03-22-repo-split.md`, `repo-split-migration-manifest.md`
`docs/retrospectives/2026-03-22-wsl2-sandbox-retro-mitigations.md`

---

### archive / deleted — 30 files

`archive/claude_backups/` (18 files), `archive/docs/DEPLOYMENT_ORACLE.md`, `archive/hook-test/test_hooks.py`, `archive/stephena-away/` (9 files), `archive/stock_analysis_python/` (3 files)

---

## 3. Files Requiring Path Changes

### Critical — build will break without these

| File | Current Reference | Required Change |
|------|-------------------|----------------|
| `projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj` | `<ProjectReference Include="..\..\..\stock-analyzer\src\StockAnalyzer.Core\StockAnalyzer.Core.csproj" />` | Update to `<ProjectReference Include="..\..\..\..\projects\stock-analyzer\src\StockAnalyzer.Core\StockAnalyzer.Core.csproj" />` — path changes because eodhd-loader moves from `projects/eodhd-loader/` to `eodhd-loader/` while stock-analyzer stays at `projects/stock-analyzer/` |

**Note on the eodhd-loader ProjectReference:** In the monorepo the path is `../../../stock-analyzer/src/StockAnalyzer.Core/StockAnalyzer.Core.csproj` (3 levels up from `src/EodhdLoader/` reaches `projects/`, then into `stock-analyzer/`). In the SA repo the path from `eodhd-loader/src/EodhdLoader/` up 3 levels reaches repo root, then the Core is at `projects/stock-analyzer/src/StockAnalyzer.Core/StockAnalyzer.Core.csproj`. The new relative path becomes `../../../projects/stock-analyzer/src/StockAnalyzer.Core/StockAnalyzer.Core.csproj`.

---

### GitHub Pages URLs — live app will fetch wrong docs without these

| File | Current Value | Required Change |
|------|---------------|----------------|
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/docs.html` | `docsBaseUrl: 'https://psford.github.io/claudeProjects/'` | Update to new SA repo GitHub Pages URL, e.g. `'https://psford.github.io/stock-analyzer/'` |
| `docs/index.html` (GitHub Pages) | `docsBaseUrl: 'https://psford.github.io/claudeProjects/'` | Update to new SA Pages URL |

---

### GitHub repo URL references — cosmetic but should be updated

| File | Reference | Action |
|------|-----------|--------|
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/about.html` | `github.com/psford/claudeProjects` | Update to `github.com/psford/stock-analyzer` |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/docs.html` | `github.com/psford/claudeProjects` | Update to `github.com/psford/stock-analyzer` |
| `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/index.html` | `github.com/psford/claudeProjects` (footer GitHub link) | Update to `github.com/psford/stock-analyzer` |
| `docs/CI_CD_SETUP.md` | `github.com/psford/claudeProjects/actions` | Update to SA repo URL |
| `docs/TECHNICAL_SPEC.md` | Multiple `psford.github.io/claudeProjects/` URLs | Update to new Pages URL |
| `CLAUDE.md` | `https://psford.github.io/claudeProjects/` (Stock Analyzer Specific section) | Update in SA repo copy |
| `helpers/hooks/validate_hf_urls.py` | `User-Agent: ...github.com/psford/claudeProjects` | Update to CE repo URL |

---

### CI workflow path filters — workflows won't trigger on correct files without these

| File | Current paths filter | Required Change |
|------|---------------------|----------------|
| `.github/workflows/dotnet-ci.yml` | `projects/stock-analyzer/**`, `SOLUTION_PATH: 'projects/stock-analyzer/StockAnalyzer.sln'`, `FRONTEND_PATH: 'projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot'` | Remove `projects/stock-analyzer/` prefix from all path references |
| `.github/workflows/azure-deploy.yml` | `dotnet restore projects/stock-analyzer/StockAnalyzer.sln`, `cd projects/stock-analyzer` in docker build step, Bicep path `projects/stock-analyzer/infrastructure/azure/main.bicep` | Remove `projects/stock-analyzer/` prefix where SA files are at root; keep `projects/stock-analyzer/` for files that remain under that subdir in SA repo |
| `.github/workflows/docs-deploy.yml` | `cp -f projects/stock-analyzer/docs/TECHNICAL_SPEC.md docs/TECHNICAL_SPEC.md`, path filter `projects/stock-analyzer/docs/**` | Remove `projects/stock-analyzer/` prefix from cp source paths; update path triggers |
| `.github/workflows/roadtrip-ci.yml` | `SOLUTION_PATH: 'projects/road-trip/RoadTripMap.sln'`, path filter `projects/road-trip/**` | Remove `projects/road-trip/` prefix — solution is at repo root |
| `.github/workflows/roadtrip-deploy.yml` | `dotnet restore projects/road-trip/RoadTripMap.sln`, `-f projects/road-trip/Dockerfile projects/road-trip/` | Remove `projects/road-trip/` prefix |
| `.github/workflows/codeql.yml` | Path filters for `projects/stock-analyzer/**`, `projects/eodhd-loader/**`, `projects/road-trip/**` | Split into per-repo workflows with appropriate path filters |

---

### Infrastructure scripts — WSL setup will clone wrong repo

| File | Current Value | Required Change |
|------|---------------|----------------|
| `infrastructure/wsl/wsl-setup.sh` | `git clone git@github.com:psford/claudeProjects.git "$REPO_DIR"` | Update to `git@github.com:psford/claude-env.git` |
| `infrastructure/wsl/pull-secrets.sh` | `$HOME/projects/claudeProjects/.gitignore` detection, output to `$HOME/projects/claudeProjects/.env` | Update path to new CE repo clone location |
| `infrastructure/wsl/test-secrets-roundtrip.sh` | `ENV_FILE="$HOME/projects/claudeProjects/.env"` | Update to new CE repo path |

---

### Claude Code hooks — wrong spec path, stale project references

| File | Current Value | Required Change |
|------|---------------|----------------|
| `.claude/hooks/spec_staleness_guard.py` | `SPEC_PATH = "projects/stock-analyzer/docs/TECHNICAL_SPEC.md"` | In SA repo: update to `"projects/stock-analyzer/docs/TECHNICAL_SPEC.md"` (unchanged); in CE repo: remove or remap |
| `.claude/hooks/eodhd_rebuild_guard.py` | `f.startswith("projects/eodhd-loader/")` | In SA repo: update to `f.startswith("eodhd-loader/")` |
| `.claude/settings.local.json` | Windows path permissions reference `claudeProjects` directory name | Update to new repo directory name for each split repo |
| `helpers/hooks/check_spec_updates.py` | `'projects/hook-test/'` exclusion | Remove (hook-test deleted) |

---

### Python tooling — incorrect scan targets

| File | Current Value | Required Change |
|------|---------------|----------------|
| `pyproject.toml` | `targets = ["stock_analysis", "helpers"]` | In CE repo: `targets = ["helpers"]`; `stock_analysis` directory was already archived |

---

### theme_manager.py — hardcoded monorepo path

| File | Current Value | Required Change |
|------|---------------|----------------|
| `helpers/theme_manager.py` | `Path(__file__).parent.parent / "projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes"` | Update to `Path(__file__).parent.parent / "projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes"` — unchanged if tool stays at `helpers/theme_manager.py` within SA repo root; verify relative depth is correct |

**Note:** If `theme_manager.py` is placed at `helpers/theme_manager.py` in the SA repo (repo root → `helpers/`), then `parent.parent` from `helpers/theme_manager.py` = repo root, and the themes path `projects/stock-analyzer/src/StockAnalyzer.Api/wwwroot/themes` resolves correctly. No change needed if the SA repo preserves the `projects/stock-analyzer/` directory structure internally.

---

## 4. Files With No Path Changes Required

The following categories have only relative internal references and require no edits after migration:

- All `projects/stock-analyzer/` C# source files (`*.cs`, `*.csproj`) — ProjectReferences are all relative within the solution
- All `projects/road-trip/` C# source files — no cross-repo dependencies
- All EF Core migration files — no external path references
- All `wwwroot/` JS files (except `docs.html`) — no hardcoded repo URLs
- All theme JSON files
- All `.mmd` diagram files
- `projects/eodhd-loader/EodhdLoader.sln` — sln paths are relative within eodhd-loader
- `projects/eodhd-loader/tests/EodhdLoader.Tests/EodhdLoader.Tests.csproj` — references `../../src/EodhdLoader/EodhdLoader.csproj` (relative within eodhd-loader tree, unchanged)
