import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import logging
import time

def make_rounded_thumbnail(img, size, radius):
    """
    Center-crop, resize to (size, size), and apply rounded corners.
    """
    # Crop to square
    min_dim = min(img.width, img.height)
    left = (img.width - min_dim) / 2
    top = (img.height - min_dim) / 2
    right = (img.width + min_dim) / 2
    bottom = (img.height + min_dim) / 2
    img = img.crop((left, top, right, bottom))
    
    # Resize
    img = img.resize((size, size), Image.LANCZOS)
    
    # Create mask for rounded corners
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
    
    # Apply mask
    img.putalpha(mask)
    return img

class OverlayWindow:
    def __init__(self, root, config, full_image_path, avatar_image_path, dialogue_text, on_timer_set=None):
        self.root = root
        self.config = config
        self.on_timer_set = on_timer_set
        
        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.0)
        
        self.panel_bg = self.config.get('panel_bg', '#141414')
        self.accent_color = self.config.get('accent_color', '#35E0C4')
        self.panel_opacity = self.config.get('panel_opacity', 0.92)
        self.panel_width = self.config.get('panel_width', 280)
        self.font_family = self.config.get('font_family', 'Consolas')
        self.font_size = self.config.get('font_size', 13)
        
        import random
        kickers = [
            "SARE — TOUCH SOME GRASS",
            "SARE — GO OUTSIDE",
            "SARE — STRETCH YOUR LEGS",
            "SARE — HYDRATE",
            "SARE — BLINK YOUR EYES",
            "SARE — REST YOUR EYES",
            "SARE — TIME TO BREATHE"
        ]
        self.kicker_label = random.choice(kickers)
        self.countdown_bar_height = self.config.get('countdown_bar_height', 2)
        self.slide_distance = self.config.get('slide_distance_px', 320)
        self.display_ms = self.config.get('display_seconds', 10) * 1000
        
        # New configs
        self.tick_interval_ms = self.config.get('tick_interval_ms', 50)
        self.avatar_size = self.config.get('avatar_thumbnail_size', 40)
        self.avatar_radius = self.config.get('avatar_thumbnail_radius', 6)
        
        self.window.configure(bg=self.panel_bg)
        
        self.screen_width = self.window.winfo_screenwidth()
        self.screen_height = self.window.winfo_screenheight()
        
        # References for images so they don't get garbage collected
        self.photo_avatar = None
        self.photo_full = None
        
        # Build UI layout
        self.build_ui(full_image_path, avatar_image_path, dialogue_text)
        
        # Update geometry to get actual height after rendering content
        # This naturally expands if Tier 2 full image is present
        self.window.update_idletasks()
        self.panel_height = self.window.winfo_height()
        
        # Calculate dock position
        dock_pos = self.config.get('dock_position', 'right_center')
        margin_x = 20
        margin_y = 20
        
        if dock_pos == 'lower_right':
            self.target_y = self.screen_height - self.panel_height - margin_y - 40 # extra space for taskbar
        else:
            # right_center default
            self.target_y = (self.screen_height - self.panel_height) // 2
            
        self.target_x = self.screen_width - self.panel_width - margin_x
        
        # Starting position for slide-in (offscreen to the right)
        self.current_x = float(self.target_x + self.slide_distance)
        self.current_y = float(self.target_y)
        self.current_alpha = 0.0
        
        self.window.geometry(f"{self.panel_width}x{self.panel_height}+{int(self.current_x)}+{int(self.current_y)}")
        
        # Bind keys for early dismissal
        self.window.bind("<Escape>", lambda e: self.trigger_exit())
        self.window.focus_force()

        # Animation state
        self.is_fading_out = False
        self.anim_job = None
        self.countdown_job = None
        self.start_time = 0
        self.paused_elapsed = 0
        
        # Start entry animation
        self.animate_entry()

    def build_ui(self, full_image_path, avatar_image_path, dialogue_text):
        # Left accent line
        accent_line = tk.Frame(self.window, width=2, bg=self.accent_color)
        accent_line.pack(side="left", fill="y")
        
        # Main content container
        content_frame = tk.Frame(self.window, bg=self.panel_bg, padx=16, pady=16)
        content_frame.pack(side="top", fill="both", expand=True)
        
        # Header (Avatar/Icon + Kicker + Timer Icon)
        header_frame = tk.Frame(content_frame, bg=self.panel_bg)
        header_frame.pack(side="top", fill="x", pady=(0, 10))
        
        # Load avatar if present
        avatar_loaded = False
        if self.config.get('always_show_avatar', True) and avatar_image_path and avatar_image_path.exists():
            try:
                img = Image.open(avatar_image_path)
                img = make_rounded_thumbnail(img, self.avatar_size, self.avatar_radius)
                self.photo_avatar = ImageTk.PhotoImage(img)
                avatar_label = tk.Label(header_frame, image=self.photo_avatar, bg=self.panel_bg)
                avatar_label.pack(side="left")
                avatar_loaded = True
            except Exception as e:
                logging.error(f"Failed to load avatar {avatar_image_path}: {e}")
        
        # Fallback to generic icon if avatar fails or is disabled
        if not avatar_loaded:
            icon_canvas = tk.Canvas(header_frame, width=12, height=12, bg=self.panel_bg, highlightthickness=0)
            icon_canvas.pack(side="left")
            icon_canvas.create_rectangle(2, 2, 10, 10, outline=self.accent_color, width=1)
            icon_canvas.create_rectangle(5, 5, 7, 7, fill=self.accent_color, outline="")
        
        # Wrapper for text so it aligns vertically in the header if we have a larger avatar
        header_text_frame = tk.Frame(header_frame, bg=self.panel_bg)
        header_text_frame.pack(side="left", padx=(8, 0), fill="y")
        
        kicker = tk.Label(
            header_text_frame, 
            text=self.kicker_label.upper(), 
            font=(self.font_family, 9, "bold"), 
            fg="#777777", 
            bg=self.panel_bg
        )
        # Pack kicker vertically centered in its frame
        kicker.pack(side="top", expand=True)
        
        # Timer Icon on right
        self.timer_icon_canvas = tk.Canvas(header_frame, width=16, height=16, bg=self.panel_bg, highlightthickness=0, cursor="hand2")
        self.timer_icon_canvas.pack(side="right", fill="y")
        
        # Vertically center the icon drawing inside the canvas by adjusting coords if needed
        # Or just draw it and let the canvas center visually. We'll draw slightly offset to look centered.
        cy = max(0, (self.avatar_size - 16) // 2) if avatar_loaded else 0
        self.timer_icon_canvas.create_oval(2, 2+cy, 14, 14+cy, outline="#777777", width=1)
        self.timer_icon_canvas.create_line(8, 4+cy, 8, 8+cy, fill="#777777", width=1)
        self.timer_icon_canvas.create_line(8, 8+cy, 11, 10+cy, fill="#777777", width=1)
        
        self.timer_icon_canvas.bind("<Button-1>", self.show_timer_menu)
        
        # Optional Tier 2 Full Image
        # If this exists, the content_frame naturally grows taller!
        if full_image_path and full_image_path.exists():
            try:
                img = Image.open(full_image_path)
                target_img_width = self.panel_width - 32 - 2
                img_ratio = img.width / img.height
                target_img_height = int(target_img_width / img_ratio)
                
                img = img.resize((target_img_width, target_img_height), Image.LANCZOS)
                self.photo_full = ImageTk.PhotoImage(img)
                
                img_label = tk.Label(content_frame, image=self.photo_full, bg=self.panel_bg)
                img_label.pack(side="top", pady=(0, 12))
            except Exception as e:
                logging.error(f"Failed to load full image {full_image_path}: {e}")
        
        # Body Text
        body_text = tk.Message(
            content_frame,
            text=dialogue_text,
            font=(self.font_family, self.font_size),
            fg="#e4e4e4",
            bg=self.panel_bg,
            width=self.panel_width - 34, # Width minus padding
            justify="left"
        )
        body_text.pack(side="top", anchor="w")
        
        # Countdown bar at the bottom
        self.bar_canvas = tk.Canvas(self.window, height=self.countdown_bar_height, bg=self.panel_bg, highlightthickness=0)
        self.bar_canvas.pack(side="bottom", fill="x")
        self.bar_rect = self.bar_canvas.create_rectangle(0, 0, self.panel_width, self.countdown_bar_height, fill=self.accent_color, outline="")

    def resume_countdown(self):
        if not self.is_fading_out and not getattr(self, 'is_dialog_open', False):
            self.start_time = time.time() - (self.paused_elapsed / 1000.0)
            self.tick_countdown()

    def show_timer_menu(self, event):
        if self.countdown_job:
            self.window.after_cancel(self.countdown_job)
            self.countdown_job = None
        
        self.paused_elapsed = (time.time() - self.start_time) * 1000
        
        menu = tk.Menu(self.window, tearoff=0, bg=self.panel_bg, fg="#e4e4e4", activebackground=self.accent_color, activeforeground="black", borderwidth=0)
        menu.add_command(label="15 Minutes", command=lambda: self.set_timer(15))
        menu.add_command(label="30 Minutes", command=lambda: self.set_timer(30))
        menu.add_command(label="1 Hour", command=lambda: self.set_timer(60))
        menu.add_command(label="2 Hours", command=lambda: self.set_timer(120))
        menu.add_command(label="Custom...", command=self.ask_custom_time)
        menu.add_separator()
        menu.add_command(label="Disable Auto-Timer", command=lambda: self.set_timer(0))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
            # Give Tkinter a moment to execute any selected command before resuming
            self.window.after(50, self.resume_countdown)

    def set_timer(self, minutes):
        if self.on_timer_set:
            self.on_timer_set(minutes)

    def ask_custom_time(self):
        self.is_dialog_open = True
        dialog = tk.Toplevel(self.window)
        dialog.overrideredirect(True)
        dialog.attributes("-topmost", True)
        dialog.configure(bg=self.panel_bg)
        
        w, h = 200, 90
        dialog.geometry(f"{w}x{h}+{self.window.winfo_x() - w - 10}+{self.window.winfo_y()}")
        
        frame = tk.Frame(dialog, bg=self.panel_bg, highlightbackground=self.accent_color, highlightthickness=1)
        frame.pack(fill="both", expand=True)
        
        lbl = tk.Label(frame, text="Timer Interval (Minutes):", font=(self.font_family, 9), fg="#e4e4e4", bg=self.panel_bg)
        lbl.pack(pady=(10, 5))
        
        entry = tk.Entry(frame, font=(self.font_family, 10), bg="#222222", fg="#e4e4e4", insertbackground="#e4e4e4", justify="center")
        entry.pack(pady=5, padx=20, fill="x")
        entry.focus_set()
        
        def on_submit(e=None):
            val = entry.get()
            try:
                mins = int(val)
                if mins >= 0:
                    self.set_timer(mins)
            except ValueError:
                pass
            dialog.destroy()
            
        entry.bind("<Return>", on_submit)
        entry.bind("<Escape>", lambda e: dialog.destroy())
        
        self.window.wait_window(dialog)
        self.is_dialog_open = False
        self.resume_countdown()

    def animate_entry(self):
        dist_x = self.target_x - self.current_x
        dist_alpha = self.panel_opacity - self.current_alpha
        
        if abs(dist_x) < 1.0 and abs(dist_alpha) < 0.01:
            self.current_x = self.target_x
            self.current_alpha = self.panel_opacity
            self.update_window_state()
            
            self.start_time = time.time()
            self.tick_countdown()
            return
            
        self.current_x += dist_x * 0.2
        self.current_alpha += dist_alpha * 0.2
        
        self.update_window_state()
        self.anim_job = self.window.after(self.tick_interval_ms, self.animate_entry)

    def trigger_exit(self):
        if self.is_fading_out:
            return
            
        self.is_fading_out = True
        if self.anim_job:
            self.window.after_cancel(self.anim_job)
        if self.countdown_job:
            self.window.after_cancel(self.countdown_job)
            
        self.bar_canvas.coords(self.bar_rect, 0, 0, 0, self.countdown_bar_height)
        
        self.target_x = self.current_x + self.slide_distance
        self.target_alpha = 0.0
        
        self.animate_exit()

    def animate_exit(self):
        dist_x = self.target_x - self.current_x
        dist_alpha = self.target_alpha - self.current_alpha
        
        if abs(dist_x) < 1.0 and abs(dist_alpha) < 0.01:
            self.destroy()
            return
            
        self.current_x += dist_x * 0.2
        self.current_alpha += dist_alpha * 0.2
        
        self.update_window_state()
        self.anim_job = self.window.after(self.tick_interval_ms, self.animate_exit)

    def tick_countdown(self):
        """
        Countdown loop running exactly every `tick_interval_ms`.
        For a default 10-second display (10000ms) with a 50ms tick,
        this will process exactly 200 steps (10000 / 50 = 200). 
        This ensures smooth bar depletion without choking the UI thread.
        """
        if self.is_fading_out:
            return
            
        elapsed_ms = (time.time() - self.start_time) * 1000
        
        if elapsed_ms >= self.display_ms:
            self.trigger_exit()
            return
            
        remaining_ratio = 1.0 - (elapsed_ms / self.display_ms)
        current_bar_width = self.panel_width * remaining_ratio
        
        self.bar_canvas.coords(self.bar_rect, 0, 0, current_bar_width, self.countdown_bar_height)
        
        self.countdown_job = self.window.after(self.tick_interval_ms, self.tick_countdown)

    def update_window_state(self):
        self.window.geometry(f"+{int(self.current_x)}+{int(self.current_y)}")
        self.window.attributes("-alpha", self.current_alpha)

    def destroy(self):
        if self.window:
            if self.anim_job:
                self.window.after_cancel(self.anim_job)
            if self.countdown_job:
                self.window.after_cancel(self.countdown_job)
            self.window.destroy()
            self.window = None
