param([Parameter(Mandatory)][string]$App)

$ErrorActionPreference = "Stop"

# ============================================================================
# INITIALIZATION
# ============================================================================

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
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

    Write-Host "Checksum verified" -ForegroundColor Green
} catch {
    Write-Host "error: failed to verify checksum: $_" -ForegroundColor Red
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
    Write-Host "Process stopped" -ForegroundColor Green
} else {
    Write-Host "Process not running (OK for first install or crashed)" -ForegroundColor Yellow
}

# ============================================================================
# BACKUP
# ============================================================================

Write-Host "Backing up existing installation..." -ForegroundColor Cyan
$backupDir = Join-Path $tempDir "backup"
if (Test-Path $installDir) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

    # Backup appsettings files
    Get-ChildItem -Path $installDir -Filter "appsettings*.json" -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $backupDir -Force
        Write-Host "  Backed up: $($_.Name)" -ForegroundColor Yellow
    }

    # Backup models directory
    $modelsDir = Join-Path $installDir "models"
    if (Test-Path $modelsDir) {
        Copy-Item -Path $modelsDir -Destination $backupDir -Recurse -Force
        Write-Host "  Backed up: models/" -ForegroundColor Yellow
    }

    Write-Host "Backup complete" -ForegroundColor Green
} else {
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
    Write-Host "Extracted to: $installDir" -ForegroundColor Green

    # ========================================================================
    # RESTORE CONFIG
    # ========================================================================

    Write-Host "Restoring configuration..." -ForegroundColor Cyan
    if (Test-Path $backupDir) {
        # Restore appsettings files from backup
        Get-ChildItem -Path $backupDir -Filter "appsettings*.json" -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $installDir -Force
            Write-Host "  Restored: $($_.Name)" -ForegroundColor Green
        }

        # Restore models directory from backup
        $backupModelsDir = Join-Path $backupDir "models"
        if (Test-Path $backupModelsDir) {
            $destModelsDir = Join-Path $installDir "models"
            Remove-Item -Path $destModelsDir -Recurse -Force -ErrorAction SilentlyContinue
            Copy-Item -Path $backupModelsDir -Destination $destModelsDir -Recurse -Force
            Write-Host "  Restored: models/" -ForegroundColor Green
        }
    } elseif ($appsettingsDefaultFile -and (Test-Path $appsettingsDefaultFile.FullName)) {
        # First install: copy default appsettings
        Copy-Item -Path $appsettingsDefaultFile.FullName -Destination (Join-Path $installDir "appsettings.json") -Force
        Write-Host "  Created default: appsettings.json" -ForegroundColor Green
    }

    Write-Host "Configuration restored" -ForegroundColor Green

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

            # Ensure target directory exists
            New-Item -ItemType Directory -Path $targetPath -Force | Out-Null

            if ($source -eq "huggingface") {
                $file = $modelEntry.file
                $url = "$($modelEntry.baseUrl)/$file"
                $downloadPath = Join-Path $targetPath $file

                if (-not (Test-Path $downloadPath)) {
                    Write-Host "  Downloading from Hugging Face: $file" -ForegroundColor Yellow
                    $retries = 3
                    $backoffSeconds = 2
                    $success = $false

                    for ($i = 0; $i -lt $retries; $i++) {
                        try {
                            Invoke-WebRequest -Uri $url -OutFile $downloadPath -UseBasicParsing
                            $success = $true
                            break
                        } catch {
                            if ($i -lt $retries - 1) {
                                Write-Host "    Retry $($i + 1)/$retries in ${backoffSeconds}s..." -ForegroundColor Yellow
                                Start-Sleep -Seconds $backoffSeconds
                                $backoffSeconds *= 2
                            }
                        }
                    }

                    if (-not $success) {
                        throw "Failed to download model: $file"
                    }
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
            } elseif ($source -eq "github-release") {
                $modelRepo = $modelEntry.repo
                $tag = $modelEntry.tag
                $file = $modelEntry.file

                Write-Host "  Downloading from GitHub release: $modelRepo@$tag" -ForegroundColor Yellow
                & gh release download $tag -R $modelRepo --pattern $file -D $targetPath
                if ($LASTEXITCODE -ne 0) {
                    throw "gh release download (model $file) failed with exit code $LASTEXITCODE"
                }

                if ($modelEntry.extract) {
                    Write-Host "    Extracting: $file" -ForegroundColor Yellow
                    $downloadPath = Join-Path $targetPath $file
                    tar -xf $downloadPath -C $targetPath
                    if ($LASTEXITCODE -ne 0) {
                        throw "tar extraction failed for $file with exit code $LASTEXITCODE"
                    }
                    Remove-Item -Path $downloadPath -Force
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
                        New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null

                        $modelPath = Join-Path $modelsDir $filename
                        if (-not (Test-Path $modelPath)) {
                            $baseUrl = $modelsConfig.baseUrl
                            $url = "$baseUrl/$filename"

                            Write-Host "  Downloading model: $filename" -ForegroundColor Yellow

                            $retries = 3
                            $backoffSeconds = 2
                            $success = $false

                            for ($i = 0; $i -lt $retries; $i++) {
                                try {
                                    Invoke-WebRequest -Uri $url -OutFile $modelPath -UseBasicParsing
                                    $success = $true
                                    break
                                } catch {
                                    if ($i -lt $retries - 1) {
                                        Write-Host "    Retry $($i + 1)/$retries in ${backoffSeconds}s..." -ForegroundColor Yellow
                                        Start-Sleep -Seconds $backoffSeconds
                                        $backoffSeconds *= 2
                                    } else {
                                        throw $_
                                    }
                                }
                            }

                            if (-not $success) {
                                throw "Failed to download model after $retries attempts"
                            }

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
    Write-Host "Attempting rollback..." -ForegroundColor Yellow

    # (1) Restore backup if it exists
    if (Test-Path $backupDir) {
        Write-Host "  Restoring backup..." -ForegroundColor Yellow

        # Remove the corrupted install directory
        if (Test-Path $installDir) {
            Remove-Item -Path $installDir -Recurse -Force -ErrorAction SilentlyContinue
        }

        # Recreate install directory and copy backup contents
        New-Item -ItemType Directory -Path $installDir -Force | Out-Null

        # Restore appsettings files
        Get-ChildItem -Path $backupDir -Filter "appsettings*.json" -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $installDir -Force
            Write-Host "    Restored: $($_.Name)" -ForegroundColor Yellow
        }

        # Restore models directory
        $backupModelsDir = Join-Path $backupDir "models"
        if (Test-Path $backupModelsDir) {
            Copy-Item -Path $backupModelsDir -Destination (Join-Path $installDir "models") -Recurse -Force
            Write-Host "    Restored: models/" -ForegroundColor Yellow
        }

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

Write-Host "Deployment successful: $App" -ForegroundColor Green
exit 0
