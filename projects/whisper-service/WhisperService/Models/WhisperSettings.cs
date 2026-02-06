namespace WhisperService.Models;

/// <summary>
/// Whisper transcription settings
/// </summary>
public class WhisperSettings
{
    /// <summary>
    /// Path to model files directory (relative to exe or absolute)
    /// </summary>
    public string ModelPath { get; set; } = "models";

    /// <summary>
    /// Model size: tiny, base, small, medium, large
    /// </summary>
    public string ModelSize { get; set; } = "base";

    /// <summary>
    /// Language code for transcription (e.g., "en", "auto")
    /// </summary>
    public string Language { get; set; } = "en";

    /// <summary>
    /// Audio sample rate in Hz (Whisper expects 16000)
    /// </summary>
    public int SampleRate { get; set; } = 16000;

    /// <summary>
    /// Minimum recording duration in seconds
    /// </summary>
    public double MinRecordingSeconds { get; set; } = 0.5;

    /// <summary>
    /// Maximum recording duration in seconds (safety limit)
    /// </summary>
    public double MaxRecordingSeconds { get; set; } = 60;

    /// <summary>
    /// Get the expected model filename for the configured size
    /// </summary>
    public string GetModelFileName() => $"ggml-{ModelSize}.bin";
}

/// <summary>
/// Hotkey configuration
/// </summary>
public class HotkeySettings
{
    /// <summary>
    /// Toggle key for press-to-start/press-to-stop (e.g., "F24" for Stream Deck)
    /// </summary>
    public string ToggleKey { get; set; } = "F24";

    /// <summary>
    /// Modifier keys for hold-to-record mode (e.g., ["Control", "Alt"])
    /// </summary>
    public string[] HoldModifiers { get; set; } = ["Control", "Alt"];

    /// <summary>
    /// Main key for hold-to-record mode (e.g., "V")
    /// </summary>
    public string HoldKey { get; set; } = "V";
}

/// <summary>
/// Output/paste configuration
/// </summary>
public class OutputSettings
{
    /// <summary>
    /// Output mode: PasteAndEnter, PasteOnly, ClipboardOnly
    /// </summary>
    public string Mode { get; set; } = "PasteAndEnter";

    /// <summary>
    /// Delay after clipboard write before pasting (ms)
    /// </summary>
    public int ClipboardDelayMs { get; set; } = 200;

    /// <summary>
    /// Delay after paste before pressing Enter (ms)
    /// </summary>
    public int EnterDelayMs { get; set; } = 100;
}
