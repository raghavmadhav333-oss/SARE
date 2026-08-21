import tkinter as tk
import keyboard
import pystray
from PIL import Image
import threading
import queue
import json
import sys
import logging
from pathlib import Path

from overlay import OverlayWindow
from content import ContentManager
from tts import TTSWorker
from fonts import load_private_font, unload_private_font

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class App:
    def __init__(self):
        self.load_config()
        self.root = tk.Tk()
        self.root.withdraw() # Hide main window
        
        self.content = ContentManager(
            self.config.get('images_dir', 'images/'),
            self.config.get('dialogues_dir', 'dialogues/'),
            self.config.get('no_repeat_history', 3)
        )
        self.tts = TTSWorker()
        
        self.font_path = self.config.get('font_path', 'fonts/pixel.ttf')
        self.font_loaded = load_private_font(self.font_path)
        
        self.event_queue = queue.Queue()
        self.current_overlay = None
        
        self.setup_hotkey()
        self.setup_tray()
        
        # Initialize auto-timer on boot if configured
        import time
        mins = self.config.get('auto_timer_minutes', 30)
        
        # Immediate one-time reminder on start
        self.event_queue.put("trigger")
        
        if mins > 0:
            self.auto_timer_next = time.time() + (mins * 60)
            logging.info(f"Auto-timer started on boot for {mins} minutes.")
        else:
            self.auto_timer_next = 0
            
        # Start queue polling
        self.root.after(50, self.poll_queue)

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config, using defaults: {e}")
            self.config = {
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
                "retrigger_behavior": "ignore"
            }

    def setup_hotkey(self):
        hotkey = self.config.get('hotkey', 'win+ctrl+r')
        try:
            keyboard.add_hotkey(hotkey, self.on_hotkey)
            logging.info(f"Registered hotkey: {hotkey}")
        except Exception as e:
            logging.error(f"Failed to register hotkey: {e}")

    def on_hotkey(self):
        # Called from background thread, marshal to main thread
        self.event_queue.put("trigger")

    def poll_queue(self):
        import time
        try:
            try:
                while not self.event_queue.empty():
                    msg = self.event_queue.get_nowait()
                    if msg == "trigger":
                        self.trigger_overlay()
                    elif msg == "quit":
                        self.quit_app()
            except queue.Empty:
                pass
                
            # Check auto timer
            if getattr(self, 'auto_timer_next', 0) > 0 and time.time() >= self.auto_timer_next:
                mins = self.config.get('auto_timer_minutes', 0)
                if mins > 0:
                    self.auto_timer_next = time.time() + (mins * 60)
                    self.trigger_overlay()
        except Exception as e:
            logging.error(f"Error in poll_queue: {e}")
        finally:
            self.root.after(50, self.poll_queue)

    def handle_timer_set(self, minutes):
        import time
        if minutes <= 0:
            self.config['auto_timer_minutes'] = 0
            self.auto_timer_next = 0
            logging.info("Auto-timer disabled.")
        else:
            self.config['auto_timer_minutes'] = minutes
            self.auto_timer_next = time.time() + (minutes * 60)
            logging.info(f"Auto-timer set for {minutes} minutes.")

    def trigger_overlay(self):
        retrigger = self.config.get('retrigger_behavior', 'ignore')
        
        if self.current_overlay and self.current_overlay.window:
            if retrigger == 'ignore':
                return
            else:
                self.current_overlay.destroy()
                
        full_image = self.content.pick_image(self.config.get('full_image_chance', 0.2))
        avatar_image = self.content.pick_avatar_thumbnail_source()
        audio_file, dialogue_text = self.content.pick_dialogue()
        
        # Reset the auto-timer so a manual trigger delays the next automatic loop
        mins = self.config.get('auto_timer_minutes', 0)
        import time
        if mins > 0:
            self.auto_timer_next = time.time() + (mins * 60)
            
        # Start Audio Playback
        if audio_file:
            self.tts.speak(audio_file)
        
        # Show overlay
        self.current_overlay = OverlayWindow(
            self.root, 
            self.config, 
            full_image,
            avatar_image,
            dialogue_text, 
            on_timer_set=self.handle_timer_set
        )

    def setup_tray(self):
        def on_trigger(icon, item):
            self.event_queue.put("trigger")
            
        def on_quit(icon, item):
            self.event_queue.put("quit")
            
        # Create a simple icon
        icon_image = Image.new('RGB', (64, 64), color = (0, 255, 204))
        menu = pystray.Menu(
            pystray.MenuItem('Trigger Now', on_trigger),
            pystray.MenuItem('Quit', on_quit)
        )
        self.tray = pystray.Icon("break_reminder", icon_image, "JARVIS Reminder", menu)
        
        # Start tray in background thread
        threading.Thread(target=self.tray.run, daemon=True).start()

    def quit_app(self):
        logging.info("Shutting down...")
        self.tray.stop()
        self.tts.stop()
        keyboard.unhook_all()
        if self.font_loaded:
            unload_private_font(self.font_path)
        if self.current_overlay:
            self.current_overlay.destroy()
        self.root.quit()
        sys.exit(0)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    import ctypes
    
    # Prevent multiple instances from running at the same time
    mutex_name = "Global\\SARE_Break_Reminder_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        logging.error("SARE is already running! Check your system tray. Exiting this instance.")
        sys.exit(0)
        
    app = App()
    app.run()
