import ctypes
import os
import logging

# Define flags for AddFontResourceEx
FR_PRIVATE = 0x10
FR_NOT_ENUM = 0x20

def load_private_font(font_path):
    """
    Loads a .ttf or .otf font into the current process privately using ctypes.
    Returns True if successful, False otherwise.
    """
    if not os.path.exists(font_path):
        logging.warning(f"Font file not found at {font_path}")
        return False
        
    # Convert path to absolute to avoid issues
    abs_path = os.path.abspath(font_path)
    
    try:
        # Load the font
        gdi32 = ctypes.windll.gdi32
        # AddFontResourceExW is the wide string (Unicode) version
        added = gdi32.AddFontResourceExW(abs_path, FR_PRIVATE | FR_NOT_ENUM, 0)
        
        if added > 0:
            logging.info(f"Successfully loaded font: {abs_path}")
            return True
        else:
            logging.warning(f"Failed to load font using AddFontResourceExW: {abs_path}")
            return False
    except Exception as e:
        logging.error(f"Exception while loading font: {e}")
        return False

def unload_private_font(font_path):
    """
    Unloads the privately loaded font to clean up resources.
    """
    if not os.path.exists(font_path):
        return
        
    abs_path = os.path.abspath(font_path)
    try:
        gdi32 = ctypes.windll.gdi32
        gdi32.RemoveFontResourceExW(abs_path, FR_PRIVATE | FR_NOT_ENUM, 0)
    except Exception as e:
        logging.error(f"Exception while unloading font: {e}")
