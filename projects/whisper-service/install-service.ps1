# Whisper Dictation Service Installer
# Run as Administrator

$ErrorActionPreference = "Stop"

$serviceName = "WhisperDictation"
$displayName = "Whisper Dictation Service"
$description = "Voice-to-text dictation using OpenAI Whisper"

# Get the directory where the script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $scriptDir "WhisperService\bin\Release\net8.0-windows\WhisperService.exe"

# Check if published release exists, otherwise use debug
if (-not (Test-Path $exePath)) {
    $exePath = Join-Path $scriptDir "WhisperService\bin\Debug\net8.0-windows\WhisperService.exe"
}

if (-not (Test-Path $exePath)) {
    Write-Error "WhisperService.exe not found. Build the project first with 'dotnet build'"
    exit 1
}

$exeDir = Split-Path -Parent $exePath

Write-Host "Installing Whisper Dictation Service..." -ForegroundColor Cyan
Write-Host "Executable: $exePath"
Write-Host "Working Directory: $exeDir"

# Check for NSSM
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Host "NSSM not found. Installing via winget..." -ForegroundColor Yellow
    winget install nssm
    $nssm = Get-Command nssm -ErrorAction SilentlyContinue
    if (-not $nssm) {
        Write-Error "Failed to install NSSM. Install it manually: winget install nssm"
        exit 1
    }
}

# Stop existing service if running
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Stopping existing service..." -ForegroundColor Yellow
    nssm stop $serviceName
    Start-Sleep -Seconds 2
    Write-Host "Removing existing service..." -ForegroundColor Yellow
    nssm remove $serviceName confirm
    Start-Sleep -Seconds 1
}

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

# Install service
Write-Host "Installing service with NSSM..." -ForegroundColor Cyan
nssm install $serviceName $exePath
nssm set $serviceName AppDirectory $exeDir
nssm set $serviceName DisplayName $displayName
nssm set $serviceName Description $description
nssm set $serviceName Start SERVICE_AUTO_START
nssm set $serviceName ObjectName LocalSystem
nssm set $serviceName Type SERVICE_INTERACTIVE_PROCESS

# Note: Interactive services have limitations on modern Windows
# For full desktop interaction, consider running as a startup app instead

Write-Host ""
Write-Host "Service installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Commands:" -ForegroundColor Cyan
Write-Host "  Start:   nssm start $serviceName"
Write-Host "  Stop:    nssm stop $serviceName"
Write-Host "  Status:  nssm status $serviceName"
Write-Host "  Remove:  nssm remove $serviceName"
Write-Host ""

# Start the service
Write-Host "Starting service..." -ForegroundColor Cyan
nssm start $serviceName

Write-Host ""
Write-Host "Service started. Check the system tray for the microphone icon." -ForegroundColor Green
Write-Host "Hotkeys: F24 (toggle) or Ctrl+Alt+V (hold)" -ForegroundColor Cyan
