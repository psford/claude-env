using WhisperService.Services;

namespace WhisperService;

/// <summary>
/// Main worker that orchestrates dictation functionality
/// </summary>
public class DictationWorker : BackgroundService
{
    private readonly ILogger<DictationWorker> _logger;
    private readonly TranscriptionService _transcription;
    private readonly AudioCaptureService _audioCapture;
    private readonly InputService _input;
    private readonly TrayIconService _trayIcon;

    private bool _isRecording;
    private readonly object _lock = new();

    public DictationWorker(
        ILogger<DictationWorker> logger,
        TranscriptionService transcription,
        AudioCaptureService audioCapture,
        InputService input,
        TrayIconService trayIcon)
    {
        _logger = logger;
        _transcription = transcription;
        _audioCapture = audioCapture;
        _input = input;
        _trayIcon = trayIcon;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Whisper Dictation Service starting...");

        try
        {
            // Hotkey events are wired up by ApplicationContext on main thread
            _logger.LogInformation("Whisper Dictation Service ready");

            // Keep running until cancelled
            await Task.Delay(Timeout.Infinite, stoppingToken);
        }
        catch (OperationCanceledException)
        {
            _logger.LogInformation("Service stopping...");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Service error");
            throw;
        }
    }

    // Public event handlers - called from main thread by ApplicationContext
    public void OnToggleRecording(object? sender, EventArgs e)
    {
        lock (_lock)
        {
            if (_isRecording)
            {
                StopRecordingAndTranscribe();
            }
            else
            {
                StartRecording();
            }
        }
    }

    public void OnRecordingStartRequested(object? sender, EventArgs e)
    {
        lock (_lock)
        {
            if (!_isRecording)
            {
                StartRecording();
            }
        }
    }

    public void OnRecordingStopRequested(object? sender, EventArgs e)
    {
        lock (_lock)
        {
            if (_isRecording)
            {
                StopRecordingAndTranscribe();
            }
        }
    }

    private void StartRecording()
    {
        try
        {
            _audioCapture.StartRecording();
            _isRecording = true;
            _trayIcon.SetRecordingState(true);
            _logger.LogInformation("Recording started");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to start recording");
            _trayIcon.ShowNotification("Recording Error", ex.Message, ToolTipIcon.Error);
        }
    }

    private void StopRecordingAndTranscribe()
    {
        _isRecording = false;
        _trayIcon.SetRecordingState(false);

        var samples = _audioCapture.StopRecording();
        if (samples == null || samples.Length == 0)
        {
            _logger.LogWarning("No audio samples captured");
            return;
        }

        // Transcribe and output in background to not block hotkey handling
        _ = Task.Run(async () =>
        {
            try
            {
                var text = await _transcription.TranscribeAsync(samples);
                if (!string.IsNullOrWhiteSpace(text))
                {
                    await _input.OutputTextAsync(text);
                }
                else
                {
                    _logger.LogWarning("No speech detected");
                }
            }
            catch (FileNotFoundException ex)
            {
                _logger.LogError(ex, "Model not found");
                _trayIcon.ShowNotification("Model Error",
                    "Whisper model not found. Please download the model file.",
                    ToolTipIcon.Error);
            }
            catch (Exception ex)
            {
                var innerMsg = ex.InnerException?.Message ?? "";
                _logger.LogError(ex, "Transcription failed. Inner: {Inner}", innerMsg);

                // Write detailed error to file for debugging
                var errorLog = Path.Combine(AppContext.BaseDirectory, "whisper_error.log");
                File.WriteAllText(errorLog, $"{DateTime.Now}: {ex}\n\nInner: {ex.InnerException}");

                _trayIcon.ShowNotification("Transcription Error", ex.Message, ToolTipIcon.Error);
            }
        });
    }
}
