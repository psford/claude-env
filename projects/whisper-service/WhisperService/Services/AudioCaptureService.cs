using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using NAudio.Wave;
using WhisperService.Models;

namespace WhisperService.Services;

/// <summary>
/// Handles audio capture from the default microphone
/// </summary>
public class AudioCaptureService : IDisposable
{
    private readonly ILogger<AudioCaptureService> _logger;
    private readonly WhisperSettings _settings;
    private WaveInEvent? _waveIn;
    private readonly List<float> _buffer = new();
    private readonly object _lock = new();
    private bool _isRecording;
    private bool _disposed;

    public bool IsRecording => _isRecording;

    public event EventHandler<RecordingStoppedEventArgs>? RecordingStopped;

    public AudioCaptureService(
        ILogger<AudioCaptureService> logger,
        IOptions<WhisperSettings> settings)
    {
        _logger = logger;
        _settings = settings.Value;
    }

    /// <summary>
    /// Start recording audio from the microphone
    /// </summary>
    public void StartRecording()
    {
        lock (_lock)
        {
            if (_isRecording)
            {
                _logger.LogWarning("Already recording");
                return;
            }

            _buffer.Clear();

            _waveIn = new WaveInEvent
            {
                WaveFormat = new WaveFormat(_settings.SampleRate, 16, 1), // 16-bit mono
                BufferMilliseconds = 100
            };

            _waveIn.DataAvailable += OnDataAvailable;
            _waveIn.RecordingStopped += OnRecordingStopped;

            try
            {
                _waveIn.StartRecording();
                _isRecording = true;
                _logger.LogInformation("Recording started");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to start recording");
                _waveIn.Dispose();
                _waveIn = null;
                throw;
            }
        }
    }

    /// <summary>
    /// Stop recording and return the captured audio samples
    /// </summary>
    /// <returns>Audio samples as float32 array, or null if not enough audio</returns>
    public float[]? StopRecording()
    {
        lock (_lock)
        {
            if (!_isRecording || _waveIn == null)
            {
                _logger.LogWarning("Not recording");
                return null;
            }

            _waveIn.StopRecording();
            _isRecording = false;

            var samples = _buffer.ToArray();
            var duration = samples.Length / (float)_settings.SampleRate;

            _logger.LogInformation("Recording stopped: {Duration:F1}s, {SampleCount} samples",
                duration, samples.Length);

            // Check minimum duration
            if (duration < _settings.MinRecordingSeconds)
            {
                _logger.LogWarning("Recording too short ({Duration:F1}s < {Min}s)",
                    duration, _settings.MinRecordingSeconds);
                return null;
            }

            return samples;
        }
    }

    private void OnDataAvailable(object? sender, WaveInEventArgs e)
    {
        // Convert 16-bit PCM to float32 [-1, 1]
        var sampleCount = e.BytesRecorded / 2;
        var samples = new float[sampleCount];

        for (var i = 0; i < sampleCount; i++)
        {
            var sample = BitConverter.ToInt16(e.Buffer, i * 2);
            samples[i] = sample / 32768f;
        }

        lock (_lock)
        {
            _buffer.AddRange(samples);

            // Safety limit: stop if we exceed max duration
            var duration = _buffer.Count / (float)_settings.SampleRate;
            if (duration > _settings.MaxRecordingSeconds)
            {
                _logger.LogWarning("Max recording duration reached ({Max}s), stopping",
                    _settings.MaxRecordingSeconds);
                _waveIn?.StopRecording();
            }
        }
    }

    private void OnRecordingStopped(object? sender, StoppedEventArgs e)
    {
        if (e.Exception != null)
        {
            _logger.LogError(e.Exception, "Recording stopped with error");
        }

        RecordingStopped?.Invoke(this, new RecordingStoppedEventArgs(e.Exception));
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;

        lock (_lock)
        {
            if (_waveIn != null)
            {
                _waveIn.DataAvailable -= OnDataAvailable;
                _waveIn.RecordingStopped -= OnRecordingStopped;
                _waveIn.Dispose();
                _waveIn = null;
            }
        }
    }
}

public class RecordingStoppedEventArgs : EventArgs
{
    public Exception? Exception { get; }

    public RecordingStoppedEventArgs(Exception? exception = null)
    {
        Exception = exception;
    }
}
