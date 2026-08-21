# JARVIS-Style Break Reminder — Architecture

## Overview
A Windows desktop utility that runs quietly in the background and, on a global
hotkey press (or timer), displays a fading HUD-style overlay with a random
image, a random line of dialogue rendered in a retro pixel font, and
text-to-speech narration — then auto-dismisses after a set duration.

## Tech Stack

| Concern            | Library      | Notes |
|---------------------|-------------|-------|
| UI / Overlay        | `tkinter`   | Borderless, transparent, topmost window |
| Text-to-Speech      | `pyttsx3`   | Runs in a daemon thread to avoid blocking the UI |
| Image processing    | `Pillow`    | Resize + aspect-ratio-preserving fit |
| Global hotkeys      | `keyboard`  | Background listener thread |
| Custom fonts        | `ctypes`    | Loads `.ttf` into Windows memory (no install) |
| System tray         | `pystray`   | Background control surface (planned) |
| Config              | `json`      | User-editable settings file |

## Process Model

```
main.py (entry point)
 ├── tray icon thread (pystray)         — Trigger Now / Pause / Settings / Quit
 ├── hotkey listener thread (keyboard)  — global hotkey → trigger event
 ├── tkinter mainloop (main thread)     — owns the overlay window lifecycle
 └── TTS worker thread (pyttsx3)        — spawned per-trigger, daemon
```

Only ONE overlay instance may exist at a time. A trigger event while an
overlay is active is either ignored or resets its display timer, depending
on config (`retrigger_behavior: "ignore" | "reset_timer"`).

## Module Breakdown

### `main.py`
- Loads `config.json`
- Registers global hotkey via `keyboard.add_hotkey(...)`
- Starts tray icon (`pystray.Icon`) with menu callbacks
- Owns the tkinter root and mainloop
- Routes trigger events (hotkey, tray "Trigger Now", or future auto-timer)
  into a thread-safe queue that the mainloop polls

### `overlay.py` — `OverlayWindow` class
- Constructs borderless `tk.Toplevel`/`Tk` window:
  - `overrideredirect(True)`
  - `attributes("-topmost", True)`
  - `attributes("-alpha", 0.0)` initial state
- Positions top-right based on `winfo_screenwidth()` (window width = 1/8 of
  screen width, aspect-locked height)
- Fade animation: `after()`-scheduled alpha steps (0 → 0.85 on show,
  0.85 → 0 on hide) — non-blocking, mainloop-driven
- Renders:
  - `PIL.ImageTk.PhotoImage` for the selected/resized image
  - `tk.Label` or `tk.Canvas.create_text` using the loaded pixel font
- Binds `<Escape>` (while focused) or a secondary hotkey to trigger early
  fade-out
- `after(10000, self.begin_fade_out)` for auto-close

### `content.py`
- `pick_image(history: list) -> Path`
- `pick_dialogue(history: list) -> str`
- Maintains a rolling "recently shown" deque (length N, configurable) per
  content type to avoid immediate repeats
- Reads from `images/` and `dialogues/` at call time (or caches directory
  listing with a refresh check, if folders are large)

### `tts.py`
- Wraps `pyttsx3.init()` in a class that:
  - Runs `.say()` / `.runAndWait()` inside a daemon `Thread`
  - Exposes `speak(text)` and `stop()` (stop cancels in-flight speech if
    retriggered)
  - Guards against overlapping engine instances (pyttsx3 is not always
    thread-safe for concurrent `runAndWait` calls — serialize via a lock or
    single worker thread + queue)

### `fonts.py`
- `load_private_font(path: Path) -> bool`
  - Uses `ctypes.windll.gdi32.AddFontResourceExW` with
    `FR_PRIVATE | FR_NOT_ENUM` so the font is available to the process only,
    not installed system-wide, and cleaned up on exit
  - Fallback: if load fails, log a warning and fall back to a bundled
    system font (e.g. "Consolas") so the UI never breaks

### `config.json` (example)
```json
{
  "hotkey": "win+ctrl+r",
  "dismiss_key": "esc",
  "display_seconds": 10,
  "fade_step_ms": 20,
  "max_opacity": 0.85,
  "window_width_ratio": 0.125,
  "aspect_ratio": [16, 9],
  "no_repeat_history": 3,
  "images_dir": "images/",
  "dialogues_dir": "dialogues/",
  "font_path": "fonts/pixel.ttf",
  "retrigger_behavior": "ignore"
}
```

## Data Flow (single trigger)

```
Hotkey pressed
   │
   ▼
main.py enqueues "trigger" event
   │
   ▼
tkinter mainloop picks up event (via after()-polling of a thread-safe Queue)
   │
   ▼
OverlayWindow created
   │
   ├── content.pick_image()      → PIL resize → PhotoImage
   ├── content.pick_dialogue()   → rendered with pixel font
   └── tts.speak(dialogue)       → daemon thread, non-blocking
   │
   ▼
Fade in (0 → 0.85) → hold 10s → fade out (0.85 → 0) → destroy()
```

## Threading Rules (important)
- **Only the main thread touches tkinter widgets.** The `keyboard` hotkey
  callback and `pyttsx3` both run on separate threads — they must never call
  into tkinter directly. Use a `queue.Queue` + `root.after(50, poll_queue)`
  pattern to marshal events onto the main thread safely.
- TTS thread is fire-and-forget per trigger, but should be cancellable
  (`engine.stop()`) if a new trigger interrupts an old one.

## Planned / Suggested Extensions
- Passive auto-trigger based on idle/active time tracking
- Time-of-day or context-based dialogue folder selection
- Weighted rarity for "easter egg" content
- Draggable overlay with remembered position
- Startup registration (registry / startup folder)
- Sound cue (`winsound`) preceding TTS playback
- Typewriter-style text reveal synced to speech

## Known Constraints
- Windows-only (relies on `ctypes` Win32 font APIs; `keyboard` also needs
  admin rights for global hooks in some environments)
- `pyttsx3` voice quality/availability depends on installed Windows SAPI5
  voices
- Single-overlay-at-a-time model; no queueing of multiple overlays
