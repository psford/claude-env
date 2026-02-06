# Whisper Dictation Startup Installer
# This installs the app to run at user login (better than Windows Service for desktop interaction)

$ErrorActionPreference = "Stop"

# Get the directory where the script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check for release build first, then debug
$exePath = Join-Path $scriptDir "WhisperService\bin\Release\net8.0-windows\WhisperService.exe"
if (-not (Test-Path $exePath)) {
    $exePath = Join-Path $scriptDir "WhisperService\bin\Debug\net8.0-windows\WhisperService.exe"
}

if (-not (Test-Path $exePath)) {
    Write-Error "WhisperService.exe not found. Build the project first with 'dotnet build'"
    exit 1
}

$exeDir = Split-Path -Parent $exePath

Write-Host "Installing Whisper Dictation to Startup..." -ForegroundColor Cyan
Write-Host "Executable: $exePath"

# Create models directory if it doesn't exist
$modelsDir = Join-Path $exeDir "models"
if (-not (Test-Path $modelsDir)) {
    New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
    Write-Host "Created models directory: $modelsDir" -ForegroundColor Green
}

# Check for model file
$modelFile = Join-Path $modelsDir "ggml-base.bin"
if (-not (Test-Path $modelFile)) {
    Write-Host ""
    Write-Host "WARNING: Whisper model not found!" -ForegroundColor Yellow
    Write-Host "Download ggml-base.bin from:"
    Write-Host "https://huggingface.co/ggerganov/whisper.cpp/tree/main" -ForegroundColor Cyan
    Write-Host "Place it in: $modelsDir"
    Write-Host ""
}

# Create shortcut in Startup folder
$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder "WhisperDictation.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = $exeDir
$shortcut.Description = "Whisper Dictation Service"
$shortcut.Save()

Write-Host ""
Write-Host "Startup shortcut created at:" -ForegroundColor Green
Write-Host $shortcutPath
Write-Host ""
Write-Host "The application will start automatically when you log in." -ForegroundColor Cyan
Write-Host ""

# Kill any existing instance
$existingProcess = Get-Process -Name "WhisperService" -ErrorAction SilentlyContinue
if ($existingProcess) {
    Write-Host "Stopping existing instance..." -ForegroundColor Yellow
    Stop-Process -Name "WhisperService" -Force
    Start-Sleep -Seconds 1
}

# Start the application now
Write-Host "Starting Whisper Dictation..." -ForegroundColor Cyan
Start-Process -FilePath $exePath -WorkingDirectory $exeDir

Write-Host ""
Write-Host "Whisper Dictation is now running!" -ForegroundColor Green
Write-Host "Look for the microphone icon in the system tray." -ForegroundColor Cyan
Write-Host ""
Write-Host "Hotkeys:" -ForegroundColor Cyan
Write-Host "  F24 (Stream Deck): Press to start, press to stop"
Write-Host "  Ctrl+Alt+V: Hold to record, release to transcribe"
Write-Host ""
Write-Host "To remove from startup:" -ForegroundColor Yellow
Write-Host "  Remove-Item '$shortcutPath'"
