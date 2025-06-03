import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import time
import shutil
import os
import asyncio
import platform
import datetime # For TimeSpan conversion

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
(  o  ) 
 > ^ <  
 /   \  
(     ) 
    """,
    r"""
 /\_/\  
(  O  ) 
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
(  O  ) 
 > ^ <  
/  ~  \ 
( === )
    """, 
    r"""
 /\_/\  
( 'o' ) 
 > ^ <  
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
(_________)-,
       /
      ~
    """, 
    r"""
    Zz
  /\_/\
 ( -.- )_
 /       \
(_________)-,
       /
      ~
    """, 
    r"""
   Zzz
  /\_/\
 ( -.- )_
 /       \
(_________)-,
       /
      ~
    """, 
    r"""
    Zz
  /\_/\
 ( -.- )_
 /       \
(_________)-,
       /
      ~
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

NETWORK_SHARE_PATH = r"\\forest\X"  # Your network share path - IMPORTANT: Update this!
CHUNK_SIZE = 65536  

class CTkAppWithDnD(TkinterDnD.DnDWrapper, ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkDnDVersion = TkinterDnD._require(self)

class DesktopPet(CTkAppWithDnD):
    def __init__(self):
        super().__init__()

        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.geometry("150x270+100+100") 
        self.configure(bg="black")

        self.title_label = ctk.CTkLabel(
            self,
            text="Sweep",
            font=("Consolas", 20, "bold"),
            text_color="white",
            fg_color="black",
            height=30
        )
        self.title_label.pack(fill="x", pady=(5,0))

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
            text_color="white",
            fg_color="black",
            justify="left"
        )
        self.label.pack(padx=5, pady=5, fill="both", expand=True)
        
        # --- Music Control and Info Frame ---
        self.music_control_frame = ctk.CTkFrame(self, fg_color="black")
        
        # Song Title Label (for scrolling text)
        self.track_title_label = ctk.CTkLabel(
            self.music_control_frame,
            text="",
            font=("Consolas", 12),
            text_color="white",
            fg_color="black",
            justify="center",
            width=self.max_song_display_width * 8 # Approximate width based on font
        )
        self.track_title_label.pack(pady=(2,5), fill="x") # Adjusted pady since progress bar is gone

        # Removed Song Progress Bar Label and its packing

        # Multimedia Control Buttons
        self.prev_button = ctk.CTkButton(self.music_control_frame, text="⏮️", command=self.skip_prev, width=40, height=25, fg_color="black", hover_color="gray", text_color="white", font=("Consolas", 14))
        self.prev_button.pack(side="left", padx=5, expand=True) 

        self.play_pause_button = ctk.CTkButton(self.music_control_frame, text="▶️", command=self.toggle_play_pause, width=40, height=25, fg_color="black", hover_color="gray", text_color="white", font=("Consolas", 14))
        self.play_pause_button.pack(side="left", padx=5, expand=True)

        self.skip_button = ctk.CTkButton(self.music_control_frame, text="⏭️", command=self.skip_next, width=40, height=25, fg_color="black", hover_color="gray", text_color="white", font=("Consolas", 14))
        self.skip_button.pack(side="left", padx=5, expand=True)

        self.music_control_frame.pack_forget() # Initially hidden

        # Main window bindings
        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)
        self.label.bind("<ButtonPress-1>", self.start_move)
        self.label.bind("<B1-Motion>", self.do_move)
        self.title_label.bind("<ButtonPress-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)

        self.label.drop_target_register(DND_FILES)
        self.label.dnd_bind('<<Drop>>', self.handle_drop)
        self.label.dnd_bind('<<DropEnter>>', self.on_file_enter)
        self.label.dnd_bind('<<DropLeave>>', self.on_file_leave)

        # Removed the "Toggle Music Mode" button

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

    def _start_tray_thread(self):
        # Start the tray icon in a separate thread after the Tk window is initialized
        self.tray_thread = threading.Thread(target=self._run_tray_icon, daemon=True)
        self.tray_thread.start()


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

        # Visibility of music_control_frame and its internal labels/buttons
        # is now handled directly in the animate loop's state transitions.

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

            if os.path.isfile(file_path):
                dest_path = os.path.join(NETWORK_SHARE_PATH, os.path.basename(file_path))
                
                if not os.path.exists(NETWORK_SHARE_PATH):
                    print(f"Error: Network share path does not exist or is inaccessible: {NETWORK_SHARE_PATH}")
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
            pystray.MenuItem('Quit', self._on_tray_quit)
        )
        self.tray_icon = pystray.Icon("Sweep", image, "Sweep", menu)
        self.tray_icon.run()

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


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = DesktopPet()
    app.mainloop()