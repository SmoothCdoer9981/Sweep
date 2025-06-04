import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import time
import shutil
import os
import asyncio
import platform
import datetime # For TimeSpan conversion
import json
from tkinter import filedialog, messagebox
import requests
import webbrowser # Import webbrowser for opening search URLs

# Add pystray and PIL imports
try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    print("pystray or PIL not available. System tray icon will not be shown.")

# --- Conditional Import for Windows Media Control ---
if platform.system() == "Windows":
    try:
        import winrt.windows.media.control as wmc 
        
        # We will NOT import MediaPlaybackStatus directly due to previous errors.
        # Instead, we define the expected integer values for the enum states.
        # These values are standard for Windows.Media.MediaPlaybackStatus.
        PLAYBACK_STATUS_PLAYING = 4  
        PLAYBACK_STATUS_PAUSED = 5   
        
        WINDOWS_MEDIA_CONTROL_AVAILABLE = True
        print("DEBUG: winrt.windows.media.control imported successfully. Using integer values for MediaPlaybackStatus.")
    except (ImportError, ModuleNotFoundError) as e:
        print(f"DEBUG: winrt-Windows.media.Control not found or incompatible. Error: {e}. Media control will be manual.")
        WINDOWS_MEDIA_CONTROL_AVAILABLE = False
else:
    WINDOWS_MEDIA_CONTROL_AVAILABLE = False
    print("DEBUG: Not on Windows. Media control will be manual.")

# --- ANIMATION FRAMES ---
idle_frames = [
    r"""
 /\_/\  
( o.o ) 
 > ^ <  
 /   \  
(     ) 
    """,
    r"""
 /\_/\  
( ^.^ ) 
 > ^ <  
 /   \  
(     ) 
    """,
    r"""
 /\_/\  
( o.o ) 
 > ^ <  
 /   \  
(   ) ) 
    """,
    r"""
 /\_/\  
( ^.^ ) 
 > ^ <  
 /   \  
( (   ) 
    """,
]

hover_frames = [
    r"""
 /\_/\  
( 'o' ) 
 > ^ <  
 /   \  
(     ) 
    """,
    r"""
 /\_/\  
( 'O' ) 
 > ^ <  
 /   \  
(     ) 
    """,
]

eating_frames = [
    r"""
 /\_/\  
( 'o' ) 
 > ^ <  
/  ~  \ 
( === )
    """, 
    r"""
 /\_/\  
( 'O' ) 
 >   <  
/  ~  \ 
( === )
    """, 
    r"""
 /\_/\  
( 'o' ) 
 >   <  
/  ~  \ 
( === )
    """, 
    r"""
 /\_/\  
(  -  ) 
 > ^ <  
/  ~  \ 
( === )
    """, 
    r"""
 /\_/\  
( ^.^ ) 
 > ^ <  
/  ~  \ 
( === )
    """, 
    r"""
 /\_/\  
( o.o ) 
 > ^ <  
 /   \  
(     ) 
    """, 
]

# Modified music_frames to include " ZZZ"
music_frames = [
    r"""
     Z
  /\_/\
 ( -.- )_
 /       \
(_________)

    """, 
    r"""
    Zz
  /\_/\
 ( -.- )_
 /       \
(_________)

    """, 
    r"""
   Zzz
  /\_/\
 ( -.- )_
 /       \
(_________)

    """, 
    r"""
    Zz
  /\_/\
 ( -.- )_
 /       \
(_________)

    """, 
]


ascii_progress_bar_states = [
    "[          ]", # 0%
    "[=         ]", # 10%
    "[==        ]", # 20%
    "[===       ]", # 30%
    "[====      ]", # 40%
    "[=====     ]", # 50%
    "[======    ]", # 60%
    "[=======   ]", # 70%
    "[========  ]", # 80%
    "[========= ]", # 90%
    "[==========]", # 100%
]

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
CHUNK_SIZE = 65536  

APP_VERSION = "0.3"
# Use the raw URL for the main branch (not refs/heads)
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/SmoothCdoer9981/Sweep/main/version.txt"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

def check_for_update():
    try:
        resp = requests.get(GITHUB_VERSION_URL, timeout=5)
        if resp.status_code == 200:
            latest = resp.text.strip()
            if latest != APP_VERSION:
                messagebox.showinfo("Update Available", f"A new version ({latest}) is available on GitHub!")
    except Exception as e:
        print(f"Update check failed: {e}")

class CTkAppWithDnD(TkinterDnD.DnDWrapper, ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkDnDVersion = TkinterDnD._require(self)


class SettingsWindow(ctk.CTkToplevel): 
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.title("Sweep Settings")
        self.geometry("400x600") # Adjusted height for new search engine option
        self.transient(master) # Make it appear on top of the main window
        self.grab_set() # Make it modal
        self.resizable(False, False) # Prevent resizing
        
        self.app = app_instance
        self.config = self.app.config.copy() # Work with a copy of the config

        self.create_widgets()

    def create_widgets(self):
        # Create a main frame to contain all widgets for consistent padding/layout
        main_frame = ctk.CTkFrame(self, fg_color="transparent") # This frame itself can be transparent
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)


        # --- ASCII Header ---
        ctk.CTkLabel(main_frame, text="""
==============================
      S W E E P  S E T T I N G S
==============================
""", font=("Consolas", 14), justify="center").pack(pady=(0, 10)) # Adjusted pady

        # --- Destination Path Setting ---
        ctk.CTkLabel(main_frame, text="Network Share Path:", font=("Consolas", 12)).pack(pady=(5,0))
        self.path_entry = ctk.CTkEntry(main_frame, width=300, font=("Consolas", 12))
        self.path_entry.insert(0, self.config.get("network_share_path", ""))
        self.path_entry.pack(pady=2)
        ctk.CTkButton(main_frame, text="Browse", command=self.browse_path, font=("Consolas", 12)).pack(pady=2)

        ctk.CTkLabel(main_frame, text="------------------------------", font=("Consolas", 10)).pack(pady=10) # Separator
        
        # --- Search Engine Setting ---
        ctk.CTkLabel(main_frame, text="Default Search Engine:", font=("Consolas", 12)).pack(pady=(5,0))
        self.search_engine_options = ["Google", "Bing", "DuckDuckGo"] 
        self.search_engine_combobox = ctk.CTkComboBox(main_frame, values=self.search_engine_options, font=("Consolas", 12))
        current_search_engine = self.config.get("search_engine", "Google")
        if current_search_engine in self.search_engine_options:
            self.search_engine_combobox.set(current_search_engine)
        else:
            self.search_engine_combobox.set("Google") # Default if current is not in options
        self.search_engine_combobox.pack(pady=2)

        ctk.CTkLabel(main_frame, text="------------------------------", font=("Consolas", 10)).pack(pady=10) # Separator

        # --- Always on Top Setting ---
        self.always_on_top_var = ctk.BooleanVar(value=self.config.get("always_on_top", True))
        ctk.CTkCheckBox(main_frame, text="Always on Top", variable=self.always_on_top_var, font=("Consolas", 12)).pack(pady=5)

        ctk.CTkLabel(main_frame, text="==============================", font=("Consolas", 14)).pack(pady=10) # Separator

        # --- Save, Apply and Cancel Buttons ---
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=10)

        ctk.CTkButton(button_frame, text="Save", command=self.save_and_close, font=("Consolas", 12)).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Apply", command=self.apply_settings, font=("Consolas", 12)).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", command=self.destroy, font=("Consolas", 12)).pack(side="right", padx=5)

    def browse_path(self):
        path = filedialog.askdirectory(title="Select Network Share Folder")
        if path:
            self.path_entry.delete(0, ctk.END)
            self.path_entry.insert(0, path)

    def apply_settings(self):
        self.config["network_share_path"] = self.path_entry.get()
        self.config["search_engine"] = self.search_engine_combobox.get() # Save search engine setting
        self.config["always_on_top"] = self.always_on_top_var.get()

        # Update the main app's config (but don't save to file yet)
        self.app.config.update(self.config)
        
        # Apply always on top immediately
        self.app.wm_attributes("-topmost", self.app.config["always_on_top"])

        messagebox.showinfo("Settings Applied", "Settings have been applied!")

    def save_and_close(self):
        self.apply_settings() # First apply the settings
        save_config(self.app.config) # Then save to file
        messagebox.showinfo("Settings Saved", "Settings have been saved successfully! Some changes may require a restart.")
        self.destroy() # Close the settings window


class DesktopPet(CTkAppWithDnD):
    def __init__(self):
        super().__init__()

        self.config = load_config() # Load all config at startup

        # Apply initial settings from config
        ctk.set_appearance_mode("dark") # This is usually set once globally
        self.wm_attributes("-topmost", self.config.get("always_on_top", True)) # Default to True

        self.overrideredirect(True)
        self.geometry("150x330+100+100") # Adjusted height for new search bar
        self.configure(bg="transparent") 

        # --- Top Bar Frame ---
        self.top_bar_frame = ctk.CTkFrame(self, fg_color="transparent") # Use transparent to respect theme
        self.top_bar_frame.pack(fill="x", pady=(5,0))

        self.title_label = ctk.CTkLabel(
            self.top_bar_frame,
            text="Sweep",
            font=("Consolas", 20, "bold"),
            height=30
        )
        self.title_label.pack(side="left", padx=(5,0))

        self.settings_button = ctk.CTkButton(
            self.top_bar_frame,
            text="⚙️",
            font=("Consolas", 14),
            width=30,
            height=30,
            command=self._on_tray_settings
        )
        self.settings_button.pack(side="right", padx=(0,5))


        self.frame_index = 0
        self.is_eating = False
        self.is_hovering_file = False
        self.eating_message_display_time = 0
        self.current_frames = idle_frames
        self.current_progress_text = "" # For file upload progress
        self.current_upload_progress = 0.0
        self.last_eating_frame = eating_frames[-2] 

        # Music related flags and info
        self.is_music_playing_system = False 
        self.is_music_playing_override = False # True if manual toggle is on (only fallback if winrt unavailable)
        self.current_track_info = "" 

        self.system_media_session = None 

        # Scrolling text variables
        self.max_song_display_width = 25 # Max chars to display on one line for song info
        self.song_scroll_offset = 0
        self.song_scroll_speed = 1 # Chars per scroll step
        self.song_scroll_pause_frames = 10 # Frames to wait at start/end before scrolling again
        self.song_scroll_direction = 1 # 1 for left, -1 for right
        self.song_scroll_counter = 0 # Counter for scrolling pause

        self.animation_state_lock = threading.Lock() 

        self.label = ctk.CTkLabel(
            self,
            text=self.current_frames[0],
            font=("Consolas", 16),
            justify="left"
        )
        self.label.pack(padx=5, pady=5, fill="both", expand=True)
        
        # --- Music Control and Info Frame ---
        self.music_control_frame = ctk.CTkFrame(self, fg_color="transparent") 
        
        # Song Title Label (for scrolling text)
        self.track_title_label = ctk.CTkLabel(
            self.music_control_frame,
            text="",
            font=("Consolas", 12),
            fg_color="transparent", 
            justify="center",
            width=self.max_song_display_width * 8 
        )
        self.track_title_label.pack(pady=(2,5), fill="x") 

        # Multimedia Control Buttons
        self.prev_button = ctk.CTkButton(self.music_control_frame, text="⏮️", command=self.skip_prev, width=40, height=25, fg_color="transparent", hover_color="gray", 
font=("Consolas", 14))
        self.prev_button.pack(side="left", padx=5, expand=True) 

        self.play_pause_button = ctk.CTkButton(self.music_control_frame, text="▶️", command=self.toggle_play_pause, width=40, height=25, fg_color="transparent", hover_color="gray", 
font=("Consolas", 14))
        self.play_pause_button.pack(side="left", padx=5, expand=True)

        self.skip_button = ctk.CTkButton(self.music_control_frame, text="⏭️", command=self.skip_next, width=40, height=25, fg_color="transparent", hover_color="gray", 
font=("Consolas", 14))
        self.skip_button.pack(side="left", padx=5, expand=True)

        self.music_control_frame.pack_forget() # Initially hidden

        # --- Search Bar and Button ---
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Search...",
            width=120,
            font=("Consolas", 12)
        )
        self.search_entry.pack(side="left", padx=(5,2), pady=5, fill="x", expand=True)
        
        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="🔎",
            command=self.perform_search,
            width=30,
            height=25,
            font=("Consolas", 14)
        )
        self.search_button.pack(side="right", padx=(2,5), pady=5)
        
        # self.search_frame.pack(fill="x") # Always visible - REMOVE OR COMMENT OUT THIS LINE
        self.search_frame.pack_forget() # Initially hidden

        # Main window bindings
        # Bind the top bar frame for dragging
        self.top_bar_frame.bind("<ButtonPress-1>", self.start_move)
        self.top_bar_frame.bind("<B1-Motion>", self.do_move)
        self.title_label.bind("<ButtonPress-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)
        self.settings_button.bind("<ButtonPress-1>", lambda e: "break") # Prevent dragging when clicking settings button

        self.label.drop_target_register(DND_FILES)
        self.label.dnd_bind('<<Drop>>', self.handle_drop)
        self.label.dnd_bind('<<DropEnter>>', self.on_file_enter)
        self.label.dnd_bind('<<DropLeave>>', self.on_file_leave)

        # NEW: Bind double-click to toggle search bar
        self.label.bind("<Double-Button-1>", self._toggle_search_bar)
        
        # Start animation thread
        self.animate_thread = threading.Thread(target=self.animate, daemon=True)
        self.animate_thread.start()

        # Start media status checker thread if on Windows
        if WINDOWS_MEDIA_CONTROL_AVAILABLE:
            self.media_status_thread = threading.Thread(target=self.run_async_loop_for_media_check, daemon=True)
            self.media_status_thread.start()
        else:
            print("Windows Media Control not available. Music mode will rely on manual toggle (via play/pause button).")

        # System tray icon
        self.tray_icon = None
        if PYSTRAY_AVAILABLE:
            # Ensure the tray icon is started after the mainloop has begun
            self.after(0, self._start_tray_thread)

        # Network share setup - now uses self.config
        self.network_share_path = self.ensure_network_share_path()

        # Schedule update check after window is ready (use a short delay, e.g. 1000ms)
        self.after(1000, check_for_update)

    def _start_tray_thread(self):
        # Start the tray icon in a separate thread after the Tk window is initialized
        self.tray_thread = threading.Thread(target=self._run_tray_icon, daemon=True)
        self.tray_thread.start()

    def _toggle_search_bar(self, event=None):
        """Toggles the visibility of the search bar."""
        if self.search_frame.winfo_ismapped():  # Check if it's currently visible
            self.search_frame.pack_forget()
        else:
            self.search_frame.pack(fill="x")


    # Helper function to update the pet's ASCII art display
    def update_pet_display(self, pet_frame, bottom_text=""):
        # Limit bottom_text to fit window width and center it
        if bottom_text:
            lines = bottom_text.split('\n')
            max_width = self.max_song_display_width
            lines = [line[:max_width] for line in lines]
            lines = [line.center(max_width) for line in lines]
            bottom_text = "\n".join(lines)
            full_text = pet_frame + "\n" + bottom_text
        else:
            full_text = pet_frame

        self.label.configure(text=full_text)

    # Helper for scrolling text
    def _get_scrolling_text(self, text):
        if not text:
            return ""

        max_width = self.max_song_display_width
        text_len = len(text)
        if text_len <= max_width:
            self.song_scroll_offset = 0
            self.song_scroll_direction = 1
            self.song_scroll_counter = 0
            return text.center(max_width)

        # Add padding for smooth looping
        padded_text = text + "   "
        padded_len = len(padded_text)

        # Clamp offset
        if self.song_scroll_offset > padded_len - max_width:
            self.song_scroll_offset = padded_len - max_width
            self.song_scroll_direction = -1
            self.song_scroll_counter = 0
        elif self.song_scroll_offset < 0:
            self.song_scroll_offset = 0
            self.song_scroll_direction = 1
            self.song_scroll_counter = 0

        start = self.song_scroll_offset
        end = start + max_width
        return padded_text[start:end]


    # --- Music Control Methods (System-Integrated) ---
    async def get_media_info(self):
        try:
            sessions = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
            
            current_session = sessions.get_current_session()
            
            if current_session:
                self.system_media_session = current_session 

                info = await current_session.try_get_media_properties_async()
                playback_info = current_session.get_playback_info()

                is_playing = (playback_info.playback_status == PLAYBACK_STATUS_PLAYING)
                
                track_title = info.title if info.title else "Unknown Title"
                track_artist = info.artist if info.artist else "Unknown Artist"
                
                print(f"DEBUG: Media Detected: {track_title} by {track_artist}, Playing: {is_playing}")
                
                return is_playing, f"{track_artist} - {track_title}"
            else:
                self.system_media_session = None 
                return False, ""

        except Exception as e:
            if "has no attribute 'playback_status'" in str(e): 
                print(f"ERROR: WinRT object structure mismatch. Ensure winrt-Windows.Media.Control is up to date. Error: {e}")
            else:
                print(f"ERROR: Exception in get_media_info: {e}")
            self.system_media_session = None
            return False, ""

    async def send_media_command(self, command):
        try:
            session_to_use = self.system_media_session 
            if not session_to_use:
                sessions = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
                session_to_use = sessions.get_current_session()
                if not session_to_use:
                    print(f"ERROR: No media session found to send '{command}' command.")
                    return

            if command == "play_pause":
                playback_info = session_to_use.get_playback_info()
                if playback_info.playback_status == PLAYBACK_STATUS_PLAYING:
                    print(f"DEBUG: Sending PAUSE command to session: {session_to_use.source_app_user_model_id}")
                    await session_to_use.try_pause_async()
                else:
                    print(f"DEBUG: Sending PLAY command to session: {session_to_use.source_app_user_model_id}") 
                    await session_to_use.try_play_async()
            elif command == "next":
                print(f"DEBUG: Sending SKIP NEXT command to session: {session_to_use.source_app_user_model_id}")
                await session_to_use.try_skip_next_async()
            elif command == "prev":
                print(f"DEBUG: Sending SKIP PREVIOUS command to session: {session_to_use.source_app_user_model_id}")
                await session_to_use.try_skip_previous_async()
            
            await asyncio.sleep(0.1) 
            print(f"DEBUG: Command '{command}' sent successfully.")

        except Exception as e:
            print(f"ERROR: Exception sending media command {command}: {e}")

    def run_async_loop_for_media_check(self):
        self.media_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.media_loop)
        
        self.media_loop.run_until_complete(self.media_check_loop())

    async def media_check_loop(self):
        while True:
            is_playing, track_info = await self.get_media_info()
            with self.animation_state_lock:
                self.is_music_playing_system = is_playing
                self.current_track_info = track_info
                
            # Update the play/pause button text on the UI thread
            self.after(0, lambda: self.play_pause_button.configure(
                text="⏸️" if self.is_music_playing_system else "▶️"
            ))

            await asyncio.sleep(1) 


    # --- Music Control Methods (UI-Triggered) ---

    def toggle_play_pause(self):
        if WINDOWS_MEDIA_CONTROL_AVAILABLE:
            threading.Thread(target=lambda: asyncio.run(self.send_media_command("play_pause")), daemon=True).start()
        else:
            with self.animation_state_lock:
                # Simulate play/pause for manual mode if system control isn't available
                self.is_music_playing_override = not self.is_music_playing_override
                # In manual mode, system playing status follows override for consistent UI
                self.is_music_playing_system = self.is_music_playing_override # Keep consistent with override
            print(f"Manual Play/Pause Toggled. Music playing (simulated): {self.is_music_playing_override}")

    def skip_prev(self):
        if WINDOWS_MEDIA_CONTROL_AVAILABLE:
            threading.Thread(target=lambda: asyncio.run(self.send_media_command("prev")), daemon=True).start()
        else:
            print("Skipping to previous track (simulated).")
            with self.animation_state_lock:
                # Ensure music mode is active if controls are used manually
                self.is_music_playing_override = True 
                self.is_music_playing_system = True # Keep consistent with override

    def skip_next(self):
        if WINDOWS_MEDIA_CONTROL_AVAILABLE:
            threading.Thread(target=lambda: asyncio.run(self.send_media_command("next")), daemon=True).start()
        else:
            print("Skipping to next track (simulated).")
            with self.animation_state_lock:
                # Ensure music mode is active if controls are used manually
                self.is_music_playing_override = True 
                self.is_music_playing_system = True # Keep consistent with override

    def perform_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return # Don't search if query is empty

        search_engine = self.config.get("search_engine", "Google")
        
        search_urls = {
            "Google": "https://www.google.com/search?q=",
            "Bing": "https://www.bing.com/search?q=",
            "DuckDuckGo": "https://duckduckgo.com/?q="
        }
        
        base_url = search_urls.get(search_engine, search_urls["Google"]) # Default to Google
        full_url = f"{base_url}{requests.utils.quote(query)}"
        
        print(f"Opening search: {full_url}")
        webbrowser.open_new_tab(full_url)
        self.search_entry.delete(0, ctk.END) # Clear the search entry after performing search

    def animate(self):
        current_animation_state = "idle" 
        current_eating_frame_index = 0
        current_music_frame_index = 0 
        self.song_scroll_counter = 0 # Counter for scrolling pause

        while True:
            with self.animation_state_lock:
                is_eating_local = self.is_eating
                is_hovering_file_local = self.is_hovering_file
                eating_message_active = self.eating_message_display_time and \
                                        (time.time() - self.eating_message_display_time) < 2
                upload_progress_local = self.current_upload_progress
                
                # Determine if the pet should be in "music display mode"
                # This is true if:
                # 1. Music is actively playing (system or manual override)
                # 2. Music is currently paused, but there's still valid track info from a session.
                has_active_music_display = (self.is_music_playing_system or self.is_music_playing_override) or \
                                           (not self.is_music_playing_system and bool(self.current_track_info))

                current_track_info_local = self.current_track_info 

            # --- State Transitions ---
            # Priority: Eating > Yum Message > Music > Hover > Idle
            if is_eating_local:
                if current_animation_state != "eating_anim" and current_animation_state != "eating_progress":
                    current_animation_state = "eating_anim"
                    current_eating_frame_index = 0
                    self.after(0, self.music_control_frame.pack_forget) # Hide controls
            elif eating_message_active:
                if current_animation_state != "yum_message":
                    current_animation_state = "yum_message"
                    self.current_progress_text = ascii_progress_bar_states[-1] 
                    self.after(0, self.music_control_frame.pack_forget) # Hide controls
            elif has_active_music_display: # Use the new combined condition
                if current_animation_state != "music":
                    current_animation_state = "music"
                    current_music_frame_index = 0 
                    self.after(0, lambda: self.music_control_frame.pack(fill="x", pady=(0,5))) # Show controls
                    self.song_scroll_offset = 0 # Reset scroll on entering music mode
                    self.song_scroll_counter = 0
            elif is_hovering_file_local:
                if current_animation_state != "hover":
                    current_animation_state = "hover"
                    self.current_frames = hover_frames
                    self.frame_index = 0
                    self.after(0, self.music_control_frame.pack_forget) # Hide controls
            else: 
                if current_animation_state != "idle":
                    current_animation_state = "idle"
                    self.current_frames = idle_frames
                    self.frame_index = 0
                    self.current_progress_text = ""
                    self.current_upload_progress = 0.0
                    self.after(0, self.music_control_frame.pack_forget) # Hide controls

            # --- Animation Logic based on State ---
            if current_animation_state == "eating_anim":
                self.current_frames = eating_frames
                if current_eating_frame_index < len(eating_frames):
                    frame_to_display = eating_frames[current_eating_frame_index]
                    self.after(0, lambda f=frame_to_display, p="": self.update_pet_display(f, p)) 
                    current_eating_frame_index += 1
                    time.sleep(0.15)
                else:
                    current_animation_state = "eating_progress"
                    self.frame_index = 0 
                    
            elif current_animation_state == "eating_progress":
                progress_bar_index = int(upload_progress_local * (len(ascii_progress_bar_states) - 1))
                progress_bar_index = max(0, min(progress_bar_index, len(ascii_progress_bar_states) - 1))
                
                self.current_progress_text = ascii_progress_bar_states[progress_bar_index]
                self.after(0, lambda f=self.last_eating_frame, p=self.current_progress_text: self.update_pet_display(f, p))
                time.sleep(0.1) 

            elif current_animation_state == "yum_message":
                self.after(0, lambda: self.update_pet_display(self.last_eating_frame, "Yum! File uploaded! 🍽️\n" + self.current_progress_text))
                time.sleep(0.1) 
            
            elif current_animation_state == "music": 
                self.current_frames = music_frames 
                current_music_frame_index = (current_music_frame_index + 1) % len(self.current_frames)
                frame_to_display = self.current_frames[current_music_frame_index]
                
                self.after(0, lambda f=frame_to_display, p="": self.update_pet_display(f, p))

                # Update scrolling song title
                scrolling_title = self._get_scrolling_text(current_track_info_local)
                self.after(0, lambda t=scrolling_title: self.track_title_label.configure(text=t))

                # Horizontal scrolling logic
                if len(current_track_info_local) > self.max_song_display_width:
                    padded_len = len(current_track_info_local + "   ")
                    max_offset = padded_len - self.max_song_display_width
                    if self.song_scroll_counter < self.song_scroll_pause_frames:
                        self.song_scroll_counter += 1
                    else:
                        self.song_scroll_offset += self.song_scroll_direction * self.song_scroll_speed
                        if self.song_scroll_offset >= max_offset or self.song_scroll_offset <= 0:
                            self.song_scroll_counter = 0
                else:
                    self.song_scroll_offset = 0
                    self.song_scroll_direction = 1
                    self.song_scroll_counter = 0

                time.sleep(0.2) # Faster update for smooth scrolling

            elif current_animation_state == "hover":
                self.frame_index = (self.frame_index + 1) % len(self.current_frames)
                self.after(0, lambda f=self.current_frames[self.frame_index], p="": self.update_pet_display(f, p))
                time.sleep(0.4)
            
            elif current_animation_state == "idle":
                self.frame_index = (self.frame_index + 1) % len(self.current_frames)
                self.after(0, lambda f=self.current_frames[self.frame_index], p="": self.update_pet_display(f, p))
                time.sleep(0.8)

    def on_file_enter(self, event):
        with self.animation_state_lock:
            # Re-evaluate the music display condition based on current values
            has_active_music_display_local = (self.is_music_playing_system or self.is_music_playing_override) or \
                                             (not self.is_music_playing_system and bool(self.current_track_info))

            # Only allow hover effect if not eating, not showing message, and NOT in music display mode
            if not self.is_eating and \
               not (self.eating_message_display_time and (time.time() - self.eating_message_display_time) < 2) and \
               not has_active_music_display_local: 
                self.after(0, lambda: setattr(self, 'is_hovering_file', True))
        return 'copy'

    def on_file_leave(self, event):
        with self.animation_state_lock:
            # Re-evaluate the music display condition based on current values
            has_active_music_display_local = (self.is_music_playing_system or self.is_music_playing_override) or \
                                             (not self.is_music_playing_system and bool(self.current_track_info))

            # Only turn off hover if not eating, not showing message, and NOT in music display mode
            if not self.is_eating and \
               not (self.eating_message_display_time and (time.time() - self.eating_message_display_time) < 2) and \
               not has_active_music_display_local: 
                self.after(0, lambda: setattr(self, 'is_hovering_file', False))
        return 'copy'

    def start_move(self, event):
        self.win_x = self.winfo_x()
        self.win_y = self.winfo_y()
        self.offset_x = event.x_root - self.win_x
        self.offset_y = event.y_root - self.win_y 
        
    def do_move(self, event):
        new_x = event.x_root - self.offset_x
        new_y = event.y_root - self.offset_y
        self.geometry(f"+{new_x}+{new_y}")

    def handle_drop(self, event):
        with self.animation_state_lock:
            self.after(0, lambda: setattr(self, 'is_hovering_file', False)) 
            # If a file is dropped, turn off manual music override
            self.after(0, lambda: setattr(self, 'is_music_playing_override', False)) 

        files = self.split_filenames(event.data)
        if files: 
            file_path = files[0] 
            print(f"File dropped: {file_path}")
            threading.Thread(target=self.eat_file, args=(file_path,), daemon=True).start()
        return 'copy'

    def split_filenames(self, data):
        if data.startswith("{") and data.endswith("}"):
            data = data[1:-1]
            raw_files = data.split("} {")
            files = []
            for rf in raw_files:
                files.append(rf.strip().strip('{').strip('}').strip('"'))
            return files
        else:
            return [f.strip('"') for f in data.split()]

    def eat_file(self, file_path):
        try:
            file_path = file_path.strip().strip('"')

            dest_folder = self.config.get("network_share_path", "") # Get path from current config
            if not dest_folder:
                self.after(0, lambda: self.update_pet_display(idle_frames[0], "No Share Set! 🚫\nUse Settings!"))
                self.after(3000, lambda: self.after(0, lambda: setattr(self, 'eating_message_display_time', 0)))
                return

            if os.path.isfile(file_path):
                dest_path = os.path.join(dest_folder, os.path.basename(file_path))
                
                if not os.path.exists(dest_folder):
                    print(f"Error: Network share path does not exist or is inaccessible: {dest_folder}")
                    self.after(0, lambda: self.update_pet_display(idle_frames[0], "Share Missing! 🚫"))
                    self.after(2000, lambda: self.after(0, lambda: setattr(self, 'eating_message_display_time', 0))) 
                    return

                total_size = os.path.getsize(file_path)
                bytes_copied = 0

                with self.animation_state_lock:
                    self.after(0, lambda: setattr(self, 'is_eating', True)) 
                    self.after(0, lambda: setattr(self, 'current_upload_progress', 0.0)) 

                try:
                    with open(file_path, 'rb') as fsrc, open(dest_path, 'wb') as fdst:
                        while True:
                            chunk = fsrc.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            fdst.write(chunk)
                            bytes_copied += len(chunk)
                            
                            progress = bytes_copied / total_size
                            with self.animation_state_lock: 
                                self.after(0, lambda p=progress: setattr(self, 'current_upload_progress', p))
                            
                            time.sleep(0.01) 
                            
                except Exception as e:
                    print(f"Error during file copy: {e}")
                    self.after(0, lambda: self.update_pet_display(idle_frames[0], f"Copy Error! ❌\n{str(e)[:20]}..."))
                    self.after(2000, lambda: self.after(0, lambda: setattr(self, 'eating_message_display_time', 0)))
                    with self.animation_state_lock: 
                        self.after(0, lambda: setattr(self, 'is_eating', False)) 
                    return

                print(f"Ate and uploaded: {file_path} → {dest_path}")
                with self.animation_state_lock:
                    self.after(0, lambda: setattr(self, 'is_eating', False)) 
                    self.after(0, lambda: setattr(self, 'eating_message_display_time', time.time())) # Trigger "Yum!" message

            else:
                print(f"Not a valid file: {file_path}")
                self.after(0, lambda: self.update_pet_display(idle_frames[0], "No Food! 😿"))
                self.after(2000, lambda: self.after(0, lambda: setattr(self, 'eating_message_display_time', 0)))

        except Exception as e:
            print(f"Overall error eating file {file_path}: {e}")
            self.after(0, lambda: self.update_pet_display(idle_frames[0], f"Error! 😥\n{str(e)[:20]}..."))
            self.after(2000, lambda: self.after(0, lambda: setattr(self, 'eating_message_display_time', 0)))
            with self.animation_state_lock: 
                self.after(0, lambda: setattr(self, 'is_eating', False)) 

    def _create_tray_image(self):
        # Create a simple icon (white cat face on black background)
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Draw a simple cat face
        draw.ellipse((16, 16, 48, 48), fill=(255,255,255,255))
        draw.polygon([(16,32),(8,8),(24,20)], fill=(255,255,255,255)) # left ear
        draw.polygon([(48,32),(56,8),(40,20)], fill=(255,255,255,255)) # right ear
        draw.ellipse((26,32,30,36), fill=(0,0,0,255)) # left eye
        draw.ellipse((34,32,38,36), fill=(0,0,0,255)) # right eye
        draw.arc((28,40,36,48), 0, 180, fill=(0,0,0,255), width=2) # mouth
        return img

    def _run_tray_icon(self):
        image = self._create_tray_image()
        menu = pystray.Menu(
            pystray.MenuItem('Settings', self._on_tray_settings), # Re-use the existing handler
            pystray.MenuItem('Clear Config', self._on_tray_clear_config),
            pystray.MenuItem('Quit', self._on_tray_quit)
        )
        self.tray_icon = pystray.Icon("Sweep", image, "Sweep", menu)
        self.tray_icon.run()

    def _on_tray_settings(self, icon=None, item=None): # icon and item are passed by pystray, but not by button click
        # Open settings window
        # Check if settings window already exists and is open
        if not hasattr(self, 'settings_window') or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self, self)
            self.settings_window.focus_set() # Bring to front if already open

    def _on_tray_clear_config(self, icon, item):
        # Remove config file and notify user
        try:
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            # Reset config in app memory
            self.config = {}
            # Show a message box on the main thread
            self.after(0, lambda: messagebox.showinfo("Config Cleared", "Network share configuration cleared.\nRestart Sweep to set up again."))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to clear config: {e}"))

    def _on_tray_quit(self, icon, item):
        # Called from tray thread, must stop icon and quit app
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.quit)

    def quit(self):
        # Properly close the app and tray icon
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()

    def ensure_network_share_path(self):
        path = self.config.get("network_share_path", "")
        while not path or not os.path.exists(path):
            self.withdraw() # Hide main window while prompting
            path = filedialog.askdirectory(title="Select Network Share Folder for Sweep") # Directly ask here
            
            if not path:
                # If user cancels, offer to quit
                if messagebox.askyesno("Setup Cancelled", "No network share folder selected. Do you want to quit Sweep?", icon='question'):
                    self.after(0, self.quit)
                    return "" # Return empty path to signal cancellation
                else:
                    # User chose not to quit, re-loop to ask for path again
                    continue 
            elif not os.path.exists(path):
                messagebox.showerror("Error", f"Selected path does not exist:\n{path}")
            else:
                self.config["network_share_path"] = path
                save_config(self.config)
                break
        self.deiconify() # Show main window again once path is set
        return path


if __name__ == "__main__":
    ctk.set_appearance_mode("dark") 
    app = DesktopPet()
    app.mainloop()