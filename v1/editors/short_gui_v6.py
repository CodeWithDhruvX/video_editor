import os
import subprocess
import json
import threading
import queue
import shutil
from pathlib import Path
import logging
from tkinter import ttk, filedialog, messagebox, colorchooser
import tkinter as tk
from faster_whisper import WhisperModel
import time
import tempfile
import traceback

# --- Custom Logging Handler ---

class TkinterLogHandler(logging.Handler):
    """Custom logging handler to redirect logs to a Tkinter widget via a queue."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        """
        Puts the log record into the queue.
        Flags records with 'is_status' extra data to update the main status label.
        """
        try:
            is_status_update = getattr(record, 'is_status', False)
            msg_type = "STATUS" if is_status_update else "LOG"
            self.log_queue.put((msg_type, self.format(record)))
        except Exception:
            # Prevent logging errors from crashing the app
            pass

# --- GUI Class ---

class VideoProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Video Processor Pro - Enhanced Edition")
        self.root.geometry("1200x900")
        self.root.configure(bg='#f0f0f0')

        # Variables
        self.input_videos = []
        self.extra_video = None
        self.background_music = None
        self.output_dir = None
        self.processing = False
        self.progress_queue = queue.Queue()
        self.stop_event = threading.Event()

        # Set up the centralized logging system
        self.setup_logging()

        # Load video titles with better error handling
        self.load_video_titles()

        self.setup_ui()
        self.check_progress()
        
    def setup_logging(self):
        """Configures the logging framework to use the custom Tkinter handler."""
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        # Clear any existing handlers to avoid duplicates
        if logger.hasHandlers():
            logger.handlers.clear()

        # Create a handler to route logs to the GUI via the progress queue
        gui_handler = TkinterLogHandler(self.progress_queue)
        gui_formatter = logging.Formatter("🔹 %(message)s")
        gui_handler.setFormatter(gui_formatter)
        logger.addHandler(gui_handler)

        # Optionally, add a handler to also log to the console for debugging
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        logging.info("Logging initialized for Video Processor Pro - Enhanced Edition.")

    def load_video_titles(self):
        """Load video titles with proper error handling"""
        try:
            with open("video_titles.json", "r", encoding="utf-8") as f:
                self.video_title_map = json.load(f)
        except FileNotFoundError:
            logging.info("Video titles file not found, using empty mapping")
            self.video_title_map = []
        except json.JSONDecodeError as e:
            logging.warning(f"Invalid JSON in video_titles.json: {e}")
            self.video_title_map = []
        except Exception as e:
            logging.warning(f"Could not load video titles: {e}")
            self.video_title_map = []

    def setup_ui(self):
        # Main title
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill='x', padx=10, pady=10)
        title_frame.pack_propagate(False)

        title_label = tk.Label(title_frame, text="🎬 Video Processor Pro - Enhanced Edition",
                              font=("Arial", 20, "bold"), fg='white', bg='#2c3e50')
        title_label.pack(expand=True)

        # Create main canvas and scrollbar for the entire interface
        self.main_canvas = tk.Canvas(self.root, bg='#f0f0f0', highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_main_frame = tk.Frame(self.main_canvas, bg='#f0f0f0')

        self.scrollable_main_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )

        self.main_canvas.create_window((0, 0), window=self.scrollable_main_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=main_scrollbar.set)

        self.main_canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=10)
        main_scrollbar.pack(side="right", fill="y", padx=(0, 20), pady=10)

        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.main_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # File selection section
        files_frame = tk.LabelFrame(self.scrollable_main_frame, text="📁 File Selection",
                                   font=("Arial", 12, "bold"), bg='#f0f0f0', padx=15, pady=15)
        files_frame.pack(fill='x', pady=10, padx=10)

        # Input videos
        tk.Button(files_frame, text="🎥 Select Main Videos",
                 command=self.select_input_videos, bg='#3498db', fg='white',
                 font=("Arial", 11, "bold"), padx=25, pady=8, relief='flat').pack(pady=5)

        # Enhanced input video display with scrollable listbox
        input_display_frame = tk.Frame(files_frame, bg='#f0f0f0')
        input_display_frame.pack(fill='x', pady=5)

        tk.Label(input_display_frame, text="Selected Videos:", font=("Arial", 10, "bold"), 
                bg='#f0f0f0').pack(anchor='w')

        self.input_listbox_frame = tk.Frame(input_display_frame, bg='#f0f0f0')
        self.input_listbox_frame.pack(fill='x', pady=2)

        self.input_listbox = tk.Listbox(self.input_listbox_frame, height=4, font=("Arial", 9), 
                                       selectmode=tk.EXTENDED, bg='#ffffff')
        input_listbox_scroll = tk.Scrollbar(self.input_listbox_frame, orient="vertical",
                                           command=self.input_listbox.yview)
        self.input_listbox.configure(yscrollcommand=input_listbox_scroll.set)

        self.input_listbox.pack(side="left", fill="both", expand=True)
        input_listbox_scroll.pack(side="right", fill="y")

        # Remove selected video button
        remove_btn_frame = tk.Frame(files_frame, bg='#f0f0f0')
        remove_btn_frame.pack(pady=5)

        tk.Button(remove_btn_frame, text="🗑️ Remove Selected",
                 command=self.remove_selected_videos, bg='#e74c3c', fg='white',
                 font=("Arial", 9), padx=15, pady=5, relief='flat').pack(side='left')

        tk.Button(remove_btn_frame, text="🧹 Clear All",
                 command=self.clear_all_videos, bg='#95a5a6', fg='white',
                 font=("Arial", 9), padx=15, pady=5, relief='flat').pack(side='left', padx=(10, 0))

        # Extra video (optional) - Enhanced section
        extra_frame = tk.LabelFrame(files_frame, text="🔗 Video Merging Options", 
                                   font=("Arial", 11, "bold"), bg='#f0f0f0', padx=10, pady=10)
        extra_frame.pack(fill='x', pady=(10, 5))

        self.enable_merge_var = tk.BooleanVar(value=False)
        merge_check = tk.Checkbutton(extra_frame, text="Enable Video Merging",
                                   variable=self.enable_merge_var, bg='#f0f0f0',
                                   font=("Arial", 10, "bold"), command=self.toggle_merge_options)
        merge_check.pack(anchor='w', pady=5)

        self.merge_options_frame = tk.Frame(extra_frame, bg='#f0f0f0')
        self.merge_options_frame.pack(fill='x', pady=(5, 0))

        self.select_extra_btn = tk.Button(self.merge_options_frame, text="➕ Select Extra Video to Merge",
                                         command=self.select_extra_video, bg='#e67e22', fg='white',
                                         font=("Arial", 10, "bold"), padx=20, pady=5, state='disabled', relief='flat')
        self.select_extra_btn.pack(pady=2)

        self.extra_label = tk.Label(self.merge_options_frame, text="No extra video selected",
                                   bg='#f0f0f0', wraplength=800, state='disabled', font=("Arial", 9))
        self.extra_label.pack(pady=2)

        # Clear extra video button
        self.clear_extra_btn = tk.Button(self.merge_options_frame, text="❌ Clear Extra Video",
                                        command=self.clear_extra_video, bg='#e74c3c', fg='white',
                                        font=("Arial", 9), padx=10, pady=5, state='disabled', relief='flat')
        self.clear_extra_btn.pack(pady=5)

        # Background music (optional) - Enhanced section
        music_frame = tk.LabelFrame(files_frame, text="🎵 Background Music Options", 
                                   font=("Arial", 11, "bold"), bg='#f0f0f0', padx=10, pady=10)
        music_frame.pack(fill='x', pady=5)

        music_btn_frame = tk.Frame(music_frame, bg='#f0f0f0')
        music_btn_frame.pack(pady=5)

        tk.Button(music_btn_frame, text="🎵 Select Background Music",
                 command=self.select_background_music, bg='#9b59b6', fg='white',
                 font=("Arial", 10, "bold"), padx=20, pady=5, relief='flat').pack(side='left')

        tk.Button(music_btn_frame, text="❌ Clear Music",
                 command=self.clear_background_music, bg='#e74c3c', fg='white',
                 font=("Arial", 9), padx=10, pady=5, relief='flat').pack(side='left', padx=(10, 0))

        self.music_label = tk.Label(music_frame, text="No background music selected",
                                   bg='#f0f0f0', wraplength=800, font=("Arial", 9))
        self.music_label.pack(pady=2)

        # Output directory
        output_frame = tk.LabelFrame(files_frame, text="📂 Output Settings", 
                                    font=("Arial", 11, "bold"), bg='#f0f0f0', padx=10, pady=10)
        output_frame.pack(fill='x', pady=5)

        tk.Button(output_frame, text="📂 Select Output Folder",
                 command=self.select_output_dir, bg='#27ae60', fg='white',
                 font=("Arial", 10, "bold"), padx=20, pady=5, relief='flat').pack(pady=5)

        self.output_label = tk.Label(output_frame, text="No output folder selected",
                                    bg='#f0f0f0', wraplength=800, font=("Arial", 9))
        self.output_label.pack(pady=2)

        # Processing options - Enhanced
        options_frame = tk.LabelFrame(self.scrollable_main_frame, text="⚙️ Processing Options",
                                     font=("Arial", 12, "bold"), bg='#f0f0f0', padx=15, pady=15)
        options_frame.pack(fill='x', pady=10, padx=10)

        # Options row 1 - Quality and Volume
        options_row1 = tk.Frame(options_frame, bg='#f0f0f0')
        options_row1.pack(fill='x', padx=10, pady=8)

        # Quality preset
        quality_frame = tk.Frame(options_row1, bg='#f0f0f0')
        quality_frame.pack(side='left', padx=(0, 30))

        tk.Label(quality_frame, text="Quality Preset:", font=("Arial", 10, "bold"), bg='#f0f0f0').pack(anchor='w')
        self.quality_var = tk.StringVar(value="fast")
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_var,
                                    values=["ultrafast", "fast", "medium", "slow"],
                                    state="readonly", width=12)
        quality_combo.pack(pady=2)

        # Music volume
        volume_frame = tk.Frame(options_row1, bg='#f0f0f0')
        volume_frame.pack(side='left')

        tk.Label(volume_frame, text="Music Volume:", font=("Arial", 10, "bold"), bg='#f0f0f0').pack(anchor='w')
        volume_control_frame = tk.Frame(volume_frame, bg='#f0f0f0')
        volume_control_frame.pack(pady=2)

        self.volume_var = tk.DoubleVar(value=0.30)
        volume_scale = tk.Scale(volume_control_frame, from_=0.0, to=0.5, resolution=0.05,
                               orient='horizontal', variable=self.volume_var, length=140)
        volume_scale.pack(side='left')

        self.volume_label = tk.Label(volume_control_frame, text="0.15", font=("Arial", 9), bg='#f0f0f0')
        self.volume_label.pack(side='left', padx=(5, 0))

        # Update volume label when scale changes
        volume_scale.configure(command=lambda val: self.volume_label.config(text=f"{float(val):.2f}"))

        # Options row 2 - Checkboxes
        options_row2 = tk.Frame(options_frame, bg='#f0f0f0')
        options_row2.pack(fill='x', padx=10, pady=8)

        # Auto-editing checkbox
        self.auto_edit_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_row2, text="✂️ Auto-Edit Videos (Remove Silent Parts)",
                      variable=self.auto_edit_var, bg='#f0f0f0', font=("Arial", 10, "bold")).pack(anchor='w', pady=2)

        # Enable GPU acceleration
        self.gpu_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_row2, text="🚀 GPU Acceleration (NVENC if available)",
                      variable=self.gpu_var, bg='#f0f0f0', font=("Arial", 10, "bold")).pack(anchor='w', pady=2)

        # Enable music ducking
        self.ducking_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_row2, text="🎵 Smart Music Ducking (Lower music during speech)",
                      variable=self.ducking_var, bg='#f0f0f0', font=("Arial", 10, "bold")).pack(anchor='w', pady=2)

        # Enhanced Subtitle customization section
        subtitle_frame = tk.LabelFrame(self.scrollable_main_frame, text="📝 Advanced Subtitle Customization",
                                      font=("Arial", 12, "bold"), bg='#f0f0f0', padx=15, pady=15)
        subtitle_frame.pack(fill='x', pady=10, padx=10)

        # Subtitle display mode row
        mode_row = tk.Frame(subtitle_frame, bg='#f0f0f0')
        mode_row.pack(fill='x', padx=10, pady=8)

        tk.Label(mode_row, text="Display Mode:", font=("Arial", 11, "bold"), bg='#f0f0f0').pack(anchor='w')
        
        mode_options_frame = tk.Frame(mode_row, bg='#f0f0f0')
        mode_options_frame.pack(anchor='w', pady=5)

        self.subtitle_mode_var = tk.StringVar(value="single")
        tk.Radiobutton(mode_options_frame, text="📝 Single Word Subtitles", variable=self.subtitle_mode_var,
                      value="single", bg='#f0f0f0', font=("Arial", 10), 
                      command=self.toggle_word_count).pack(anchor='w', pady=2)
        tk.Radiobutton(mode_options_frame, text="📄 Multiple Words Subtitles", variable=self.subtitle_mode_var,
                      value="multiple", bg='#f0f0f0', font=("Arial", 10),
                      command=self.toggle_word_count).pack(anchor='w', pady=2)

        # Words count row (initially hidden) - Enhanced
        self.words_count_frame = tk.Frame(subtitle_frame, bg='#f0f0f0')
        self.words_count_frame.pack(fill='x', padx=10, pady=8)

        words_count_inner = tk.Frame(self.words_count_frame, bg='#f0f0f0')
        words_count_inner.pack(anchor='w')

        tk.Label(words_count_inner, text="Words per subtitle group:", 
                font=("Arial", 10, "bold"), bg='#f0f0f0').pack(side='left')
        
        self.words_count_var = tk.IntVar(value=3)
        words_scale = tk.Scale(words_count_inner, from_=2, to=10, resolution=1,
                             orient='horizontal', variable=self.words_count_var, length=200)
        words_scale.pack(side='left', padx=(15, 5))
        
        self.words_count_label = tk.Label(words_count_inner, text="3 words per group", 
                                         font=("Arial", 10, "bold"), bg='#f0f0f0', fg='#2c3e50')
        self.words_count_label.pack(side='left', padx=(5, 0))
        
        # Update words count label when scale changes
        words_scale.configure(command=lambda val: self.words_count_label.config(text=f"{int(float(val))} words per group"))

        # Subtitle size and appearance row
        appearance_row = tk.Frame(subtitle_frame, bg='#f0f0f0')
        appearance_row.pack(fill='x', padx=10, pady=8)

        # Subtitle size
        size_frame = tk.Frame(appearance_row, bg='#f0f0f0')
        size_frame.pack(side='left', padx=(0, 30))

        tk.Label(size_frame, text="Subtitle Size (pixels):", font=("Arial", 10, "bold"), bg='#f0f0f0').pack(anchor='w')
        size_control_frame = tk.Frame(size_frame, bg='#f0f0f0')
        size_control_frame.pack(pady=2)

        self.subtitle_size_var = tk.IntVar(value=24)
        size_scale = tk.Scale(size_control_frame, from_=12, to=48, resolution=2,
                             orient='horizontal', variable=self.subtitle_size_var, length=180)
        size_scale.pack(side='left')
        
        self.size_label = tk.Label(size_control_frame, text="24px", font=("Arial", 10, "bold"), 
                                  bg='#f0f0f0', fg='#2c3e50')
        self.size_label.pack(side='left', padx=(8, 0))
        
        # Update size label when scale changes
        size_scale.configure(command=lambda val: self.size_label.config(text=f"{int(float(val))}px"))

        # Subtitle color selection - Enhanced
        color_frame = tk.Frame(appearance_row, bg='#f0f0f0')
        color_frame.pack(side='left')

        tk.Label(color_frame, text="Subtitle Color:", font=("Arial", 10, "bold"), bg='#f0f0f0').pack(anchor='w')

        # Color control frame
        color_control_frame = tk.Frame(color_frame, bg='#f0f0f0')
        color_control_frame.pack(pady=2)

        # Color preview and hex input
        self.subtitle_color = "#FFFFFF"
        self.color_preview = tk.Label(color_control_frame, text="    ", bg=self.subtitle_color,
                                     relief='solid', borderwidth=2, width=6, height=2, cursor='hand2')
        self.color_preview.pack(side='left', padx=(0, 8))
        self.color_preview.bind("<Button-1>", lambda e: self.pick_subtitle_color())

        # Color picker and hex input frame
        color_input_frame = tk.Frame(color_control_frame, bg='#f0f0f0')
        color_input_frame.pack(side='left')

        # Color picker button
        tk.Button(color_input_frame, text="🎨 Pick Color", command=self.pick_subtitle_color,
                 bg='#f39c12', fg='white', font=("Arial", 9), relief='flat').pack(pady=(0, 2))

        # Hex input frame
        hex_frame = tk.Frame(color_input_frame, bg='#f0f0f0')
        hex_frame.pack()

        tk.Label(hex_frame, text="Hex:", font=("Arial", 9), bg='#f0f0f0').pack(side='left')
        self.hex_var = tk.StringVar(value=self.subtitle_color)
        self.hex_entry = tk.Entry(hex_frame, textvariable=self.hex_var, width=8, font=("Arial", 9))
        self.hex_entry.pack(side='left', padx=2)
        self.hex_entry.bind('<KeyRelease>', self.on_hex_change)

        tk.Button(hex_frame, text="Apply", command=self.apply_hex_color,
                 bg='#27ae60', fg='white', font=("Arial", 8), relief='flat').pack(side='left', padx=(2, 0))

        # Preset colors - Enhanced
        preset_frame = tk.Frame(subtitle_frame, bg='#f0f0f0')
        preset_frame.pack(fill='x', padx=10, pady=8)

        tk.Label(preset_frame, text="Quick Color Presets:", font=("Arial", 10, "bold"), bg='#f0f0f0').pack(anchor='w')

        preset_colors_frame = tk.Frame(preset_frame, bg='#f0f0f0')
        preset_colors_frame.pack(pady=5)

        preset_colors = [
            ("#FFFFFF", "White"), ("#FFFF00", "Yellow"), ("#FF0000", "Red"),
            ("#00FF00", "Green"), ("#0000FF", "Blue"), ("#FF00FF", "Magenta"),
            ("#00FFFF", "Cyan"), ("#FFA500", "Orange"), ("#000000", "Black"),
            ("#808080", "Gray")
        ]

        for i, (color, name) in enumerate(preset_colors):
            btn = tk.Button(preset_colors_frame, text="  ", bg=color, width=4, height=2,
                           relief='solid', borderwidth=1, cursor='hand2',
                           command=lambda c=color: self.set_subtitle_color(c))
            btn.pack(side='left', padx=2)
            # Add tooltip
            self.create_tooltip(btn, name)

        # Initially hide words count controls
        self.toggle_word_count()

        # Process and Stop buttons frame - Enhanced
        button_frame = tk.Frame(self.scrollable_main_frame, bg='#f0f0f0')
        button_frame.pack(pady=25)

        # Process button
        self.process_btn = tk.Button(button_frame, text="🚀 START PROCESSING",
                                    command=self.start_processing, bg='#e74c3c', fg='white',
                                    font=("Arial", 14, "bold"), pady=12, padx=30, relief='flat',
                                    cursor='hand2')
        self.process_btn.pack(side='left', padx=(0, 15))

        # Stop button (initially disabled)
        self.stop_btn = tk.Button(button_frame, text="⏹️ STOP PROCESSING",
                                 command=self.stop_processing, bg='#e67e22', fg='white',
                                 font=("Arial", 14, "bold"), pady=12, padx=30, state='disabled',
                                 relief='flat', cursor='hand2')
        self.stop_btn.pack(side='left')

        # Enhanced Progress section
        progress_frame = tk.LabelFrame(self.scrollable_main_frame, text="📊 Processing Progress & Logs",
                                      font=("Arial", 12, "bold"), bg='#f0f0f0', padx=15, pady=15)
        progress_frame.pack(fill='both', expand=True, pady=10, padx=10)

        # Progress bar with percentage label
        progress_container = tk.Frame(progress_frame, bg='#f0f0f0')
        progress_container.pack(fill='x', pady=10)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_container, variable=self.progress_var,
                                          maximum=100, length=800, mode='determinate')
        self.progress_bar.pack(side='left', fill='x', expand=True)

        self.progress_percent_label = tk.Label(progress_container, text="0%", font=("Arial", 10, "bold"),
                                             bg='#f0f0f0', width=5)
        self.progress_percent_label.pack(side='right', padx=(10, 0))

        self.status_label = tk.Label(progress_frame, text="Ready to process",
                                    bg='#f0f0f0', font=("Arial", 11, "bold"), fg='#2c3e50')
        self.status_label.pack(pady=8)

        # Enhanced Log text area with scrollbar
        log_frame = tk.Frame(progress_frame, bg='#f0f0f0')
        log_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Log text with enhanced styling
        self.log_text = tk.Text(log_frame, height=10, bg='#2c3e50', fg='#ecf0f1',
                               font=("Consolas", 9), wrap=tk.WORD, state=tk.DISABLED)
        
        # Enhanced scrollbar for logs
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")

        # Log control buttons
        log_control_frame = tk.Frame(progress_frame, bg='#f0f0f0')
        log_control_frame.pack(pady=5)

        tk.Button(log_control_frame, text="🧹 Clear Logs", command=self.clear_logs,
                 bg='#95a5a6', fg='white', font=("Arial", 9), padx=15, pady=5, relief='flat').pack(side='left')

        tk.Button(log_control_frame, text="💾 Save Logs", command=self.save_logs,
                 bg='#3498db', fg='white', font=("Arial", 9), padx=15, pady=5, relief='flat').pack(side='left', padx=(10, 0))

    def create_tooltip(self, widget, text):
        """Create a simple tooltip for a widget"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, font=("Arial", 8), bg="#ffffe0", 
                           relief="solid", borderwidth=1)
            label.pack()
            widget.tooltip = tooltip
            
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                delattr(widget, 'tooltip')
                
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def remove_selected_videos(self):
        """Remove selected videos from the listbox"""
        selected_indices = self.input_listbox.curselection()
        if selected_indices:
            # Remove in reverse order to maintain indices
            for index in reversed(selected_indices):
                if 0 <= index < len(self.input_videos):
                    del self.input_videos[index]
            self.update_input_listbox()
        else:
            messagebox.showinfo("No Selection", "Please select videos to remove from the list.")

    def clear_all_videos(self):
        """Clear all videos from the list"""
        if self.input_videos and messagebox.askquestion("Clear All", 
                                                        "Are you sure you want to clear all selected videos?") == 'yes':
            self.input_videos.clear()
            self.update_input_listbox()

    def update_input_listbox(self):
        """Update the input video listbox display"""
        self.input_listbox.delete(0, tk.END)
        for video in self.input_videos:
            filename = os.path.basename(video)
            # Show filename and size info
            try:
                if os.path.exists(video):
                    size_mb = os.path.getsize(video) / (1024 * 1024)
                    self.input_listbox.insert(tk.END, f"{filename} ({size_mb:.1f} MB)")
                else:
                    self.input_listbox.insert(tk.END, f"{filename} (File not found)")
            except Exception:
                self.input_listbox.insert(tk.END, filename)

    def clear_extra_video(self):
        """Clear the selected extra video"""
        self.extra_video = None
        self.extra_label.config(text="No extra video selected")

    def clear_logs(self):
        """Clear the log text area"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def save_logs(self):
        """Save logs to a file"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save Processing Logs"
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Logs saved to: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save logs: {e}")

    def toggle_merge_options(self):
        """Enable/disable merge options based on checkbox"""
        enabled = self.enable_merge_var.get()
        
        # Enable/disable all merge-related widgets
        state = 'normal' if enabled else 'disabled'
        self.select_extra_btn.config(state=state)
        self.clear_extra_btn.config(state=state)
        self.extra_label.config(fg='black' if enabled else 'gray')
        
        if not enabled:
            self.clear_extra_video()

    def toggle_word_count(self):
        """Show/hide word count controls based on mode selection"""
        if self.subtitle_mode_var.get() == "multiple":
            self.words_count_frame.pack(fill='x', padx=10, pady=8, before=self.words_count_frame.master.winfo_children()[-1])
        else:
            self.words_count_frame.pack_forget()

    def pick_subtitle_color(self):
        color = colorchooser.askcolor(title="Choose Subtitle Color",
                                     initialcolor=self.subtitle_color)
        if color[1]:
            self.set_subtitle_color(color[1])

    def set_subtitle_color(self, color_hex):
        self.subtitle_color = color_hex.upper()
        self.color_preview.config(bg=self.subtitle_color)
        self.hex_var.set(self.subtitle_color)

    def on_hex_change(self, event):
        hex_value = self.hex_var.get().strip()
        if len(hex_value) == 7 and hex_value.startswith('#'):
            try:
                self.root.winfo_rgb(hex_value)
                self.color_preview.config(bg=hex_value)
            except Exception:
                pass

    def apply_hex_color(self):
        hex_value = self.hex_var.get().strip().upper()
        if not hex_value.startswith('#'):
            hex_value = '#' + hex_value

        if len(hex_value) == 7:
            try:
                self.root.winfo_rgb(hex_value)
                self.set_subtitle_color(hex_value)
            except Exception:
                messagebox.showerror("Invalid Color", "Please enter a valid hex color (e.g., #FFFFFF)")
        else:
            messagebox.showerror("Invalid Format", "Hex color must be 6 characters (e.g., #FFFFFF)")

    def log_message(self, message):
        """Add message to log display"""
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
            self.root.update_idletasks()
        except Exception:
            # Prevent logging errors from crashing the app
            pass

    def select_input_videos(self):
        files = filedialog.askopenfilenames(
            title="Select Main Input Videos",
            filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi *.m4v *.wmv *.flv")]
        )
        if files:
            # Validate that all selected files exist
            valid_files = []
            invalid_files = []
            for file in files:
                if os.path.exists(file):
                    valid_files.append(file)
                else:
                    invalid_files.append(os.path.basename(file))
            
            if invalid_files:
                messagebox.showwarning("Invalid Files", 
                                     f"The following files could not be found:\n{', '.join(invalid_files)}")
            
            if valid_files:
                self.input_videos = list(valid_files)
                self.update_input_listbox()

    def select_extra_video(self):
        file = filedialog.askopenfilename(
            title="Select Extra Video to Merge",
            filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi *.m4v *.wmv *.flv")]
        )
        if file:
            if os.path.exists(file):
                self.extra_video = file
                filename = os.path.basename(file)
                try:
                    size_mb = os.path.getsize(file) / (1024 * 1024)
                    self.extra_label.config(text=f"✅ Extra video: {filename} ({size_mb:.1f} MB)")
                except Exception:
                    self.extra_label.config(text=f"✅ Extra video: {filename}")
                self.clear_extra_btn.config(state='normal')
            else:
                messagebox.showerror("File Not Found", f"The selected file could not be found:\n{file}")

    def select_background_music(self):
        file = filedialog.askopenfilename(
            title="Select Background Music (Optional)",
            filetypes=[("Audio Files", "*.mp3 *.wav *.aac *.m4a *.ogg *.flac *.wma")]
        )
        if file:
            if os.path.exists(file):
                self.background_music = file
                filename = os.path.basename(file)
                try:
                    size_mb = os.path.getsize(file) / (1024 * 1024)
                    self.music_label.config(text=f"✅ Background music: {filename} ({size_mb:.1f} MB)")
                except Exception:
                    self.music_label.config(text=f"✅ Background music: {filename}")
            else:
                messagebox.showerror("File Not Found", f"The selected file could not be found:\n{file}")

    def clear_background_music(self):
        self.background_music = None
        self.music_label.config(text="No background music selected")

    def select_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Folder")
        if directory:
            if os.path.exists(directory) and os.path.isdir(directory):
                self.output_dir = directory
                self.output_label.config(text=f"✅ Output folder: {directory}")
            else:
                messagebox.showerror("Invalid Directory", "The selected directory is not valid or accessible.")

    def validate_inputs(self):
        """Validate all inputs before processing"""
        if not self.input_videos:
            messagebox.showerror("Error", "Please select main input videos")
            return False
        
        # Check if all input videos exist
        missing_videos = []
        for video in self.input_videos:
            if not os.path.exists(video):
                missing_videos.append(os.path.basename(video))
        
        if missing_videos:
            messagebox.showerror("Missing Videos", 
                               f"The following videos could not be found:\n{', '.join(missing_videos)}")
            return False
        
        if self.enable_merge_var.get():
            if not self.extra_video:
                messagebox.showerror("Error", "Please select extra video to merge or disable video merging")
                return False
            if not os.path.exists(self.extra_video):
                messagebox.showerror("Error", "The selected extra video could not be found")
                return False
        
        if not self.output_dir:
            messagebox.showerror("Error", "Please select output folder")
            return False
        
        if not os.path.exists(self.output_dir) or not os.path.isdir(self.output_dir):
            messagebox.showerror("Error", "The selected output directory is not valid")
            return False
        
        if self.background_music and not os.path.exists(self.background_music):
            messagebox.showerror("Error", "The selected background music file could not be found")
            return False
        
        return True

    def start_processing(self):
        if not self.validate_inputs():
            return

        if self.processing:
            messagebox.showwarning("Warning", "Processing already in progress!")
            return

        self.stop_event.clear()
        self.processing = True
        self.process_btn.config(state='disabled', text="⏳ PROCESSING...")
        self.stop_btn.config(state='normal')
        self.progress_var.set(0)
        self.progress_percent_label.config(text="0%")
        self.clear_logs()

        thread = threading.Thread(target=self.process_videos_thread, daemon=True)
        thread.start()

    def stop_processing(self):
        if not self.processing:
            return

        if messagebox.askquestion("Stop Processing",
                                 "Are you sure you want to stop processing?\nCurrent video will be completed, but remaining videos will be skipped.",
                                 icon='warning') == 'yes':
            self.stop_event.set()
            logging.warning("🛑 Stop requested by user. Finishing current video...")
            self.stop_btn.config(state='disabled', text="⏳ STOPPING...")

    def process_videos_thread(self):
        try:
            processor = OptimizedVideoProcessor(self.progress_queue, self.video_title_map, self.stop_event)
            processor.process_all_videos(
                self.input_videos, self.extra_video if self.enable_merge_var.get() else None, 
                self.output_dir, self.background_music, self.quality_var.get(), self.gpu_var.get(), 
                self.volume_var.get(), self.ducking_var.get(), self.auto_edit_var.get(), 
                self.subtitle_color, self.subtitle_mode_var.get(), self.subtitle_size_var.get(),
                self.words_count_var.get()
            )

            if self.stop_event.is_set():
                self.progress_queue.put(("STOPPED", "🛑 Processing stopped by user"))
            else:
                self.progress_queue.put(("COMPLETE", "🎉 All videos processed successfully!"))

        except Exception as e:
            if self.stop_event.is_set():
                self.progress_queue.put(("STOPPED", "🛑 Processing stopped by user"))
            else:
                logging.error(f"❌ Processing failed: {e}", exc_info=True)
                self.progress_queue.put(("ERROR", f"❌ An unexpected error occurred: {str(e)}"))
        finally:
            self.processing = False

    def check_progress(self):
        """Check for progress and log updates from the worker thread's queue."""
        try:
            while True:
                msg_type, message = self.progress_queue.get_nowait()

                if msg_type == "PROGRESS":
                    self.progress_var.set(message)
                    self.progress_percent_label.config(text=f"{int(message)}%")
                elif msg_type == "STATUS":
                    self.status_label.config(text=message)
                    self.log_message(message)
                elif msg_type == "LOG":
                    self.log_message(message)
                elif msg_type in ("COMPLETE", "STOPPED", "ERROR"):
                    self.status_label.config(text=message)
                    if msg_type != "ERROR":
                       self.log_message(message)
                    
                    self.process_btn.config(state='normal', text="🚀 START PROCESSING")
                    self.stop_btn.config(state='disabled', text="⏹️ STOP PROCESSING")
                    
                    if msg_type == "COMPLETE":
                        self.progress_var.set(100)
                        self.progress_percent_label.config(text="100%")
                        messagebox.showinfo("Success", "All videos processed successfully!")
                    elif msg_type == "STOPPED":
                        messagebox.showinfo("Stopped", "Processing stopped by user")
                    elif msg_type == "ERROR":
                        messagebox.showerror("Error", message)

        except queue.Empty:
            pass

        self.root.after(100, self.check_progress)

# --- Video Processing Class ---

class OptimizedVideoProcessor:
    def __init__(self, progress_queue, video_title_map, stop_event):
        self.progress_queue = progress_queue
        self.video_title_map = video_title_map
        self.whisper_model = None
        self.stop_event = stop_event

    def update_progress(self, percentage):
        """Sends a progress update to the GUI queue."""
        try:
            self.progress_queue.put(("PROGRESS", max(0, min(100, percentage))))
        except Exception:
            pass

    def check_stop(self):
        return self.stop_event.is_set()

    def get_whisper_model(self):
        if self.whisper_model is None:
            logging.info("🧠 Loading Whisper model...", extra={'is_status': True})
            try:
                self.whisper_model = WhisperModel("large-v3", compute_type="int8")
                logging.info("✅ Loaded large-v3 Whisper model")
            except Exception as e:
                logging.warning(f"⚠️ Could not load 'large-v3' model, trying 'small'. Reason: {e}")
                try:
                    self.whisper_model = WhisperModel("small", compute_type="int8")
                    logging.info("✅ Loaded small Whisper model")
                except Exception as e2:
                    logging.warning(f"⚠️ Could not load 'small' model, falling back to 'tiny'. Reason: {e2}")
                    self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                    logging.info("✅ Loaded tiny Whisper model")
        return self.whisper_model

    def hex_to_ass_color(self, hex_color):
        """Convert hex color to ASS subtitle format"""
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"&H00{b:02X}{g:02X}{r:02X}"
        except Exception:
            # Default to white if conversion fails
            return "&H00FFFFFF"

    def format_ass_time(self, seconds):
        """Format time for ASS subtitle format"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds * 100) % 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def check_ffmpeg_availability(self):
        """Check if required tools are available"""
        missing_tools = []
        
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True, timeout=10)
            logging.info("✅ FFmpeg is available")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            missing_tools.append("FFmpeg")
        
        try:
            result = subprocess.run(["auto-editor", "--version"], capture_output=True, check=True, text=True, timeout=10)
            logging.info("✅ auto-editor is available")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            missing_tools.append("auto-editor")
        
        if missing_tools:
            raise Exception(f"Required tools not found: {', '.join(missing_tools)}. Please install them and ensure they are in your system's PATH.")
        
        return True

    def transcribe_audio_optimized(self, audio_path):
        """Transcribe audio using Whisper with error handling"""
        try:
            if self.check_stop(): 
                return []
            
            if not os.path.exists(audio_path):
                logging.error(f"Audio file not found: {audio_path}")
                return []
            
            logging.info(f"🧠 Transcribing: {os.path.basename(audio_path)}", extra={'is_status': True})
            model = self.get_whisper_model()
            
            segments, _ = model.transcribe(
                audio_path, beam_size=1, best_of=1, word_timestamps=True,
                language="en", condition_on_previous_text=False
            )
            
            words = []
            for segment in segments:
                if self.check_stop(): 
                    break
                if hasattr(segment, 'words') and segment.words:
                    for w in segment.words:
                        if w.word and w.word.strip():
                            words.append({
                                "word": w.word.strip(),
                                "start": max(0, w.start),  # Ensure non-negative
                                "end": max(w.start, w.end)  # Ensure end >= start
                            })
            
            logging.info(f"✅ Transcribed {len(words)} words")
            return words
        except Exception as e:
            logging.error(f"❌ Transcription failed: {e}", exc_info=True)
            return []

    def generate_grouped_subtitles(self, words, words_per_group):
        """Group words into subtitle segments with better error handling"""
        if not words:
            return []
        
        grouped_subtitles = []
        for i in range(0, len(words), words_per_group):
            group = words[i:i + words_per_group]
            if group:
                try:
                    text = " ".join([w["word"] for w in group if w.get("word")])
                    start_time = group[0]["start"]
                    end_time = group[-1]["end"]
                    
                    # Ensure valid timing
                    if end_time > start_time and text.strip():
                        grouped_subtitles.append({
                            "text": text.strip().upper(),
                            "start": start_time,
                            "end": end_time
                        })
                except Exception as e:
                    logging.warning(f"⚠️ Error grouping subtitle segment: {e}")
                    continue
        
        return grouped_subtitles

    def generate_ass_subtitles(self, content, ass_path, subtitle_color="#FFFFFF", subtitle_size=24, mode="single", words_count=1):
        """Generate ASS subtitle file with improved error handling"""
        if self.check_stop(): 
            return
        
        try:
            ass_color = self.hex_to_ass_color(subtitle_color)
            
            with open(ass_path, "w", encoding="utf-8") as f:
                f.write(f"""[Script Info]
Title: {"Single Word" if mode == "single" else f"{words_count} Words"} Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,{subtitle_size},{ass_color},&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
                
                if mode == "single":
                    # Single word mode
                    for w in content:
                        if self.check_stop(): 
                            break
                        try:
                            word = w.get("word", "").strip().upper()
                            start, end = w.get("start", 0), w.get("end", 0)
                            if word and end > start:
                                f.write(f"Dialogue: 0,{self.format_ass_time(start)},{self.format_ass_time(end)},Default,,0,0,0,,{word}\n")
                        except Exception as e:
                            logging.warning(f"⚠️ Error writing subtitle: {e}")
                            continue
                else:
                    # Multiple words mode
                    grouped_subs = self.generate_grouped_subtitles(content, words_count)
                    for sub in grouped_subs:
                        if self.check_stop(): 
                            break
                        try:
                            text = sub.get("text", "")
                            start, end = sub.get("start", 0), sub.get("end", 0)
                            if text and end > start:
                                f.write(f"Dialogue: 0,{self.format_ass_time(start)},{self.format_ass_time(end)},Default,,0,0,0,,{text}\n")
                        except Exception as e:
                            logging.warning(f"⚠️ Error writing grouped subtitle: {e}")
                            continue
            
            mode_text = "single word" if mode == "single" else f"{words_count} words per subtitle"
            logging.info(f"✅ Generated ASS subtitles with {mode_text} in color {subtitle_color} (size: {subtitle_size}px)")
        
        except Exception as e:
            logging.error(f"❌ ASS subtitle generation failed: {e}", exc_info=True)
            raise

    def _copy_file_safely(self, src, dst):
        """Copy file with proper error handling"""
        try:
            if not os.path.exists(src):
                raise FileNotFoundError(f"Source file not found: {src}")
            
            # Ensure destination directory exists
            dst_dir = os.path.dirname(dst)
            os.makedirs(dst_dir, exist_ok=True)
            
            shutil.copy2(src, dst)
            logging.info(f"📋 Copied original video to output: {os.path.basename(dst)}")
        except Exception as copy_error:
            logging.error(f"❌ Failed to copy video: {copy_error}")
            raise

    def run_subprocess_with_timeout(self, cmd, timeout=None, check_stop_interval=1):
        """Run subprocess with timeout and stop checking"""
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            start_time = time.time()
            while process.poll() is None:
                if self.check_stop():
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return None
                
                if timeout and (time.time() - start_time) > timeout:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    raise subprocess.TimeoutExpired(cmd, timeout)
                
                time.sleep(check_stop_interval)
            
            if process.returncode != 0:
                stderr_output = process.stderr.read()
                raise subprocess.CalledProcessError(process.returncode, cmd, stderr=stderr_output)
            
            return process
            
        except Exception as e:
            if self.check_stop():
                return None
            raise

    def add_background_music_with_ducking(self, video_path, music_path, output_path, words, volume=0.15, enable_ducking=True):
        """Add background music with improved error handling"""
        if self.check_stop(): 
            return False
        
        try:
            logging.info(f"🎵 Adding background music: {os.path.basename(music_path)}", extra={'is_status': True})
            
            # Validate input files
            for file_path, file_type in [(video_path, "Video"), (music_path, "Music")]:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"{file_type} file not found: {file_path}")

            if not enable_ducking or not words:
                logging.info("🎵 Adding music without ducking...")
                cmd = [
                    "ffmpeg", "-y", "-loglevel", "warning", "-i", video_path,
                    "-stream_loop", "-1", "-i", music_path,
                    "-filter_complex", f"[1:a]volume={volume}[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[audio_out]",
                    "-map", "0:v", "-map", "[audio_out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_path
                ]
            else:
                logging.info("🎵 Adding music with smart ducking...")
                cmd = [
                    "ffmpeg", "-y", "-loglevel", "warning", "-i", video_path,
                    "-stream_loop", "-1", "-i", music_path,
                    "-filter_complex", f"[1:a]volume={volume}[music];[0:a]asplit[original][sidechain];[music][sidechain]sidechaincompress=threshold=0.003:ratio=20:attack=5:release=50[ducked_music];[original][ducked_music]amix=inputs=2:duration=first[audio_out]",
                    "-map", "0:v", "-map", "[audio_out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_path
                ]

            process = self.run_subprocess_with_timeout(cmd, timeout=3600)  # 1 hour timeout
            
            if process is None:  # Stopped by user
                return False
            
            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logging.info(f"✅ Background music added successfully (Size: {size_mb:.1f}MB)")
                return True
            else:
                raise Exception("Output file was not created")

        except Exception as e:
            if self.check_stop(): 
                return False
            logging.warning(f"⚠️ Music processing failed: {e}. Continuing without background music.")
            try:
                self._copy_file_safely(video_path, output_path)
                return False
            except Exception as copy_error:
                logging.error(f"❌ Failed to copy video after music failure: {copy_error}")
                raise

    def merge_videos_fast(self, main_video, extra_video, output_path):
        """Merge videos with improved error handling"""
        if self.check_stop():
            return
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            concat_file = temp_dir / "concat_list.txt"
            temp_main = temp_dir / "temp_main.mp4"
            temp_extra = temp_dir / "temp_extra.mp4"

            try:
                logging.info("🔄 Preparing videos for merge...", extra={'is_status': True})

                # Normalize videos
                for input_vid, output_vid in [(main_video, temp_main), (extra_video, temp_extra)]:
                    if self.check_stop(): 
                        return
                    
                    cmd = [
                        "ffmpeg", "-y", "-loglevel", "error", "-i", str(input_vid),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k",
                        "-r", "30", "-vsync", "cfr", str(output_vid)
                    ]
                    
                    process = self.run_subprocess_with_timeout(cmd, timeout=1800)  # 30 min timeout
                    if process is None:  # Stopped by user
                        return
                    
                    if not os.path.exists(output_vid):
                        raise Exception(f"Failed to normalize video: {input_vid}")

                if self.check_stop(): 
                    return

                # Create concat file
                with open(concat_file, "w", encoding="utf-8") as f:
                    f.write(f"file '{os.path.abspath(temp_main).replace(os.sep, '/')}'\n")
                    f.write(f"file '{os.path.abspath(temp_extra).replace(os.sep, '/')}'\n")

                logging.info("🔗 Merging normalized videos...", extra={'is_status': True})
                
                # Try concat first
                cmd = [
                    "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(concat_file), "-c", "copy", "-avoid_negative_ts", "make_zero", output_path
                ]
                
                try:
                    process = self.run_subprocess_with_timeout(cmd, timeout=1800)
                    if process is None:  # Stopped by user
                        return
                    
                    if not os.path.exists(output_path):
                        raise Exception("Concat method failed")
                        
                except Exception:
                    if self.check_stop():
                        return
                    
                    logging.warning("⚠️ Fallback merge method used.")
                    cmd_fallback = [
                        "ffmpeg", "-y", "-loglevel", "error", "-i", str(temp_main), "-i", str(temp_extra),
                        "-filter_complex", "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]",
                        "-map", "[outv]", "-map", "[outa]", "-c:v", "libx264", "-preset", "fast",
                        "-c:a", "aac", "-b:a", "128k", "-avoid_negative_ts", "make_zero", output_path
                    ]
                    
                    process = self.run_subprocess_with_timeout(cmd_fallback, timeout=1800)
                    if process is None:  # Stopped by user
                        return
                    
                    if not os.path.exists(output_path):
                        raise Exception("Both merge methods failed")

                logging.info("✅ Videos merged successfully")

            except Exception as e:
                if self.check_stop(): 
                    return
                logging.error(f"❌ Video merging failed: {e}", exc_info=True)
                raise

    def process_single_video(self, input_video, output_path, extra_video, background_music,
                           quality_preset, use_gpu, music_volume, enable_ducking,
                           enable_auto_edit, subtitle_color, subtitle_mode, subtitle_size, words_count):
        """Process a single video with comprehensive error handling"""
        if self.check_stop():
            return
        
        base_name = Path(input_video).stem
        clean_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip() or f"video_{hash(base_name)}"
        
        # Use temporary directory for better cleanup
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            
            # Temporary files
            auto_edited = temp_dir / f"auto_{clean_name}.mp4"
            audio_path = temp_dir / f"audio_{clean_name}.wav"
            ass_path = temp_dir / f"subs_{clean_name}.ass"
            final_with_subs = temp_dir / f"subs_{clean_name}.mp4"
            final_with_music = temp_dir / f"music_{clean_name}.mp4"

            try:
                if self.check_stop(): 
                    return
                
                self.check_ffmpeg_availability()

                current_video_path = Path(input_video)
                
                # Auto-editing step
                if enable_auto_edit:
                    logging.info(f"✂️ Auto-editing: {os.path.basename(input_video)}", extra={'is_status': True})
                    try:
                        cmd = ["auto-editor", str(input_video), "-o", str(auto_edited), "--no-open", "--frame-rate", "30", "--silent-speed", "99999", "--video-codec", "libx264"]
                        process = self.run_subprocess_with_timeout(cmd, timeout=1800)
                        
                        if process is None:  # Stopped by user
                            return
                        
                        if os.path.exists(auto_edited):
                            logging.info("✅ Auto-editing completed.")
                            current_video_path = auto_edited
                        else:
                            raise Exception("Auto-editor did not create output file")
                            
                    except Exception as e:
                        if self.check_stop(): 
                            return
                        logging.warning(f"⚠️ Auto-editor issue: {e}. Using original video.")
                        shutil.copy2(input_video, auto_edited)
                        current_video_path = auto_edited
                else:
                    logging.info("ℹ️ Auto-editing disabled, using original video.")
                    shutil.copy2(input_video, auto_edited)
                    current_video_path = auto_edited

                if self.check_stop(): 
                    return

                # Audio extraction for transcription
                logging.info("🔊 Extracting audio for transcription...", extra={'is_status': True})
                cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(current_video_path), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(audio_path)]
                process = self.run_subprocess_with_timeout(cmd, timeout=600)
                
                if process is None:  # Stopped by user
                    return
                
                if not os.path.exists(audio_path):
                    raise Exception("Failed to extract audio")
                
                if self.check_stop(): 
                    return
                
                # Transcription
                words = self.transcribe_audio_optimized(str(audio_path))
                if self.check_stop(): 
                    return

                # Subtitle processing
                if words:
                    try:
                        self.generate_ass_subtitles(words, str(ass_path), subtitle_color, subtitle_size, subtitle_mode, words_count)
                        if self.check_stop(): 
                            return
                        
                        mode_text = "single word" if subtitle_mode == "single" else f"{words_count} words per subtitle"
                        logging.info(f"📝 Adding {mode_text} ASS subtitles (color: {subtitle_color}, size: {subtitle_size}px)...", extra={'is_status': True})
                        
                        # Escape the subtitle path for FFmpeg
                        subtitle_filter = f"ass='{str(ass_path).replace('\\', '/').replace(':', '\\:')}'"
                        ffmpeg_cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(current_video_path), "-vf", subtitle_filter]
                        
                        # GPU acceleration handling
                        if use_gpu:
                            try:
                                # Test for GPU availability
                                test_cmd = ["ffmpeg", "-f", "lavfi", "-i", "nullsrc", "-c:v", "h264_nvenc", "-t", "1", "-f", "null", "-"]
                                test_process = subprocess.run(test_cmd, capture_output=True, check=True, timeout=10)
                                ffmpeg_cmd.extend(["-c:v", "h264_nvenc", "-preset", quality_preset])
                                logging.info("🚀 Using GPU (h264_nvenc) acceleration.")
                            except Exception:
                                logging.warning("⚠️ GPU (h264_nvenc) not available, falling back to CPU (libx264).")
                                ffmpeg_cmd.extend(["-c:v", "libx264", "-preset", quality_preset, "-crf", "23"])
                        else:
                            ffmpeg_cmd.extend(["-c:v", "libx264", "-preset", quality_preset, "-crf", "23"])
                        
                        ffmpeg_cmd.extend(["-c:a", "copy", str(final_with_subs)])
                        
                        process = self.run_subprocess_with_timeout(ffmpeg_cmd, timeout=3600)
                        if process is None:  # Stopped by user
                            return
                        
                        if os.path.exists(final_with_subs):
                            current_video_path = final_with_subs
                            logging.info(f"✅ Custom {mode_text} subtitles added successfully.")
                        else:
                            raise Exception("Subtitle processing failed to create output")
                            
                    except Exception as e:
                        if self.check_stop(): 
                            return
                        logging.warning(f"⚠️ Subtitle processing failed: {e}")
                        # Continue without subtitles

                if self.check_stop(): 
                    return

                # Background music processing
                if background_music and os.path.exists(background_music):
                    success = self.add_background_music_with_ducking(str(current_video_path), background_music, str(final_with_music), words, music_volume, enable_ducking)
                    if success and not self.check_stop():
                        current_video_path = final_with_music
                else:
                    logging.info("ℹ️ No background music selected, skipping step.")

                if self.check_stop(): 
                    return

                # Video merging or final copy
                if extra_video:
                    logging.info("🔗 Merging with extra video...", extra={'is_status': True})
                    self.merge_videos_fast(str(current_video_path), extra_video, output_path)
                else:
                    logging.info("ℹ️ No extra video to merge, copying final video...", extra={'is_status': True})
                    self._copy_file_safely(str(current_video_path), output_path)

                if not self.check_stop() and os.path.exists(output_path):
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    logging.info(f"✅ Successfully completed: {os.path.basename(output_path)} ({size_mb:.1f} MB)", extra={'is_status': True})

            except Exception as e:
                if self.check_stop(): 
                    return
                logging.error(f"❌ Processing failed for {os.path.basename(input_video)}: {e}", exc_info=True)
                raise

    def process_all_videos(self, input_videos, extra_video, output_dir,
                          background_music, quality_preset, use_gpu, music_volume, enable_ducking,
                          enable_auto_edit, subtitle_color, subtitle_mode, subtitle_size, words_count):
        """Process all videos with improved error handling and progress tracking"""
        total_videos = len(input_videos)
        successful, failed = 0, []
        
        mode_text = "single word" if subtitle_mode == "single" else f"{words_count} words per subtitle"
        merge_text = "with video merging" if extra_video else "without video merging"
        
        logging.info(f"🎬 Starting batch processing of {total_videos} videos {merge_text}...", extra={'is_status': True})
        logging.info(f"   Auto-Edit: {'✅ Enabled' if enable_auto_edit else '❌ Disabled'}")
        logging.info(f"   Subtitles: {mode_text}, Color: {subtitle_color}, Size: {subtitle_size}px")
        logging.info(f"   Quality: {quality_preset}, GPU: {'✅ Enabled' if use_gpu else '❌ Disabled'}")
        logging.info(f"   Music: {'✅ Enabled' if background_music else '❌ Disabled'}, Volume: {music_volume:.2f}")

        try:
            for i, input_video in enumerate(input_videos, 1):
                if self.check_stop():
                    logging.warning(f"🛑 Processing stopped. Completed {successful}/{total_videos} videos.")
                    break
                
                try:
                    logging.info(f"--- 📹 Processing video {i}/{total_videos}: {os.path.basename(input_video)} ---", extra={'is_status': True})
                    self.update_progress((i - 1) / total_videos * 100)
                    
                    # Validate input file exists
                    if not os.path.exists(input_video):
                        raise FileNotFoundError(f"Input video not found: {input_video}")
                    
                    base_name = Path(input_video).stem
                    output_filename = f"{base_name}_processed.mp4"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # Handle existing output files
                    if os.path.exists(output_path):
                        logging.warning(f"⚠️ Output file exists, overwriting: {os.path.basename(output_path)}")
                    
                    self.process_single_video(
                        input_video, output_path, extra_video, background_music, quality_preset, use_gpu,
                        music_volume, enable_ducking, enable_auto_edit, subtitle_color, subtitle_mode, 
                        subtitle_size, words_count
                    )

                    if not self.check_stop() and os.path.exists(output_path):
                        successful += 1
                        self.update_progress(i / total_videos * 100)
                    elif not self.check_stop():
                        raise Exception("Output file was not created")
                
                except Exception as e:
                    if self.check_stop(): 
                        break
                    failed.append((input_video, str(e)))
                    logging.error(f"❌ FAILED to process {os.path.basename(input_video)}: {e}")
                    continue
            
            if not self.check_stop():
                self.update_progress(100)
            
            # Final summary
            if self.check_stop():
                logging.warning(f"🛑 Processing stopped by user. Completed: {successful}, Failed: {len(failed)}")
            else:
                logging.info(f"🏁 BATCH COMPLETE! Success: {successful}, Failed: {len(failed)}", extra={'is_status': True})
            
            if failed:
                logging.error("--- SUMMARY OF FAILED VIDEOS ---")
                for video, error in failed:
                    logging.error(f"   - {os.path.basename(video)}: {error}")
                    
        except Exception as e:
            logging.error(f"❌ Batch processing failed: {e}", exc_info=True)
            raise

def check_dependencies():
    """Check if all required dependencies are available"""
    missing = []
    
    # Check FFmpeg
    try: 
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=10)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired): 
        missing.append("FFmpeg")
    
    # Check auto-editor
    try: 
        subprocess.run(["auto-editor", "--version"], capture_output=True, check=True, timeout=10)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired): 
        missing.append("auto-editor")
    
    # Check faster-whisper
    try: 
        import faster_whisper
    except ImportError: 
        missing.append("faster-whisper (pip install faster-whisper)")
    
    return missing

def main():
    """Main application entry point"""
    # Check dependencies first
    missing_deps = check_dependencies()
    if missing_deps:
        root = tk.Tk()
        root.withdraw()
        message = "❌ Missing required dependencies:\n\n" + "\n".join(f"• {dep}" for dep in missing_deps)
        message += "\n\n📋 Installation Instructions:"
        message += "\n• FFmpeg: Download from https://ffmpeg.org/"
        message += "\n• auto-editor: pip install auto-editor"
        message += "\n• faster-whisper: pip install faster-whisper"
        message += "\n\nPlease install them and ensure they are in your system's PATH."
        messagebox.showerror("Missing Dependencies", message)
        return

    # Create main window
    root = tk.Tk()
    
    # Try to set icon if available
    try: 
        root.iconbitmap("icon.ico")
    except: 
        pass

    # Center the window on screen
    root.update_idletasks()
    width, height = 1200, 900
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Set minimum window size
    root.minsize(800, 600)
    
    # Create the main application
    try:
        app = VideoProcessorGUI(root)
    except Exception as e:
        messagebox.showerror("Initialization Error", f"Failed to initialize application: {e}")
        return

    def on_closing():
        """Handle window closing event"""
        if app.processing:
            if messagebox.askokcancel("Quit", 
                                    "⚠️ Processing is still running. Are you sure you want to quit?\n\n" +
                                    "This will stop all current processing."):
                app.stop_event.set()
                root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Start the application
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logging.info("\n🛑 Application interrupted by user.")
    except Exception as e:
        logging.critical(f"💥 A critical application error occurred: {e}", exc_info=True)
        messagebox.showerror("Critical Error", f"A critical error occurred:\n{e}\n\nPlease check the logs for more details.")

if __name__ == "__main__":
    main()