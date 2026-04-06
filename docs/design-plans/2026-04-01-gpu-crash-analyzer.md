# GPU Crash Analyzer Design

## Summary

GPU Crash Analyzer is a standalone PowerShell diagnostic tool that reads Windows Event Viewer logs and produces a plain-English crash report for users experiencing GPU instability. Rather than requiring a user to manually wade through Event Viewer or interpret raw kernel events, the script collects relevant system and hardware error events, groups them into discrete crash incidents by time proximity, and matches each incident against an embedded knowledge base to produce a specific diagnosis and a ranked list of recommended fixes. The output is a markdown report that is readable by someone unfamiliar with Windows internals.

The tool has two modes. The **analyzer** (`Analyze-GpuCrashes.ps1`) runs on demand after a crash — it queries Event Viewer, correlates events into incidents, matches against a knowledge base, and writes a markdown report with diagnosis and fix recommendations. The **monitor** (`Monitor-Gpu.ps1`) is an optional lightweight background logger that polls `nvidia-smi` every second, writing GPU power draw, temperature, and clock state to CSV with immediate flush so data survives hard crashes. When both are used together, the analyzer reads telemetry from the seconds before the crash to enrich its diagnosis — distinguishing, for example, a crash at full GPU boost from a crash at idle. Minidump parsing via `cdb.exe` is available as an additional optional layer.

## Definition of Done
1. **A PowerShell diagnostic script** that queries Windows Event Viewer for GPU crash-related events (nvlddmkm, Kernel-Power, WHEA-Logger, BugCheck) and optionally parses minidump files via `cdb.exe`
2. **Produces a markdown report** with a crash timeline, event correlation, and likely root cause diagnosis with actionable fix recommendations
3. **An optional lightweight GPU telemetry logger** that runs `nvidia-smi` in a background loop, writing power draw, temperature, clocks, and utilization to a CSV flushed every second — survives hard crashes
4. **The analyzer integrates telemetry data** when available, correlating GPU state in the seconds before a crash with Event Viewer data for richer diagnosis
5. **Lives in its own repo** (`psford/gpu-crash-analyzer`), usable by anyone with GPU crash issues

## Acceptance Criteria

### gpu-crash-analyzer.AC1: Event Viewer queries retrieve GPU crash events
- **gpu-crash-analyzer.AC1.1 Success:** Script retrieves nvlddmkm events (IDs 0, 14, 153) from System/Application logs
- **gpu-crash-analyzer.AC1.2 Success:** Script retrieves Kernel-Power 41 (with BugcheckCode properties), WHEA-Logger 17/18/19, BugCheck, LiveKernelEvent, and EventLog 6008 entries
- **gpu-crash-analyzer.AC1.3 Success:** `-Days` parameter limits query to specified time window
- **gpu-crash-analyzer.AC1.4 Edge:** No crash events found — script reports "no GPU crash events found" cleanly

### gpu-crash-analyzer.AC2: Events are correlated into crash incidents
- **gpu-crash-analyzer.AC2.1 Success:** Events within a 5-second window are grouped as one incident
- **gpu-crash-analyzer.AC2.2 Success:** Causal chain (WHEA → nvlddmkm → Kernel-Power) is identified when present
- **gpu-crash-analyzer.AC2.3 Edge:** Lone Kernel-Power 41 with BugcheckCode 0 and no GPU events classified as hardware power-off

### gpu-crash-analyzer.AC3: Crash patterns produce accurate diagnoses
- **gpu-crash-analyzer.AC3.1 Success:** Known patterns produce correct diagnosis text and actionable recommendations
- **gpu-crash-analyzer.AC3.2 Edge:** Unrecognized pattern produces "unrecognized" message with raw events included for sharing

### gpu-crash-analyzer.AC4: Markdown report is generated
- **gpu-crash-analyzer.AC4.1 Success:** Report contains system info, crash timeline, diagnosis, and recommended actions
- **gpu-crash-analyzer.AC4.2 Success:** Report written to `./reports/` by default, or custom path via `-OutputDir`
- **gpu-crash-analyzer.AC4.3 Success:** Report is readable and useful to someone unfamiliar with Event Viewer

### gpu-crash-analyzer.AC5: Minidump parsing works when available
- **gpu-crash-analyzer.AC5.1 Success:** With `-IncludeMinidump` and `cdb.exe` on PATH, minidump findings appear in report
- **gpu-crash-analyzer.AC5.2 Edge:** Without `cdb.exe`, script warns and continues without minidump analysis
- **gpu-crash-analyzer.AC5.3 Edge:** Minidump directory requires elevation — script detects and warns

### gpu-crash-analyzer.AC6: GPU telemetry monitor logs data continuously
- **gpu-crash-analyzer.AC6.1 Success:** Monitor script polls nvidia-smi at configured interval and writes CSV with timestamp, power draw, temperature, clocks, utilization
- **gpu-crash-analyzer.AC6.2 Success:** Each CSV line is flushed to disk immediately so data survives hard crashes
- **gpu-crash-analyzer.AC6.3 Success:** Daily log rotation with configurable retention
- **gpu-crash-analyzer.AC6.4 Edge:** nvidia-smi not found on PATH — script exits with clear error message
- **gpu-crash-analyzer.AC6.5 Edge:** nvidia-smi returns error (e.g., driver not loaded) — script logs error and retries

### gpu-crash-analyzer.AC7: Analyzer integrates telemetry data when available
- **gpu-crash-analyzer.AC7.1 Success:** When telemetry CSV exists, report includes GPU state (power, temp, clocks) in the 30-60 seconds before the crash
- **gpu-crash-analyzer.AC7.2 Success:** Telemetry enriches diagnosis (e.g., "GPU was drawing 420W at max boost when system died — confirms transient-induced power loss")
- **gpu-crash-analyzer.AC7.3 Edge:** No telemetry CSV found — analyzer proceeds with Event Viewer data only, notes that telemetry was not available

## Glossary
- **nvlddmkm**: The NVIDIA Windows kernel-mode display driver. Events from this provider (IDs 0, 14, 153) indicate the GPU driver has timed out, crashed, or failed to respond.
- **Kernel-Power 41**: A Windows kernel event logged after an unexpected system shutdown. Records the bugcheck code. Notably records *next boot time*, not crash time — making EventLog 6008 necessary for accurate timestamps.
- **WHEA-Logger**: Windows Hardware Error Architecture — logs corrected and uncorrectable hardware errors. Events 17, 18, 19 cover PCIe bus errors that often precede GPU crashes.
- **BugcheckCode**: The numeric stop code in a Kernel-Power 41 event. Code 0 = hard power-off (no software trace). Code 0x3B = SYSTEM_SERVICE_EXCEPTION (kernel driver fault).
- **EventLog 6008**: Logged at boot time indicating the previous shutdown was unexpected. Carries the actual crash timestamp.
- **TDR (Timeout Detection and Recovery)**: Windows mechanism that detects when a GPU stops responding and attempts to reset it. A recovered TDR produces nvlddmkm 0; a failed TDR produces a bugcheck.
- **12VHPWR**: The 16-pin PCIe power connector on high-end GPUs (RTX 3000/4000 series). Known for contact failures causing instantaneous power loss under transient load.
- **DDU (Display Driver Uninstaller)**: Community tool that completely removes NVIDIA/AMD driver files before a clean reinstall.
- **cdb.exe**: Console-mode debugger from the Windows SDK / WinDbg package. Used to run `!analyze -v` against minidump files.
- **Minidump**: Compact crash dump in `C:\Windows\Minidump\` written during a bugcheck. Contains stop code, loaded drivers, and faulting thread.
- **`Get-WinEvent -FilterHashtable`**: PowerShell server-side event log filtering. Significantly faster than client-side filtering for large logs.
- **Knowledge base**: The embedded hashtable mapping event patterns to diagnoses and recommendations. A static lookup table, not an external service.

## Architecture

Single PowerShell script (`Analyze-GpuCrashes.ps1`) with four internal stages executed sequentially:

**Stage 1: System Info Collection** — Uses WMI/CIM to gather GPU model, driver version, VBIOS version, Windows version, and available RAM. Provides hardware context at the top of every report.

**Stage 2: Event Collection** — Queries Windows Event Viewer using `Get-WinEvent -FilterHashtable` (server-side filtering) for these providers:
- `nvlddmkm` — Event IDs 0, 14, 153 (GPU driver timeout/failure)
- `Kernel-Power` — Event ID 41 (unexpected shutdown)
- `WHEA-Logger` — Event IDs 17, 18, 19 (corrected/uncorrectable hardware errors)
- `BugCheck` — System bugcheck events
- `LiveKernelEvent` — GPU-specific kernel events
- `EventLog` — Event ID 6008 (unexpected shutdown timestamp — provides the actual crash time)

Queries System and Application logs. Default lookback: 30 days, configurable via `-Days` parameter.

**Stage 3: Crash Correlation** — Groups collected events into crash incidents using a 5-second time window. Events within the window are grouped as one incident. The correlator identifies the causal chain (WHEA → nvlddmkm → Kernel-Power) and classifies each incident by pattern.

**Stage 4: Diagnosis & Report** — Matches the most recent crash incident against an embedded knowledge base (hashtable mapping event patterns to plain-English diagnoses and actionable fix recommendations). Writes a markdown report to `./reports/`.

**Optional: Minidump Parsing** — If `cdb.exe` is found on PATH (ships with Windows SDK or WinDbg), the script runs automated analysis on `.dmp` files in `C:\Windows\Minidump\` and includes findings in the report. Gracefully skips if `cdb.exe` is not available.

**Optional: Telemetry Log Integration** — If a GPU telemetry CSV exists (produced by the monitor script), the analyzer reads the final entries before the crash timestamp and includes them in the report: power draw, temperature, clock speeds, and utilization in the seconds leading up to the crash.

### GPU Telemetry Monitor

A separate lightweight script (`Monitor-Gpu.ps1`) that runs in the background and logs GPU state to CSV via `nvidia-smi`. Designed to survive hard crashes by flushing every write.

**How it works:**
- Runs `nvidia-smi --query-gpu=timestamp,power.draw,temperature.gpu,clocks.current.graphics,clocks.current.memory,memory.used,utilization.gpu,utilization.memory --format=csv` in a loop
- Polls every 1 second (configurable via `-IntervalSeconds`)
- Appends each reading to a date-stamped CSV in `./telemetry/` (e.g., `gpu-telemetry-2026-04-02.csv`)
- Flushes after every write so data survives instant power loss
- Auto-rotates daily, configurable retention via `-RetentionDays` (default: 7)
- Requires `nvidia-smi` on PATH (ships with NVIDIA driver)

**What it captures vs. what it can't:**
- Captures: Average power draw, temperature, clock state, utilization at 1-second resolution
- Cannot capture: Microsecond power transients (the actual kill spike). But the seconds leading up to a crash reveal load level, boost state, and whether the GPU was transitioning — enough to confirm or rule out power-related crashes.

```powershell
# Start monitoring (runs until Ctrl+C or system crash)
.\Monitor-Gpu.ps1

# Custom interval and retention
.\Monitor-Gpu.ps1 -IntervalSeconds 2 -RetentionDays 14

# Custom output directory
.\Monitor-Gpu.ps1 -OutputDir "C:\GpuLogs"
```

### Knowledge Base

Embedded in the script as a hashtable. Maps event patterns to diagnoses:

| Pattern | Diagnosis | Recommended Actions |
|---------|-----------|-------------------|
| Kernel-Power 41 + BugcheckCode 0 + no GPU/WHEA events | **Hardware power-off** — system lost power instantly, no software trace. Power delivery failure during GPU transient load | Reseat 12VHPWR connector, undervolt GPU 50-75mV, check PSU model/age, test different PSU |
| nvlddmkm 153 + WHEA 17 (PCIe) | Power delivery issue with PCIe bus errors — 12VHPWR connector or PSU transient response | Reseat connector, check for discoloration, undervolt GPU, test different PSU |
| Kernel-Power 41 + BugcheckCode 0x3B | SYSTEM_SERVICE_EXCEPTION — kernel driver bug (often NVIDIA) | Check minidump for faulting module, DDU clean install, roll back driver |
| nvlddmkm 14 alone | Driver crash | DDU clean install, roll back to older driver |
| Kernel-Power 41 + BugcheckCode 0 + no GPU events + no gaming context | Sudden power loss unrelated to GPU | Check PSU, wall outlet, UPS |
| WHEA 19 (uncorrectable) | Hardware failure | GPU or PCIe slot may be failing, RMA consideration |
| nvlddmkm 0 + LiveKernelEvent | TDR (Timeout Detection & Recovery) | Increase TDR timeout, check thermals, reduce overclock |
| Unrecognized pattern | Unknown — raw events included | Share report for community help |

### Report Structure

```markdown
# GPU Crash Report - YYYY-MM-DD

## System Info
- GPU: [model]
- Driver: [version]
- VBIOS: [version]
- Windows: [version]
- RAM: [amount]

## What Happened
[Timeline of the most recent crash incident — which events fired, in what order, with timestamps]

## Diagnosis
[Plain-English explanation of what the event pattern means]

## Recommended Actions
1. [Most likely fix]
2. [Second option]
3. [Third option]

## Raw Events
[Full event details for reference or sharing]
```

### Script Interface

```powershell
# Basic usage — analyze last 30 days, report on most recent crash
.\Analyze-GpuCrashes.ps1

# Custom lookback window
.\Analyze-GpuCrashes.ps1 -Days 90

# Include minidump analysis (requires cdb.exe on PATH)
.\Analyze-GpuCrashes.ps1 -IncludeMinidump

# Specify output directory
.\Analyze-GpuCrashes.ps1 -OutputDir "C:\Reports"
```

## Existing Patterns

This is a greenfield project in a new repo. No existing codebase patterns to follow.

The script follows standard PowerShell conventions: verb-noun naming (`Analyze-GpuCrashes`), `CmdletBinding()` with parameter declarations, and `Write-Host` / `Write-Verbose` for console output.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Repo Setup & Script Skeleton
**Goal:** Create the repo structure and a runnable script that collects system info.

**Components:**
- `Analyze-GpuCrashes.ps1` — Script with parameter block and Stage 1 (system info via `Get-CimInstance Win32_VideoController`)
- `README.md` — Usage instructions
- `LICENSE` — MIT
- `.gitignore` — Ignore `reports/` output directory

**Dependencies:** None

**Done when:** Script runs on Windows, outputs GPU model and driver version to console
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Event Collection
**Goal:** Query Event Viewer for GPU crash-related events efficiently.

**Components:**
- Event collection function in `Analyze-GpuCrashes.ps1` — Queries System and Application logs using `Get-WinEvent -FilterHashtable` for nvlddmkm, Kernel-Power, WHEA-Logger, BugCheck, and LiveKernelEvent providers
- `-Days` parameter support for configurable lookback window

**Dependencies:** Phase 1 (script skeleton exists)

**Covers:** gpu-crash-analyzer.AC1

**Done when:** Script retrieves and displays relevant events from Event Viewer, handles case where no events are found
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Crash Correlation
**Goal:** Group raw events into crash incidents using time-window correlation.

**Components:**
- Correlation function in `Analyze-GpuCrashes.ps1` — Groups events within 5-second windows, identifies causal chain (WHEA → nvlddmkm → Kernel-Power), classifies each incident by event pattern

**Dependencies:** Phase 2 (events collected)

**Covers:** gpu-crash-analyzer.AC2

**Done when:** Events are grouped into discrete incidents with classified patterns
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Knowledge Base & Diagnosis
**Goal:** Match crash patterns to diagnoses and produce actionable recommendations.

**Components:**
- Knowledge base hashtable in `Analyze-GpuCrashes.ps1` — Maps event patterns to diagnoses and fix recommendations
- Diagnosis function — Matches most recent incident against knowledge base, falls back to "unrecognized pattern" with raw event dump

**Dependencies:** Phase 3 (incidents classified)

**Covers:** gpu-crash-analyzer.AC3

**Done when:** Script produces a plain-English diagnosis with specific recommended actions for known patterns, and useful output for unknown patterns
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Report Generation
**Goal:** Output a markdown report file with all findings.

**Components:**
- Report generator function in `Analyze-GpuCrashes.ps1` — Assembles system info, crash timeline, diagnosis, and recommendations into markdown
- `-OutputDir` parameter support
- `reports/` default output directory

**Dependencies:** Phase 4 (diagnosis complete)

**Covers:** gpu-crash-analyzer.AC4

**Done when:** Script writes a complete, readable markdown report to disk
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: Optional Minidump Parsing
**Goal:** Extract additional diagnostic info from Windows minidump files when tooling is available.

**Components:**
- Minidump parser function in `Analyze-GpuCrashes.ps1` — Detects `cdb.exe` on PATH, runs automated analysis (`!analyze -v`) on `.dmp` files in `C:\Windows\Minidump\`, extracts bugcheck code and faulting module
- `-IncludeMinidump` switch parameter
- Graceful skip when `cdb.exe` not found

**Dependencies:** Phase 5 (report structure exists to append to)

**Covers:** gpu-crash-analyzer.AC5

**Done when:** Minidump findings appear in report when `-IncludeMinidump` is used and `cdb.exe` is available; script works fine without it
<!-- END_PHASE_6 -->

<!-- START_PHASE_7 -->
### Phase 7: GPU Telemetry Monitor
**Goal:** Lightweight background script that logs GPU state to CSV, surviving hard crashes.

**Components:**
- `Monitor-Gpu.ps1` — Polls `nvidia-smi` at configurable interval, appends CSV with timestamp/power/temp/clocks/utilization, flushes every write
- `-IntervalSeconds`, `-RetentionDays`, `-OutputDir` parameters
- Daily log rotation and old file cleanup
- nvidia-smi detection and error handling

**Dependencies:** None (standalone script, but designed to pair with analyzer)

**Covers:** gpu-crash-analyzer.AC6

**Done when:** Monitor runs in background, produces CSV that survives simulated hard termination (`Stop-Process -Force`), rotates daily
<!-- END_PHASE_7 -->

<!-- START_PHASE_8 -->
### Phase 8: Telemetry Integration in Analyzer
**Goal:** Analyzer reads telemetry CSV and correlates GPU state with crash events.

**Components:**
- Telemetry reader function in `Analyze-GpuCrashes.ps1` — Finds most recent telemetry CSV, extracts rows from the 60 seconds before crash timestamp (from EventLog 6008)
- Report enrichment — Adds "GPU State Before Crash" section showing power draw, temperature, clocks, and utilization trend
- Diagnosis enrichment — Knowledge base uses telemetry to strengthen or refine diagnosis (e.g., high power draw + BugcheckCode 0 = strong power delivery confirmation)

**Dependencies:** Phase 5 (report generation), Phase 7 (monitor produces CSV)

**Covers:** gpu-crash-analyzer.AC7

**Done when:** Report includes telemetry data when CSV is available, diagnosis references GPU state, gracefully omits section when no telemetry exists
<!-- END_PHASE_8 -->

## Additional Considerations

**Permissions:** `Get-WinEvent` for System/Application logs and `Get-CimInstance` work without elevation. Minidump files in `C:\Windows\Minidump\` require admin access. The script should detect and warn if elevation is needed for minidump parsing.

**PowerShell version:** Target PowerShell 5.1 (ships with Windows 10/11) for maximum compatibility. Avoid PowerShell 7+ features.

**nvidia-smi dependency:** The monitor requires `nvidia-smi.exe` which ships with the NVIDIA driver (typically at `C:\Windows\System32\nvidia-smi.exe`). No additional install needed. The analyzer does not require nvidia-smi — it only reads the CSV output.

**Telemetry limitations:** Software polling at 1-second intervals cannot capture microsecond power transients. The telemetry shows GPU state *leading up to* a crash, not the spike itself. This is still valuable — it distinguishes "crash at idle" from "crash at full load during boost" which directly informs the diagnosis.

**Live analysis (2026-04-02):** Ran diagnostic queries against Patrick's machine during design. Found 4 crashes in 30 days — 3 were BugcheckCode 0 (hard power-off, no software trace), 1 was BugcheckCode 0x3B (SYSTEM_SERVICE_EXCEPTION, driver bug). Zero WHEA events. This validated the knowledge base patterns and revealed that EventLog 6008 is essential for getting actual crash timestamps (Kernel-Power 41 records boot time, not crash time). Full report saved in `psford/gpu-crash-analyzer` repo.

**Repo status:** Local repo initialized at `/home/patrick/projects/gpu-crash-analyzer/` with crash report committed. GitHub remote (`psford/gpu-crash-analyzer`) not yet created.
