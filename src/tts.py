import threading
import logging
import pygame

# Suppress Pygame welcome message
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

class TTSWorker:
    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        
        try:
            pygame.mixer.init()
        except Exception as e:
            logging.error(f"Failed to initialize pygame mixer: {e}")

    def _speak_worker(self, audio_file):
        with self.lock:
            try:
                # Ensure previous file is fully unloaded before playing new
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass

                # Load and play the local audio file
                pygame.mixer.music.load(str(audio_file))
                pygame.mixer.music.play()
                
            except Exception as e:
                logging.error(f"Audio Playback Error: {e}")

    def speak(self, audio_file):
        self.stop() # Stop previous before speaking new
        self.thread = threading.Thread(target=self._speak_worker, args=(audio_file,), daemon=True)
        self.thread.start()

    def stop(self):
        # We don't acquire the lock here to allow immediate stopping of playback
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
        except Exception as e:
            pass
