# Whisper Dictation Service

A Windows Service for voice-to-text dictation using OpenAI's Whisper model. Press a hotkey to record, release to transcribe and paste.

## Features

- **Toggle Mode** (F24): Press to start recording, press again to stop and transcribe. Perfect for Stream Deck.
- **Hold Mode** (Ctrl+Alt+V): Hold to record, release to transcribe.
- **System Tray**: Blue microphone icon when ready, red when recording.
- **Auto-paste**: Transcribed text is automatically pasted and Enter is pressed (configurable).
- **Windows Service**: Runs on startup, survives crashes.

## Requirements

- Windows 10/11
- .NET 8.0 Runtime
- Whisper model file (downloaded separately)

## Quick Start

### 1. Download Whisper Model

Download the model from [Hugging Face](https://huggingface.co/ggerganov/whisper.cpp/tree/main):

- **Base** (recommended): `ggml-base.bin` (~142 MB) - Good balance of speed and accuracy
- **Medium**: `ggml-medium.bin` (~1.5 GB) - Better accuracy, slower

Place the model file in the `models` folder:
```
WhisperService/
├── models/
│   └── ggml-base.bin
├── WhisperService.exe
├── appsettings.json
└── ...
```

### 2. Run the Application

```powershell
# Run directly
.\WhisperService.exe

# Or install as Windows Service (recommended)
.\install-service.ps1
```

### 3. Use Hotkeys

- **F24** (Stream Deck): Press to start, press again to stop
- **Ctrl+Alt+V**: Hold to record, release to transcribe

The transcribed text is automatically pasted into the active application.

## Configuration

Edit `appsettings.json` to customize:

```json
{
  "Whisper": {
    "ModelPath": "models",        // Path to model files
    "ModelSize": "base",          // tiny, base, small, medium, large
    "Language": "en",             // Language code
    "MinRecordingSeconds": 0.5,   // Ignore very short recordings
    "MaxRecordingSeconds": 60     // Safety limit
  },
  "Hotkeys": {
    "ToggleKey": "F24",           // Toggle mode key
    "HoldModifiers": ["Control", "Alt"],
    "HoldKey": "V"                // Hold mode key
  },
  "Output": {
    "Mode": "PasteAndEnter",      // PasteAndEnter, PasteOnly, ClipboardOnly
    "ClipboardDelayMs": 200,
    "EnterDelayMs": 100
  }
}
```

### Output Modes

| Mode | Behavior |
|------|----------|
| `PasteAndEnter` | Copy to clipboard, Ctrl+V, Enter |
| `PasteOnly` | Copy to clipboard, Ctrl+V |
| `ClipboardOnly` | Copy to clipboard only |

## Installing as Windows Service

Run the installation script as Administrator:

```powershell
.\install-service.ps1
```

Or manually with NSSM:

```powershell
# Install NSSM if not present
winget install nssm

# Install service
nssm install WhisperDictation "C:\path\to\WhisperService.exe"
nssm set WhisperDictation AppDirectory "C:\path\to"
nssm set WhisperDictation DisplayName "Whisper Dictation Service"
nssm set WhisperDictation Start SERVICE_AUTO_START

# Start service
nssm start WhisperDictation
```

## Troubleshooting

### Model not found
Ensure `ggml-{size}.bin` is in the `models` folder relative to the exe.

### No audio recorded
Check Windows audio input settings. The default microphone is used.

### Hotkey not working
The service needs to run with desktop interaction. If installed as a Windows Service, ensure it runs in the user session.

## Development

```powershell
# Build
cd WhisperService
dotnet build

# Run
dotnet run

# Publish (self-contained)
dotnet publish -c Release -r win-x64 --self-contained
```

## License

MIT
