using System.Drawing;
using Microsoft.Extensions.Logging;

namespace WhisperService.Services;

/// <summary>
/// Manages the system tray icon and menu
/// </summary>
public class TrayIconService : IDisposable
{
    private readonly ILogger<TrayIconService> _logger;
    private NotifyIcon? _notifyIcon;
    private bool _disposed;
    private bool _isRecording;

    public event EventHandler? QuitRequested;
    public event EventHandler? SettingsRequested;

    public TrayIconService(ILogger<TrayIconService> logger)
    {
        _logger = logger;
    }

    /// <summary>
    /// Initialize and show the tray icon
    /// </summary>
    public void Initialize()
    {
        _notifyIcon = new NotifyIcon
        {
            Icon = CreateIcon(false),
            Text = "Whisper Dictation - Ready",
            Visible = true,
            ContextMenuStrip = CreateContextMenu()
        };

        _notifyIcon.DoubleClick += (_, _) => SettingsRequested?.Invoke(this, EventArgs.Empty);

        _logger.LogInformation("Tray icon initialized");
    }

    /// <summary>
    /// Update the icon to show recording state
    /// </summary>
    public void SetRecordingState(bool isRecording)
    {
        if (_notifyIcon == null) return;

        _isRecording = isRecording;
        _notifyIcon.Icon = CreateIcon(isRecording);
        _notifyIcon.Text = isRecording
            ? "Whisper Dictation - Recording..."
            : "Whisper Dictation - Ready";
    }

    /// <summary>
    /// Show a balloon notification
    /// </summary>
    public void ShowNotification(string title, string message, ToolTipIcon icon = ToolTipIcon.Info)
    {
        _notifyIcon?.ShowBalloonTip(3000, title, message, icon);
    }

    private ContextMenuStrip CreateContextMenu()
    {
        var menu = new ContextMenuStrip();

        var statusItem = new ToolStripMenuItem("Whisper Dictation")
        {
            Enabled = false
        };
        menu.Items.Add(statusItem);

        menu.Items.Add(new ToolStripSeparator());

        var hotkeyItem = new ToolStripMenuItem("Toggle: F24 (Stream Deck)")
        {
            Enabled = false
        };
        menu.Items.Add(hotkeyItem);

        var holdItem = new ToolStripMenuItem("Hold: Ctrl+Alt+V")
        {
            Enabled = false
        };
        menu.Items.Add(holdItem);

        menu.Items.Add(new ToolStripSeparator());

        var quitItem = new ToolStripMenuItem("Quit");
        quitItem.Click += (_, _) => QuitRequested?.Invoke(this, EventArgs.Empty);
        menu.Items.Add(quitItem);

        return menu;
    }

    private static Icon CreateIcon(bool isRecording)
    {
        var size = 64;
        using var bitmap = new Bitmap(size, size);
        using var graphics = Graphics.FromImage(bitmap);
        graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;

        // Background circle
        var bgColor = isRecording ? Color.FromArgb(255, 51, 51) : Color.FromArgb(33, 150, 243);
        var borderColor = isRecording ? Color.FromArgb(204, 0, 0) : Color.FromArgb(21, 101, 192);

        using var bgBrush = new SolidBrush(bgColor);
        using var borderPen = new Pen(borderColor, 2);
        graphics.FillEllipse(bgBrush, 2, 2, 60, 60);
        graphics.DrawEllipse(borderPen, 2, 2, 60, 60);

        // Microphone icon (simplified)
        using var whiteBrush = new SolidBrush(Color.White);
        using var whitePen = new Pen(Color.White, 3);

        // Mic body (oval)
        graphics.FillEllipse(whiteBrush, 22, 10, 20, 26);

        // Mic stand
        graphics.FillRectangle(whiteBrush, 29, 36, 6, 10);

        // Mic arc
        graphics.DrawArc(whitePen, 18, 28, 28, 24, 0, 180);

        // Base
        graphics.DrawLine(whitePen, 24, 52, 40, 52);
        graphics.DrawLine(whitePen, 32, 46, 32, 52);

        // Convert to icon
        var hIcon = bitmap.GetHicon();
        return Icon.FromHandle(hIcon);
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;

        if (_notifyIcon != null)
        {
            _notifyIcon.Visible = false;
            _notifyIcon.Dispose();
            _notifyIcon = null;
        }
    }
}
