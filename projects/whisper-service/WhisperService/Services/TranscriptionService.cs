using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Whisper.net;
using WhisperService.Models;

namespace WhisperService.Services;

/// <summary>
/// Handles Whisper model loading and transcription
/// </summary>
public class TranscriptionService : IDisposable
{
    private readonly ILogger<TranscriptionService> _logger;
    private readonly WhisperSettings _settings;
    private WhisperProcessor? _processor;
    private readonly object _lock = new();
    private bool _disposed;

    public TranscriptionService(
        ILogger<TranscriptionService> logger,
        IOptions<WhisperSettings> settings)
    {
        _logger = logger;
        _settings = settings.Value;
    }

    /// <summary>
    /// Ensure the model is loaded. Called lazily on first transcription.
    /// </summary>
    public async Task EnsureModelLoadedAsync()
    {
        if (_processor != null) return;

        lock (_lock)
        {
            if (_processor != null) return;

            var modelPath = GetModelPath();
            if (!File.Exists(modelPath))
            {
                throw new FileNotFoundException(
                    $"Whisper model not found at {modelPath}. " +
                    $"Download the {_settings.ModelSize} model from https://huggingface.co/ggerganov/whisper.cpp/tree/main " +
                    $"and place it in the models folder.",
                    modelPath);
            }

            _logger.LogInformation("Loading Whisper model: {ModelPath}", modelPath);

            try
            {
                var factory = WhisperFactory.FromPath(modelPath);
                _processor = factory.CreateBuilder()
                    .WithLanguage(_settings.Language)
                    .Build();

                _logger.LogInformation("Whisper model loaded successfully");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to load Whisper model. Inner: {Inner}", ex.InnerException?.Message);
                throw new InvalidOperationException($"Failed to load the whisper model: {ex.Message}", ex);
            }
        }

        await Task.CompletedTask;
    }

    /// <summary>
    /// Transcribe audio samples to text
    /// </summary>
    /// <param name="samples">Audio samples (float32, mono, 16kHz)</param>
    /// <returns>Transcribed text</returns>
    public async Task<string> TranscribeAsync(float[] samples)
    {
        await EnsureModelLoadedAsync();

        if (_processor == null)
        {
            throw new InvalidOperationException("Whisper processor not initialized");
        }

        _logger.LogDebug("Transcribing {SampleCount} samples ({Duration:F1}s)",
            samples.Length,
            samples.Length / (float)_settings.SampleRate);

        var segments = new List<string>();

        await foreach (var segment in _processor.ProcessAsync(samples))
        {
            var text = segment.Text.Trim();
            if (!string.IsNullOrWhiteSpace(text))
            {
                segments.Add(text);
            }
        }

        var result = string.Join(" ", segments).Trim();
        _logger.LogInformation("Transcription result: {Text}", result);

        return result;
    }

    /// <summary>
    /// Unload the model to free memory
    /// </summary>
    public void UnloadModel()
    {
        lock (_lock)
        {
            _processor?.Dispose();
            _processor = null;
            _logger.LogInformation("Whisper model unloaded");
        }
    }

    private string GetModelPath()
    {
        var modelDir = _settings.ModelPath;

        // If relative path, make it relative to exe location
        if (!Path.IsPathRooted(modelDir))
        {
            var exeDir = AppContext.BaseDirectory;
            modelDir = Path.Combine(exeDir, modelDir);
        }

        return Path.Combine(modelDir, _settings.GetModelFileName());
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        UnloadModel();
    }
}
