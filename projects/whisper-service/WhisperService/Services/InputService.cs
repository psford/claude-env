using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using InputSimulatorStandard;
using InputSimulatorStandard.Native;
using WhisperService.Models;

namespace WhisperService.Services;

/// <summary>
/// Handles text output via clipboard and simulated keyboard input
/// </summary>
public class InputService
{
    private readonly ILogger<InputService> _logger;
    private readonly OutputSettings _settings;
    private readonly InputSimulator _simulator;

    public InputService(
        ILogger<InputService> logger,
        IOptions<OutputSettings> settings)
    {
        _logger = logger;
        _settings = settings.Value;
        _simulator = new InputSimulator();
    }

    /// <summary>
    /// Output text according to configured mode
    /// </summary>
    public async Task OutputTextAsync(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            _logger.LogWarning("Empty text, nothing to output");
            return;
        }

        _logger.LogInformation("Outputting text ({Length} chars): {Preview}",
            text.Length,
            text.Length > 50 ? text[..50] + "..." : text);

        switch (_settings.Mode.ToLowerInvariant())
        {
            case "pasteandenter":
                await PasteAndEnterAsync(text);
                break;

            case "pasteonly":
                await PasteOnlyAsync(text);
                break;

            case "clipboardonly":
                CopyToClipboard(text);
                break;

            default:
                _logger.LogWarning("Unknown output mode: {Mode}, defaulting to PasteAndEnter",
                    _settings.Mode);
                await PasteAndEnterAsync(text);
                break;
        }
    }

    private async Task PasteAndEnterAsync(string text)
    {
        CopyToClipboard(text);

        await Task.Delay(_settings.ClipboardDelayMs);

        // Simulate Ctrl+V
        _simulator.Keyboard.ModifiedKeyStroke(
            VirtualKeyCode.CONTROL,
            VirtualKeyCode.VK_V);

        await Task.Delay(_settings.EnterDelayMs);

        // Press Enter to submit
        _simulator.Keyboard.KeyPress(VirtualKeyCode.RETURN);

        _logger.LogDebug("Pasted and pressed Enter");
    }

    private async Task PasteOnlyAsync(string text)
    {
        CopyToClipboard(text);

        await Task.Delay(_settings.ClipboardDelayMs);

        // Simulate Ctrl+V
        _simulator.Keyboard.ModifiedKeyStroke(
            VirtualKeyCode.CONTROL,
            VirtualKeyCode.VK_V);

        _logger.LogDebug("Pasted (no Enter)");
    }

    private void CopyToClipboard(string text)
    {
        // Must run on STA thread for clipboard access
        var thread = new Thread(() =>
        {
            System.Windows.Forms.Clipboard.SetText(text);
        });
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        thread.Join();

        _logger.LogDebug("Copied to clipboard");
    }
}
