using System.Runtime.InteropServices;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using WhisperService.Models;

namespace WhisperService.Services;

/// <summary>
/// Handles global hotkey registration and events
/// </summary>
public class HotkeyService : IDisposable
{
    private readonly ILogger<HotkeyService> _logger;
    private readonly HotkeySettings _settings;
    private IntPtr _hookId = IntPtr.Zero;
    private readonly LowLevelKeyboardProc _hookProc;
    private bool _disposed;

    // Track key states for hold mode
    private bool _holdKeyDown;

    public event EventHandler? RecordingStartRequested;
    public event EventHandler? RecordingStopRequested;
    public event EventHandler? ToggleRecordingRequested;

    // Win32 imports
    private delegate IntPtr LowLevelKeyboardProc(int nCode, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    private static extern IntPtr SetWindowsHookEx(int idHook, LowLevelKeyboardProc lpfn, IntPtr hMod, uint dwThreadId);

    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool UnhookWindowsHookEx(IntPtr hhk);

    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    private static extern IntPtr CallNextHookEx(IntPtr hhk, int nCode, IntPtr wParam, IntPtr lParam);

    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    private static extern IntPtr GetModuleHandle(string lpModuleName);

    [DllImport("user32.dll")]
    private static extern short GetAsyncKeyState(int vKey);

    private const int WH_KEYBOARD_LL = 13;
    private const int WM_KEYDOWN = 0x0100;
    private const int WM_KEYUP = 0x0101;
    private const int WM_SYSKEYDOWN = 0x0104;
    private const int WM_SYSKEYUP = 0x0105;

    public HotkeyService(
        ILogger<HotkeyService> logger,
        IOptions<HotkeySettings> settings)
    {
        _logger = logger;
        _settings = settings.Value;
        _hookProc = HookCallback;
    }

    /// <summary>
    /// Start listening for hotkeys
    /// </summary>
    public void Start()
    {
        if (_hookId != IntPtr.Zero)
        {
            _logger.LogWarning("Hotkey hook already installed");
            return;
        }

        using var process = System.Diagnostics.Process.GetCurrentProcess();
        using var module = process.MainModule;

        if (module == null)
        {
            throw new InvalidOperationException("Cannot get main module handle");
        }

        _hookId = SetWindowsHookEx(WH_KEYBOARD_LL, _hookProc, GetModuleHandle(module.ModuleName!), 0);

        if (_hookId == IntPtr.Zero)
        {
            var error = Marshal.GetLastWin32Error();
            throw new InvalidOperationException($"Failed to install keyboard hook. Error: {error}");
        }

        _logger.LogInformation("Hotkey service started. Toggle: {Toggle}, Hold: {Hold}+{Key}",
            _settings.ToggleKey,
            string.Join("+", _settings.HoldModifiers),
            _settings.HoldKey);
    }

    /// <summary>
    /// Stop listening for hotkeys
    /// </summary>
    public void Stop()
    {
        if (_hookId != IntPtr.Zero)
        {
            UnhookWindowsHookEx(_hookId);
            _hookId = IntPtr.Zero;
            _logger.LogInformation("Hotkey service stopped");
        }
    }

    private IntPtr HookCallback(int nCode, IntPtr wParam, IntPtr lParam)
    {
        if (nCode >= 0)
        {
            var vkCode = Marshal.ReadInt32(lParam);
            var keyDown = wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN;
            var keyUp = wParam == WM_KEYUP || wParam == WM_SYSKEYUP;

            // Log all F-key events for debugging
            if (vkCode >= 0x70 && vkCode <= 0x87 && keyDown)
            {
                _logger.LogInformation("F-key detected: vkCode=0x{VkCode:X2} (F{FNum})",
                    vkCode, vkCode - 0x6F);
            }

            // Check for toggle key (F24 for Stream Deck)
            var toggleVk = GetVirtualKeyCode(_settings.ToggleKey);
            if (vkCode == toggleVk && keyDown)
            {
                _logger.LogInformation("Toggle key F24 (0x87) matched! Firing ToggleRecordingRequested...");
                ToggleRecordingRequested?.Invoke(this, EventArgs.Empty);
            }

            // Check for hold mode (Ctrl+Alt+V)
            var holdVk = GetVirtualKeyCode(_settings.HoldKey);
            if (vkCode == holdVk)
            {
                var modifiersPressed = AreModifiersPressed();

                if (keyDown && modifiersPressed && !_holdKeyDown)
                {
                    _holdKeyDown = true;
                    _logger.LogDebug("Hold key pressed with modifiers");
                    RecordingStartRequested?.Invoke(this, EventArgs.Empty);
                }
                else if (keyUp && _holdKeyDown)
                {
                    _holdKeyDown = false;
                    _logger.LogDebug("Hold key released");
                    RecordingStopRequested?.Invoke(this, EventArgs.Empty);
                }
            }
        }

        return CallNextHookEx(_hookId, nCode, wParam, lParam);
    }

    private bool AreModifiersPressed()
    {
        foreach (var modifier in _settings.HoldModifiers)
        {
            var vk = GetModifierVirtualKeyCode(modifier);
            if ((GetAsyncKeyState(vk) & 0x8000) == 0)
            {
                return false;
            }
        }
        return true;
    }

    private static int GetVirtualKeyCode(string keyName)
    {
        return keyName.ToUpperInvariant() switch
        {
            "F1" => 0x70,
            "F2" => 0x71,
            "F3" => 0x72,
            "F4" => 0x73,
            "F5" => 0x74,
            "F6" => 0x75,
            "F7" => 0x76,
            "F8" => 0x77,
            "F9" => 0x78,
            "F10" => 0x79,
            "F11" => 0x7A,
            "F12" => 0x7B,
            "F13" => 0x7C,
            "F14" => 0x7D,
            "F15" => 0x7E,
            "F16" => 0x7F,
            "F17" => 0x80,
            "F18" => 0x81,
            "F19" => 0x82,
            "F20" => 0x83,
            "F21" => 0x84,
            "F22" => 0x85,
            "F23" => 0x86,
            "F24" => 0x87,
            "A" => 0x41,
            "B" => 0x42,
            "C" => 0x43,
            "D" => 0x44,
            "E" => 0x45,
            "F" => 0x46,
            "G" => 0x47,
            "H" => 0x48,
            "I" => 0x49,
            "J" => 0x4A,
            "K" => 0x4B,
            "L" => 0x4C,
            "M" => 0x4D,
            "N" => 0x4E,
            "O" => 0x4F,
            "P" => 0x50,
            "Q" => 0x51,
            "R" => 0x52,
            "S" => 0x53,
            "T" => 0x54,
            "U" => 0x55,
            "V" => 0x56,
            "W" => 0x57,
            "X" => 0x58,
            "Y" => 0x59,
            "Z" => 0x5A,
            _ => 0
        };
    }

    private static int GetModifierVirtualKeyCode(string modifier)
    {
        return modifier.ToUpperInvariant() switch
        {
            "CONTROL" or "CTRL" => 0x11,
            "ALT" or "MENU" => 0x12,
            "SHIFT" => 0x10,
            "WIN" or "LWIN" => 0x5B,
            _ => 0
        };
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        Stop();
    }
}
