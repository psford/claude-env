using WhisperService;
using WhisperService.Models;
using WhisperService.Services;

// Required for Windows Forms (tray icon)
Application.SetHighDpiMode(HighDpiMode.SystemAware);
Application.EnableVisualStyles();
Application.SetCompatibleTextRenderingDefault(false);

var builder = Host.CreateApplicationBuilder(args);

// Add Windows Service support
builder.Services.AddWindowsService(options =>
{
    options.ServiceName = "WhisperDictation";
});

// Configuration binding
builder.Services.Configure<WhisperSettings>(
    builder.Configuration.GetSection("Whisper"));
builder.Services.Configure<HotkeySettings>(
    builder.Configuration.GetSection("Hotkeys"));
builder.Services.Configure<OutputSettings>(
    builder.Configuration.GetSection("Output"));

// Register services as singletons (they need to persist across the app lifetime)
builder.Services.AddSingleton<TranscriptionService>();
builder.Services.AddSingleton<AudioCaptureService>();
builder.Services.AddSingleton<InputService>();
builder.Services.AddSingleton<HotkeyService>();
builder.Services.AddSingleton<TrayIconService>();

// The main worker that orchestrates everything
builder.Services.AddHostedService<DictationWorker>();

var host = builder.Build();

// Get services that need main thread initialization
var trayIcon = host.Services.GetRequiredService<TrayIconService>();
var hotkey = host.Services.GetRequiredService<HotkeyService>();
var worker = host.Services.GetServices<IHostedService>()
    .OfType<DictationWorker>()
    .First();

// Create application context that will manage everything on the main thread
var appContext = new TrayApplicationContext(trayIcon, hotkey, worker, host);

// Run the Windows Forms message pump with our context
Application.Run(appContext);

/// <summary>
/// Application context that manages the tray icon and host lifetime
/// </summary>
public class TrayApplicationContext : ApplicationContext
{
    private readonly TrayIconService _trayIcon;
    private readonly HotkeyService _hotkey;
    private readonly IHost _host;

    public TrayApplicationContext(TrayIconService trayIcon, HotkeyService hotkey, DictationWorker worker, IHost host)
    {
        _trayIcon = trayIcon;
        _hotkey = hotkey;
        _host = host;

        // Initialize tray icon on main thread
        _trayIcon.Initialize();
        _trayIcon.QuitRequested += OnQuitRequested;

        // Initialize hotkey service on main thread (requires message pump)
        _hotkey.ToggleRecordingRequested += worker.OnToggleRecording;
        _hotkey.RecordingStartRequested += worker.OnRecordingStartRequested;
        _hotkey.RecordingStopRequested += worker.OnRecordingStopRequested;
        _hotkey.Start();

        _trayIcon.ShowNotification("Whisper Dictation", "Service started. Press F24 or Ctrl+Alt+V to dictate.");

        // Start the host in background
        _ = StartHostAsync();
    }

    private async Task StartHostAsync()
    {
        try
        {
            await _host.RunAsync();
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Host error: {ex.Message}", "Whisper Dictation Error",
                MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            ExitThread();
        }
    }

    private void OnQuitRequested(object? sender, EventArgs e)
    {
        _hotkey.Stop();
        _ = _host.StopAsync();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _hotkey.Dispose();
            _trayIcon.Dispose();
        }
        base.Dispose(disposing);
    }
}
