param([Parameter(Mandatory)][string]$App)

$ErrorActionPreference = "Stop"

# ============================================================================
# LOAD SHARED FUNCTIONS
# ============================================================================

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "deploy-functions.ps1") -App $App

# ============================================================================
# INITIALIZATION
# ============================================================================

$registryPath = Join-Path $scriptDir "app-registry.json"

Write-Host "Deployment: $App" -ForegroundColor Cyan

# Load registry
if (-not (Test-Path $registryPath)) {
    Write-Host "error: app-registry.json not found at $registryPath" -ForegroundColor Red
    exit 1
}

$registry = Get-Content $registryPath | ConvertFrom-Json
if (-not $registry.$App) {
    Write-Host "error: app '$App' not found in registry" -ForegroundColor Red
    exit 1
}

$appConfig = $registry.$App
$repo = $appConfig.repo
$processName = $appConfig.processName
$installDirName = $appConfig.installDir
$startupShortcutName = $appConfig.startupShortcutName
$installDir = Join-Path $env:USERPROFILE "Apps\$installDirName"

Write-Host "  Repo: $repo" -ForegroundColor Cyan
Write-Host "  Install dir: $installDir" -ForegroundColor Cyan

# ============================================================================
# PREREQUISITES CHECK
# ============================================================================

$ghCommand = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghCommand) {
    Write-Host "error: gh CLI not found. Install with: winget install GitHub.cli" -ForegroundColor Red
    exit 1
}

Write-Host "Prerequisites OK" -ForegroundColor Green

# ============================================================================
# DOWNLOAD
# ============================================================================

Write-Host "Downloading release artifacts..." -ForegroundColor Cyan
$tempDir = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) "deploy-$App-$(Get-Random)") -Force
$zipFile = $null
$sha256File = $null
$appsettingsDefaultFile = $null

try {
    # Log download start
    Write-AuditLog "Download started: repo=$repo"

    # Download release artifacts
    & gh release download --pattern "*.zip" -R $repo -D $tempDir
    if ($LASTEXITCODE -ne 0) {
        throw "gh release download (*.zip) failed with exit code $LASTEXITCODE"
    }
    & gh release download --pattern "*.sha256" -R $repo -D $tempDir
    if ($LASTEXITCODE -ne 0) {
        throw "gh release download (*.sha256) failed with exit code $LASTEXITCODE"
    }
    & gh release download --pattern "appsettings.default.json" -R $repo -D $tempDir
    if ($LASTEXITCODE -ne 0) {
        throw "gh release download (appsettings.default.json) failed with exit code $LASTEXITCODE"
    }

    # Find downloaded files
    $zipFile = Get-ChildItem -Path $tempDir -Filter "*.zip" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $zipFile) {
        throw "No .zip file found in release"
    }

    $sha256File = Get-ChildItem -Path $tempDir -Filter "*.sha256" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $sha256File) {
        throw "No .sha256 file found in release"
    }

    $appsettingsDefaultFile = Get-ChildItem -Path $tempDir -Filter "appsettings.default.json" -ErrorAction SilentlyContinue | Select-Object -First 1

    Write-Host "Downloaded: $($zipFile.Name)" -ForegroundColor Green
} catch {
    Write-Host "error: failed to download release artifacts: $_" -ForegroundColor Red
    Write-AuditLog "FAILED: Download failed: $_"
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

# ============================================================================
# VERIFY RELEASE PROVENANCE
# ============================================================================

Write-Host "Verifying release provenance..." -ForegroundColor Cyan
try {
    $provenanceInfo = Assert-ReleaseProvenance -Repo $repo
    Write-AuditLog "Provenance verified: author=$($provenanceInfo.Author)"
} catch {
    Write-Host "error: failed to verify release provenance: $_" -ForegroundColor Red
    Write-AuditLog "FAILED: Provenance verification failed: $_"
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

# ============================================================================
# VERIFY CHECKSUM
# ============================================================================

Write-Host "Verifying checksum..." -ForegroundColor Cyan
try {
    $sha256Content = Get-Content $sha256File.FullName -Raw
    # Format: "<hash>  <filename>"
    $hashMatch = $sha256Content -match '([a-f0-9]{64})\s+(.+)'
    if (-not $hashMatch) {
        throw "Invalid .sha256 file format"
    }

    $expectedHash = $Matches[1]
    $expectedFilename = $Matches[2].Trim()

    $fileHash = (Get-FileHash -Path $zipFile.FullName -Algorithm SHA256).Hash

    if ($fileHash -ne $expectedHash) {
        throw "Checksum mismatch: expected $expectedHash, got $fileHash"
    }

    Write-AuditLog "Checksum verified: $fileHash"
    Write-Host "Checksum verified" -ForegroundColor Green
} catch {
    Write-Host "error: failed to verify checksum: $_" -ForegroundColor Red
    Write-AuditLog "FAILED: Checksum verification failed: $_"
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

# ============================================================================
# STOP PROCESS
# ============================================================================

Write-Host "Stopping existing process..." -ForegroundColor Cyan
$process = Get-Process -Name $processName -ErrorAction SilentlyContinue
if ($process) {
    $process | ForEach-Object {
        Write-Host "  Found process: $($_.Name) (PID: $($_.Id))" -ForegroundColor Yellow
    }
    Stop-Process -Force -InputObject $process
    Start-Sleep -Seconds 2
    Write-AuditLog "Process stopped"
    Write-Host "Process stopped" -ForegroundColor Green
} else {
    Write-AuditLog "Process not running"
    Write-Host "Process not running (OK for first install or crashed)" -ForegroundColor Yellow
}

# ============================================================================
# BACKUP
# ============================================================================

Write-Host "Backing up existing installation..." -ForegroundColor Cyan
$backupDir = Join-Path $tempDir "backup"
if (Test-Path $installDir) {
    # Backup the entire installation directory for complete rollback capability
    Copy-Item -Path $installDir -Destination $backupDir -Recurse -Force
    Write-Host "  Backed up entire installation directory" -ForegroundColor Yellow

    Write-AuditLog "Backup created: complete installation backed up to $backupDir"
    Write-Host "Backup complete" -ForegroundColor Green
} else {
    Write-AuditLog "No existing installation to backup (first install)"
    Write-Host "No existing installation to backup (first install)" -ForegroundColor Yellow
}

# ============================================================================
# EXTRACT THROUGH START (WITH ROLLBACK ON FAILURE)
# ============================================================================

try {
    # ========================================================================
    # EXTRACT
    # ========================================================================

    Write-Host "Extracting release..." -ForegroundColor Cyan
    Expand-Archive -Path $zipFile.FullName -DestinationPath $installDir -Force
    Write-AuditLog "Archive extracted: $($zipFile.Name)"
    Write-Host "Extracted to: $installDir" -ForegroundColor Green

    # ========================================================================
    # RESTORE CONFIG
    # ========================================================================

    Write-Host "Restoring configuration and models..." -ForegroundColor Cyan
    if (Test-Path $backupDir) {
        # Restore appsettings files from backup (prefer user's existing config)
        Get-ChildItem -Path $backupDir -Filter "appsettings*.json" -ErrorAction SilentlyContinue | ForEach-Object {
            $destPath = Join-Path $installDir $_.Name
            Assert-PathWithinInstallDir -Path $destPath -InstallDir $installDir
            Copy-Item -Path $_.FullName -Destination $destPath -Force
            Write-Host "  Restored: $($_.Name)" -ForegroundColor Green
        }

        # Restore models directory from backup (avoid re-downloading)
        $backupModelsDir = Join-Path $backupDir "models"
        if (Test-Path $backupModelsDir) {
            $destModelsDir = Join-Path $installDir "models"
            Assert-PathWithinInstallDir -Path $destModelsDir -InstallDir $installDir
            Remove-Item -Path $destModelsDir -Recurse -Force -ErrorAction SilentlyContinue
            Copy-Item -Path $backupModelsDir -Destination $destModelsDir -Recurse -Force
            Write-Host "  Restored: models/" -ForegroundColor Green
        }
        Write-AuditLog "Config and models restored from backup"
    } elseif ($appsettingsDefaultFile -and (Test-Path $appsettingsDefaultFile.FullName)) {
        # First install: copy default appsettings
        $destPath = Join-Path $installDir "appsettings.json"
        Assert-PathWithinInstallDir -Path $destPath -InstallDir $installDir
        Copy-Item -Path $appsettingsDefaultFile.FullName -Destination $destPath -Force
        Write-Host "  Created default: appsettings.json" -ForegroundColor Green
        Write-AuditLog "Config: first install — defaults applied"
    }

    Write-Host "Configuration and models restored" -ForegroundColor Green

    # ========================================================================
    # MODEL CHECK & DOWNLOAD
    # ========================================================================

    Write-Host "Checking models..." -ForegroundColor Cyan

    if ($appConfig.models -is [System.Array]) {
        # Array format (SysTTS and future apps)
        Write-Host "  Using array format for models" -ForegroundColor Yellow

        foreach ($modelEntry in $appConfig.models) {
            $source = $modelEntry.source
            $targetDir = $modelEntry.targetDir
            $targetPath = Join-Path $installDir $targetDir

            # Validate path is within install directory
            Assert-PathWithinInstallDir -Path $targetPath -InstallDir $installDir

            # Ensure target directory exists
            New-Item -ItemType Directory -Path $targetPath -Force | Out-Null

            if ($source -eq "huggingface") {
                # Support both singular file and plural files array
                $files = @()
                if ($modelEntry.files -is [System.Array]) {
                    # Multiple files (e.g., ONNX model + JSON config)
                    $files = $modelEntry.files
                } elseif ($modelEntry.file) {
                    # Single file
                    $files = @($modelEntry.file)
                } else {
                    throw "Hugging Face model entry must have either 'files' (array) or 'file' (string)"
                }

                # Download each file
                foreach ($file in $files) {
                    $url = "$($modelEntry.baseUrl)/$file"
                    $downloadPath = Join-Path $targetPath $file

                    if (-not (Test-Path $downloadPath)) {
                        Write-Host "  Downloading from Hugging Face: $file" -ForegroundColor Yellow
                        Invoke-WebRequestWithRetry -Uri $url -OutFile $downloadPath -Filename $file
                        Write-Host "    Downloaded: $file" -ForegroundColor Green
                    } else {
                        Write-Host "    Already exists: $file" -ForegroundColor Green
                    }

                    if ($modelEntry.extract) {
                        Write-Host "    Extracting: $file" -ForegroundColor Yellow
                        tar -xf $downloadPath -C $targetPath
                        if ($LASTEXITCODE -ne 0) {
                            throw "tar extraction failed for $file with exit code $LASTEXITCODE"
                        }
                        Remove-Item -Path $downloadPath -Force
                    }
                }
            } elseif ($source -eq "github-release") {
                $modelRepo = $modelEntry.repo
                $tag = $modelEntry.tag
                $file = $modelEntry.file
                $downloadPath = Join-Path $targetPath $file

                # Check if extracted output already exists (avoid re-downloading and re-extracting)
                $extractedMarker = $false
                if ($modelEntry.extract) {
                    # For extracted archives, check if the extracted content exists
                    # This is a simple heuristic; adjust if needed based on archive structure
                    $baseName = $file
                    # Strip known compound archive extensions before using GetFileNameWithoutExtension
                    if ($baseName -match '\.tar\.(bz2|gz|xz|zst)$') {
                        $baseName = $baseName -replace '\.tar\.(bz2|gz|xz|zst)$', ''
                    } else {
                        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($baseName)
                    }
                    $extractedPath = Join-Path $targetPath $baseName
                    if (Test-Path $extractedPath) {
                        Write-Host "    Already extracted: $file" -ForegroundColor Green
                        $extractedMarker = $true
                    }
                } else {
                    # For non-extracted files, check if the file exists
                    if (Test-Path $downloadPath) {
                        Write-Host "    Already exists: $file" -ForegroundColor Green
                        $extractedMarker = $true
                    }
                }

                if (-not $extractedMarker) {
                    Write-Host "  Downloading from GitHub release: $modelRepo@$tag" -ForegroundColor Yellow
                    $retries = 3
                    $backoffSeconds = 2
                    $success = $false

                    for ($i = 0; $i -lt $retries; $i++) {
                        try {
                            & gh release download $tag -R $modelRepo --pattern $file -D $targetPath
                            if ($LASTEXITCODE -ne 0) {
                                throw "gh release download failed with exit code $LASTEXITCODE"
                            }
                            $success = $true
                            break
                        } catch {
                            if ($i -lt $retries - 1) {
                                Write-Host "    Retry $($i + 1)/$retries in ${backoffSeconds}s..." -ForegroundColor Yellow
                                Write-AuditLog "Model download retry (github-release): $file (attempt $($i + 1)/$retries)"
                                Start-Sleep -Seconds $backoffSeconds
                                $backoffSeconds *= 2
                            } else {
                                Write-AuditLog "FAILED: GitHub release download failed after $retries attempts: $file - $_"
                            }
                        }
                    }

                    if (-not $success) {
                        throw "Failed to download from GitHub release: $file after $retries attempts"
                    }

                    Write-Host "    Downloaded: $file" -ForegroundColor Green

                    if ($modelEntry.extract) {
                        Write-Host "    Extracting: $file" -ForegroundColor Yellow
                        tar -xf $downloadPath -C $targetPath
                        if ($LASTEXITCODE -ne 0) {
                            throw "tar extraction failed for $file with exit code $LASTEXITCODE"
                        }
                        Remove-Item -Path $downloadPath -Force
                    }
                }
            }
        }
    } else {
        # Object format (whisper-service)
        Write-Host "  Using object format for models" -ForegroundColor Yellow

        $modelsConfig = $appConfig.models
        $source = $modelsConfig.source

        if ($source -eq "huggingface") {
            # Read model name from appsettings.json
            $appsettingsPath = Join-Path $installDir "appsettings.json"
            if (Test-Path $appsettingsPath) {
                try {
                    $settings = Get-Content $appsettingsPath | ConvertFrom-Json
                    $configSection = $modelsConfig.configSection
                    $configKey = $modelsConfig.configKey

                    $modelName = $settings.$configSection.$configKey
                    if ($modelName) {
                        $filePattern = $modelsConfig.filePattern
                        $filename = $filePattern -replace '\{model\}', $modelName
                        $modelsDir = Join-Path $installDir "models"
                        Assert-PathWithinInstallDir -Path $modelsDir -InstallDir $installDir
                        New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null

                        $modelPath = Join-Path $modelsDir $filename
                        if (-not (Test-Path $modelPath)) {
                            $baseUrl = $modelsConfig.baseUrl
                            $url = "$baseUrl/$filename"

                            Write-Host "  Downloading model: $filename" -ForegroundColor Yellow
                            Invoke-WebRequestWithRetry -Uri $url -OutFile $modelPath -Filename $filename
                            Write-Host "    Downloaded: $filename" -ForegroundColor Green
                        } else {
                            Write-Host "  Model already exists: $filename" -ForegroundColor Green
                        }
                    } else {
                        Write-Host "  Model config not found in appsettings.json" -ForegroundColor Yellow
                    }
                } catch {
                    Write-Host "warning: failed to parse appsettings.json: $_" -ForegroundColor Yellow
                }
            }
        }
    }

    Write-AuditLog "Models checked"
    Write-Host "Model check complete" -ForegroundColor Green

    # ========================================================================
    # UPDATE STARTUP SHORTCUT
    # ========================================================================

    Write-Host "Updating startup shortcut..." -ForegroundColor Cyan
    $startupFolder = [Environment]::GetFolderPath('Startup')
    $shortcutPath = Join-Path $startupFolder "$startupShortcutName.lnk"

    if (Test-Path $shortcutPath) {
        try {
            $shell = New-Object -ComObject WScript.Shell
            $shortcut = $shell.CreateShortCut($shortcutPath)

            # Find the executable in the install directory
            $exe = Get-ChildItem -Path $installDir -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($exe) {
                $shortcut.TargetPath = $exe.FullName
                $shortcut.WorkingDirectory = $installDir
                $shortcut.Save()
                Write-Host "Updated shortcut: $shortcutPath" -ForegroundColor Green
            } else {
                Write-Host "warning: no .exe found in install directory" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "warning: failed to update shortcut: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Shortcut not found (OK if not yet created)" -ForegroundColor Yellow
    }

    # ========================================================================
    # START PROCESS
    # ========================================================================

    Write-Host "Starting application..." -ForegroundColor Cyan
    $exe = Get-ChildItem -Path $installDir -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1

    if ($exe) {
        Start-Process -FilePath $exe.FullName -WorkingDirectory $installDir
        Write-Host "Process started: $($exe.Name)" -ForegroundColor Green

        # Wait for process to appear (up to 10 seconds, check every 500ms)
        $waitSeconds = 10
        $checkIntervalMs = 500
        $stopTime = [datetime]::Now.AddSeconds($waitSeconds)
        $found = $false

        while ([datetime]::Now -lt $stopTime) {
            $running = Get-Process -Name $processName -ErrorAction SilentlyContinue
            if ($running) {
                $running | ForEach-Object {
                    Write-Host "Confirmed running: $($_.Name) (PID: $($_.Id))" -ForegroundColor Green
                    Write-AuditLog "Process started: PID=$($_.Id)"
                }
                $found = $true
                break
            }
            Start-Sleep -Milliseconds $checkIntervalMs
        }

        if (-not $found) {
            Write-Host "warning: process not confirmed running after $waitSeconds seconds" -ForegroundColor Yellow
        }
    } else {
        throw "No .exe file found in install directory"
    }

} catch {
    # ========================================================================
    # ROLLBACK ON FAILURE
    # ========================================================================

    Write-Host "error: deployment failed: $_" -ForegroundColor Red
    Write-AuditLog "FAILED: $_"
    Write-Host "Attempting rollback..." -ForegroundColor Yellow

    # (1) Restore backup if it exists
    if (Test-Path $backupDir) {
        Write-Host "  Restoring backup..." -ForegroundColor Yellow

        # Remove the corrupted install directory
        if (Test-Path $installDir) {
            Remove-Item -Path $installDir -Recurse -Force -ErrorAction SilentlyContinue
        }

        # Restore entire backup directory (includes binaries, config, and models)
        Copy-Item -Path "$backupDir\*" -Destination $installDir -Recurse -Force
        Write-Host "    Restored complete installation from backup" -ForegroundColor Yellow

        Write-AuditLog "Rollback: backup restored (complete installation)"
        Write-Host "Backup restored" -ForegroundColor Yellow
    }

    # (2) Attempt to restart old process
    $process = Get-Process -Name $processName -ErrorAction SilentlyContinue
    if (-not $process) {
        Write-Host "  Searching for previous executable to restart..." -ForegroundColor Yellow

        # Find the executable in the install directory (now restored from backup)
        $exe = Get-ChildItem -Path $installDir -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($exe) {
            try {
                Start-Process -FilePath $exe.FullName -WorkingDirectory $installDir
                Write-AuditLog "Rollback: old process restarted"
                Write-Host "  Old process restarted" -ForegroundColor Yellow
            } catch {
                Write-Host "  warning: could not restart old process: $_" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  warning: no executable found to restart" -ForegroundColor Yellow
        }
    }

    # (3) Clean up temp directory
    Write-Host "  Cleaning up temporary files..." -ForegroundColor Yellow
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue

    # (4) Exit with error
    Write-Host "Rollback complete" -ForegroundColor Red
    exit 1
}

# ============================================================================
# CLEANUP
# ============================================================================

Write-Host "Cleaning up..." -ForegroundColor Cyan
Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Cleanup complete" -ForegroundColor Green

# ============================================================================
# SUCCESS
# ============================================================================

Write-AuditLog "Deploy complete: success"
Write-Host "Deployment successful: $App" -ForegroundColor Green
exit 0
