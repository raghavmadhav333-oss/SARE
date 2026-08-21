import os
import random
import logging
from collections import deque
from pathlib import Path

# Dictionary to format raw filenames into perfect subtitles
DIALOGUE_MAP = {
    "DOES YOUR MOTHER KNOW": "Doth mother know you weareth her drapes?",
    "GENIUS BILLIONARE PLAYBOY PHILANTHROPHIST": "Genius, billionaire, playboy, philanthropist.",
    "I DON'T PAINT": "I don't paint.",
    "I M DONATING YOU TO CITY COLLEGE": "I'm donating you to City College.",
    "I M IRON MAN": "I am Iron Man.",
    "IS IT TOO MUCH TO ASK FOR BOTH": "Is it too much to ask for both?",
    "LEAVE IT URGENT": "Leave it. Urgent.",
    "SIR LEAVE THAT DONUT": "Sir, leave that donut.",
    "SOMETIMES YOU GOTA RUN": "Sometimes you gotta run before you can walk.",
    "THIS IS NOT THE WORST THING YOU HAVE CAUGHT ME DOING": "Admit it, this isn't the worst thing you've caught me doing.",
    "WE HAVE A HULK": "We have a Hulk.",
    "WHEN DID YOU BECOME AN EXPERT": "When did you become an expert in thermonuclear astrophysics?"
}

class ContentManager:
    def __init__(self, images_dir, dialogues_dir, no_repeat_history=3):
        self.images_dir = Path(images_dir)
        self.dialogues_dir = Path(dialogues_dir)
        self.no_repeat_history = no_repeat_history
        
        self.image_history = deque(maxlen=no_repeat_history)
        self.dialogue_history = deque(maxlen=no_repeat_history)

    def get_all_images(self):
        if not self.images_dir.exists():
            return []
        
        valid_exts = {'.png', '.jpg', '.jpeg', '.gif', '.jfif'}
        images = []
        for file in self.images_dir.iterdir():
            if file.is_file() and file.suffix.lower() in valid_exts:
                images.append(file)
        return images

    def get_all_audio_files(self):
        if not self.dialogues_dir.exists():
            return []
            
        audio_files = []
        for file in self.dialogues_dir.iterdir():
            if file.is_file() and file.suffix.lower() == '.mp3':
                audio_files.append(file)
        return audio_files

    def pick_image(self, chance=1.0):
        if random.random() > chance:
            return None
            
        images = self.get_all_images()
        if not images:
            return None
            
        available = [img for img in images if img not in self.image_history]
        if not available:
            available = images
            
        choice = random.choice(available)
        self.image_history.append(choice)
        return choice

    def pick_avatar_thumbnail_source(self):
        """Picks a source image for the thumbnail avatar (100% chance, respecting history)."""
        return self.pick_image(chance=1.0)

    def pick_dialogue(self):
        """Returns a tuple of (audio_file_path, dialogue_text)"""
        audio_files = self.get_all_audio_files()
        if not audio_files:
            return (None, "System ready.")
            
        available = [f for f in audio_files if f not in self.dialogue_history]
        if not available:
            available = audio_files
            
        choice = random.choice(available)
        self.dialogue_history.append(choice)
        
        # Get perfectly formatted text based on filename
        base_name = choice.stem
        formatted_text = DIALOGUE_MAP.get(base_name, base_name.replace("_", " ").title())
        
        return (choice, formatted_text)
