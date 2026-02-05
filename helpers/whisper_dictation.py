"""
Windows Whisper Dictation - System tray app for voice-to-text

Two hotkey modes:
  - Hold mode: Ctrl+Alt+V (hold to record, release to transcribe)
  - Toggle mode: F24 (press to start, press again to stop) - for Stream Deck

Usage:
    1. Run this script (tray icon appears)
    2. Focus on any text input (VS Code, Notepad, browser, etc.)
    3. Either:
       - Hold Ctrl+Alt+V and speak, then release
       - Press F24 to start, speak, press F24 again to stop
    4. Text is transcribed and pasted

Requirements:
    pip install openai-whisper torch sounddevice numpy pystray pillow keyboard pyperclip pyautogui
"""
import whisper
import sounddevice as sd
import numpy as np
import keyboard
import pyperclip
import pyautogui
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw
import threading
import time
import sys

# Configuration
HOLD_HOTKEY_COMBO = ['ctrl', 'alt']  # Modifier keys for hold mode
HOLD_HOTKEY_TRIGGER = 'v'  # Trigger key for hold mode
TOGGLE_HOTKEY = 'f24'  # Single key for toggle mode (Stream Deck)
MODEL_SIZE = 'base'  # tiny, base, small, medium, large
SAMPLE_RATE = 16000
MIN_RECORDING_SECONDS = 0.5

# Global state
model = None
recording = False
audio_frames = []
recording_lock = threading.Lock()
tray_icon = None


def load_model():
    """Load Whisper model on startup."""
    global model
    print(f"Loading Whisper '{MODEL_SIZE}' model...")
    print("(First run will download ~140MB model file)")
    model = whisper.load_model(MODEL_SIZE)
    print("Model loaded. Ready for dictation.")
    print(f"Hold mode: Ctrl+Alt+V (hold to record, release to transcribe)")
    print(f"Toggle mode: F24 (press to start, press to stop) - for Stream Deck")


def create_icon_image(is_recording=False):
    """Create icon for the system tray."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if is_recording:
        # Red recording indicator
        draw.ellipse([8, 8, 56, 56], fill='red', outline='darkred', width=2)
        # White mic silhouette
        draw.ellipse([24, 16, 40, 36], fill='white')
        draw.rectangle([30, 36, 34, 44], fill='white')
    else:
        # Normal microphone icon (white on transparent)
        draw.ellipse([20, 8, 44, 38], fill='white', outline='gray')
        draw.rectangle([28, 38, 36, 48], fill='white')
        draw.arc([16, 28, 48, 56], 0, 180, fill='white', width=3)
        draw.line([32, 56, 32, 60], fill='white', width=3)
        draw.line([22, 60, 42, 60], fill='white', width=3)

    return img


def update_tray_icon():
    """Update tray icon to reflect recording state."""
    global tray_icon
    if tray_icon:
        tray_icon.icon = create_icon_image(recording)


def audio_callback(indata, frames, time_info, status):
    """Callback for audio recording."""
    global audio_frames
    if recording:
        audio_frames.append(indata.copy())


def start_recording():
    """Start recording audio from microphone."""
    global recording, audio_frames

    with recording_lock:
        if recording:
            return False
        recording = True
        audio_frames = []

    print("Recording... (press F24 or release Ctrl+Alt+V to stop)")
    update_tray_icon()
    return True


def stop_recording_and_transcribe():
    """Stop recording and transcribe the audio."""
    global recording, audio_frames

    with recording_lock:
        if not recording:
            return
        recording = False
        frames_to_process = audio_frames.copy()
        audio_frames = []

    update_tray_icon()

    if not frames_to_process:
        print("No audio recorded.")
        return

    # Combine all frames
    audio = np.concatenate(frames_to_process, axis=0).flatten()

    # Check minimum duration
    duration = len(audio) / SAMPLE_RATE
    if duration < MIN_RECORDING_SECONDS:
        print(f"Recording too short ({duration:.1f}s < {MIN_RECORDING_SECONDS}s)")
        return

    print(f"Transcribing {duration:.1f}s of audio...")

    # Normalize audio to float32 range [-1, 1]
    audio = audio.astype(np.float32)
    max_val = np.abs(audio).max()
    if max_val > 0:
        audio = audio / max_val

    # Transcribe
    try:
        result = model.transcribe(audio, language='en', fp16=False)
        text = result['text'].strip()

        if text:
            print(f"Transcribed: {text}")
            # Copy to clipboard
            pyperclip.copy(text)
            # Small delay to ensure clipboard is ready and keys are released
            time.sleep(0.2)
            # Simulate Ctrl+V to paste using pyautogui (works across apps)
            pyautogui.hotkey('ctrl', 'v')
        else:
            print("No speech detected.")
    except Exception as e:
        print(f"Transcription error: {e}")


def toggle_recording():
    """Toggle recording on/off (for Stream Deck F24 key)."""
    global recording

    if recording:
        # Stop and transcribe
        threading.Thread(target=stop_recording_and_transcribe, daemon=True).start()
    else:
        # Start recording
        start_recording()


def on_key_event(event):
    """Handle keyboard events for hotkeys."""
    global recording

    # Toggle mode: F24 (for Stream Deck)
    if event.name == TOGGLE_HOTKEY and event.event_type == 'down':
        toggle_recording()
        return

    # Hold mode: Ctrl+Alt+V
    modifiers_pressed = all(keyboard.is_pressed(key) for key in HOLD_HOTKEY_COMBO)

    if event.name == HOLD_HOTKEY_TRIGGER:
        if event.event_type == 'down' and modifiers_pressed and not recording:
            start_recording()
        elif event.event_type == 'up' and recording:
            # Only stop if we're in hold mode (modifiers were used to start)
            threading.Thread(target=stop_recording_and_transcribe, daemon=True).start()


def run_tray_icon():
    """Run the system tray icon."""
    global tray_icon

    menu = Menu(
        MenuItem('Whisper Dictation', lambda: None, enabled=False),
        MenuItem(f'Hold: Ctrl+Alt+V', lambda: None, enabled=False),
        MenuItem(f'Toggle: F24 (Stream Deck)', lambda: None, enabled=False),
        MenuItem(f'Model: {MODEL_SIZE}', lambda: None, enabled=False),
        Menu.SEPARATOR,
        MenuItem('Quit', lambda icon, item: (icon.stop(), sys.exit(0)))
    )

    tray_icon = Icon('whisper_dictation', create_icon_image(), 'Whisper Dictation', menu)
    tray_icon.run()


def main():
    """Main entry point."""
    print("=" * 50)
    print("Whisper Dictation for Windows")
    print("=" * 50)

    # Load the model
    load_model()

    # Start audio stream (always running, but only saves when recording=True)
    print("Starting audio stream...")
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32',
        callback=audio_callback
    )
    stream.start()

    # Register keyboard hook
    print("Registering hotkeys...")
    keyboard.hook(on_key_event)

    # Run system tray icon (this blocks)
    print("Starting system tray icon...")
    print("-" * 50)
    run_tray_icon()

    # Cleanup
    stream.stop()
    stream.close()


if __name__ == '__main__':
    main()
