param([Parameter(Mandatory)][string]$App)

<#
.SYNOPSIS
Write an entry to the deployment audit log.
This creates a timestamped record of all deployment actions for compliance and debugging.

.PARAMETER Message
The message to log (e.g., "Checksum verified: abc123def456").

.DESCRIPTION
Appends a timestamped entry to the audit log file at %USERPROFILE%\Apps\deploy-log.txt.
Each entry includes the timestamp, app name, and message.
Format: yyyy-MM-dd HH:mm:ss | <App> | <Message>
#>
function Write-AuditLog {
    param([string]$Message)
    $logFile = Join-Path $env:USERPROFILE "Apps\deploy-log.txt"
    $logDir = Split-Path $logFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $App | $Message" | Out-File -FilePath $logFile -Append -Encoding UTF8
}

<#
.SYNOPSIS
Verify that a release was created by GitHub Actions (CI).
This ensures only automated, verified builds are deployed.

.PARAMETER Repo
The GitHub repository in owner/repo format.

.DESCRIPTION
Queries release metadata via gh API to confirm the release was authored
by 'github-actions[bot]'. Returns the tag and version on success.
Throws error if authored by manual upload or user.
#>
function Assert-ReleaseProvenance {
    param(
        [Parameter(Mandatory)][string]$Repo
    )

    try {
        $releaseInfo = gh api "repos/$repo/releases/latest" | ConvertFrom-Json

        # Validate API response contains expected fields
        if (-not $releaseInfo -or -not $releaseInfo.PSObject.Properties["author"]) {
            throw "Release metadata missing author field"
        }

        $authorLogin = $releaseInfo.author.login
        $releaseTag = $releaseInfo.tag_name
        $releaseName = $releaseInfo.name

        # Layer 1: Entry validation - check author field exists
        if (-not $authorLogin) {
            throw "Release author is empty or null"
        }

        # Layer 2: Business logic validation - verify it's the CI bot
        if ($authorLogin -ne "github-actions[bot]") {
            throw "Release was not created by GitHub Actions (author: $authorLogin). Refusing to deploy."
        }

        Write-Host "Release provenance verified: $releaseTag (author: $authorLogin)" -ForegroundColor Green
        return @{
            Tag = $releaseTag
            Name = $releaseName
            Author = $authorLogin
        }
    } catch {
        throw "Failed to verify release provenance: $_"
    }
}

<#
.SYNOPSIS
Validate that a path is contained within the install directory.
This prevents directory traversal attacks that attempt to write outside the intended location.

.PARAMETER Path
The path to validate (may contain .. or other traversal attempts).

.PARAMETER InstallDir
The base install directory that all writes must be contained within.

.DESCRIPTION
Resolves both paths to their absolute forms and checks that the target path
is within the install directory. Throws if any attempt to escape is detected.
#>
function Assert-PathWithinInstallDir {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$InstallDir
    )

    try {
        # Resolve paths to absolute form to handle .. and other traversal attempts
        $resolvedPath = [System.IO.Path]::GetFullPath($Path)
        $resolvedInstall = [System.IO.Path]::GetFullPath($InstallDir)

        # Ensure install dir ends with separator for proper prefix matching
        if (-not $resolvedInstall.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
            $resolvedInstall += [System.IO.Path]::DirectorySeparatorChar
        }

        # Check containment: path must start with install directory (case-insensitive on Windows)
        if (-not $resolvedPath.StartsWith($resolvedInstall, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Path '$resolvedPath' is outside install directory '$($resolvedInstall.TrimEnd([System.IO.Path]::DirectorySeparatorChar))'. Refusing to write."
        }
    } catch {
        throw "Path validation failed: $_"
    }
}
