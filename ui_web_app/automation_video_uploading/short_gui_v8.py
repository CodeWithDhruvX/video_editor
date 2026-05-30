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
import random

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
            pass

# --- GUI Class ---

class VideoProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Video Processor Pro - Enhanced Edition with Mixed Fonts & Speech Recognition")
        self.root.geometry("1300x1000")
        self.root.configure(bg='#f0f0f0')

        self.input_videos = []
        self.extra_video = None
        self.background_music = None
        self.output_dir = None
        self.processing = False
        self.progress_queue = queue.Queue()
        self.stop_event = threading.Event()

        self.setup_logging()
        self.load_video_titles()
        self.setup_ui()
        self.check_progress()

    def setup_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        if logger.hasHandlers():
            logger.handlers.clear()
        gui_handler = TkinterLogHandler(self.progress_queue)
        gui_formatter = logging.Formatter("🔹 %(message)s")
        gui_handler.setFormatter(gui_formatter)
        logger.addHandler(gui_handler)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        logging.info("Logging initialized for Video Processor Pro.")

    def load_video_titles(self):
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
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill='x', padx=10, pady=10)
        title_frame.pack_propagate(False)
        title_label = tk.Label(title_frame, text="🎬 Video Processor Pro - Enhanced Edition with Mixed Fonts & Speech Recognition",
                              font=("Arial", 18, "bold"), fg='white', bg='#2c3e50')
        title_label.pack(expand=True)

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

        def _on_mousewheel(event):
            self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.main_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        config_frame = tk.LabelFrame(self.scrollable_main_frame, text="🛠️ Config Management",
                                     font=("Arial", 12, "bold"), bg='#f0f0f0', padx=15, pady=15)
        config_frame.pack(fill='x', pady=10, padx=10)

        tk.Button(config_frame, text="📤 Load Config JSON",
                  command=self.load_config, bg='#3498db', fg='white',
                  font=("Arial", 11, "bold"), padx=25, pady=8, relief='flat').pack(side='left', pady=5, padx=5)
        tk.Button(config_frame, text="💾 Save Current Config",
                  command=self.save_config, bg='#27ae60', fg='white',
                  font=("Arial", 11, "bold"), padx=25, pady=8, relief='flat').pack(side='left', pady=5, padx=5)

        files_frame = tk.LabelFrame(self.scrollable_main_frame, text="📁 File Selection",
                                   font=("Arial", 12, "bold"), bg='#f0f0f0', padx=15, pady=15)
        files_frame.pack(fill='x', pady=10, padx=10)

        tk.Button(files_frame, text="🎥 Select Main Videos",
                 command=self.select_input_videos, bg='#3498db', fg='white',
                 font=("Arial", 11, "bold"), padx=25, pady=8, relief='flat').pack(pady=5)

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

        remove_btn_frame = tk.Frame(files_frame, bg='#f0f0f0')
        remove_btn_frame.pack(pady=5)
        tk.Button(remove_btn_frame, text="🗑️ Remove Selected",
                 command=self.remove_selected_videos, bg='#e74c3c', fg='white',
                 font=("Arial", 9), padx=15, pady=5, relief='flat').pack(side='left')
        tk.Button(remove_btn_frame, text="🧹 Clear All",
                 command=self.clear_all_videos, bg='#95a5a6', fg='white',
                 font=("Arial", 9), padx=15, pady=5, relief='flat').pack(side='left', padx=(10, 0))

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
        self.clear_extra_btn = tk.Button(self.merge_options_frame, text="❌ Clear Extra Video",
                                        command=self.clear_extra_video, bg='#e74c3c', fg='white',
                                        font=("Arial", 9), padx=10, pady=5, state='disabled', relief='flat')
        self.clear_extra_btn.pack(pady=5)

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

        output_frame = tk.LabelFrame(files_frame, text="📂 Output Settings", 
                                    font=("Arial", 11, "bold"), bg='#f0f0f0', padx=10, pady=10)
        output_frame.pack(fill='x', pady=5)
        tk.Button(output_frame, text="📂 Select Output Folder",
                 command=self.select_output_dir, bg='#27ae60', fg='white',
                 font=("Arial", 10, "bold"), padx=20, pady=5, relief='flat').pack(pady=5)
        self.output_label = tk.Label(output_frame, text="No output folder selected",
                                    bg='#f0f0f0', wraplength=800, font=("Arial", 9))
        self.output_label.pack(pady=2)

        options_frame = tk.LabelFrame(self.scrollable_main_frame, text="⚙️ Processing Options",
                                     font=("Arial", 12, "bold"), bg='#f0f0f0', padx=15, pady=15)
        options_frame.pack(fill='x', pady=10, padx=10)
        options_row1 = tk.Frame(options_frame, bg='#f0f0f0')
        options_row1.pack(fill='x', padx=10, pady=8)
        quality_frame = tk.Frame(options_row1, bg='#f0f0f0')
        quality_frame.pack(side='left', padx=(0, 30))
        tk.Label(quality_frame, text="Quality Preset:", font=("Arial", 10, "bold"), bg='#f0f0f0').pack(anchor='w')
        self.quality_var = tk.StringVar(value="fast")
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_var,
                                    values=["ultrafast", "fast", "medium", "slow"],
                                    state="readonly", width=12)
        quality_combo.pack(pady=2)
        volume_frame = tk.Frame(options_row1, bg='#f0f0f0')
        volume_frame.pack(side='left')
        tk.Label(volume_frame, text="Music Volume:", font=("Arial", 10, "bold"), bg='#f0f0f0').pack(anchor='w')
        volume_control_frame = tk.Frame(volume_frame, bg='#f0f0f0')
        volume_control_frame.pack(pady=2)
        self.volume_var = tk.DoubleVar(value=0.30)
        volume_scale = tk.Scale(volume_control_frame, from_=0.0, to=0.5, resolution=0.05,
                               orient='horizontal', variable=self.volume_var, length=140)
        volume_scale.pack(side='left')
        self.volume_label = tk.Label(volume_control_frame, text="0.30", font=("Arial", 9), bg='#f0f0f0')
        self.volume_label.pack(side='left', padx=(5, 0))
        volume_scale.configure(command=lambda val: self.volume_label.config(text=f"{float(val):.2f}"))
        options_row2 = tk.Frame(options_frame, bg='#f0f0f0')
        options_row2.pack(fill='x', padx=10, pady=8)
        self.auto_edit_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_row2, text="✂️ Auto-Edit Videos (Remove Silent Parts)",
                      variable=self.auto_edit_var, bg='#f0f0f0', font=("Arial", 10, "bold")).pack(anchor='w', pady=2)
        self.gpu_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_row2, text="🚀 GPU Acceleration (NVENC if available)",
                      variable=self.gpu_var, bg='#f0f0f0', font=("Arial", 10, "bold")).pack(anchor='w', pady=2)
        self.ducking_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_row2, text="🎵 Smart Music Ducking (Lower music during speech)",
                      variable=self.ducking_var, bg='#f0f0f0', font=("Arial", 10, "bold")).pack(anchor='w', pady=2)
        self.speech_borders_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_row2, text="🗣️ Add Border Boxes to Spoken Words",
                      variable=self.speech_borders_var, bg='#f0f0f0', font=("Arial", 10, "bold")).pack(anchor='w', pady=2)

        subtitle_frame = tk.LabelFrame(self.scrollable_main_frame, text="📝 Advanced Subtitle Customization",
                                      font=("Arial", 12, "bold"), bg='#f0f0f0', padx=15, pady=15)
        subtitle_frame.pack(fill='x', pady=10, padx=10)
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
        tk.Radiobutton(mode_options_frame, text="🎨 Mixed Font Styles (Creative)", variable=self.subtitle_mode_var,
                      value="mixed", bg='#f0f0f0', font=("Arial", 10),
                      command=self.toggle_word_count).pack(anchor='w', pady=2)
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
        words_scale.configure(command=lambda val: self.words_count_label.config(text=f"{int(float(val))} words per group"))
        self.mixed_font_frame = tk.LabelFrame(subtitle_frame, text="🎨 Mixed Font Styles Configuration", 
                                             font=("Arial", 11, "bold"), bg='#f0f0f0', padx=10, pady=10)
        self.mixed_font_frame.pack(fill='x', padx=10, pady=8)
        font_options_row1 = tk.Frame(self.mixed_font_frame, bg='#f0f0f0')
        font_options_row1.pack(fill='x', pady=5)
        self.enable_random_fonts_var = tk.BooleanVar(value=True)
        tk.Checkbutton(font_options_row1, text="🔀 Random Font Families", 
                      variable=self.enable_random_fonts_var, bg='#f0f0f0', font=("Arial", 10)).pack(anchor='w')
        self.enable_random_colors_var = tk.BooleanVar(value=True)
        tk.Checkbutton(font_options_row1, text="🌈 Random Colors", 
                      variable=self.enable_random_colors_var, bg='#f0f0f0', font=("Arial", 10)).pack(anchor='w')
        self.enable_random_sizes_var = tk.BooleanVar(value=True)
        tk.Checkbutton(font_options_row1, text="📏 Random Sizes", 
                      variable=self.enable_random_sizes_var, bg='#f0f0f0', font=("Arial", 10)).pack(anchor='w')
        self.enable_effects_var = tk.BooleanVar(value=True)
        tk.Checkbutton(font_options_row1, text="✨ Special Effects (Bold, Italic)", 
                      variable=self.enable_effects_var, bg='#f0f0f0', font=("Arial", 10)).pack(anchor='w')
        border_frame = tk.LabelFrame(subtitle_frame, text="📦 Speech Border Box Settings", 
                                    font=("Arial", 11, "bold"), bg='#f0f0f0', padx=10, pady=10)
        border_frame.pack(fill='x', padx=10, pady=8)
        border_row1 = tk.Frame(border_frame, bg='#f0f0f0')
        border_row1.pack(fill='x', pady=5)
        tk.Label(border_row1, text="Border Thickness:", font=("Arial", 10, "bold"), bg='#f0f0f0').pack(side='left')
        self.border_thickness_var = tk.IntVar(value=3)
        border_scale = tk.Scale(border_row1, from_=1, to=8, resolution=1,
                               orient='horizontal', variable=self.border_thickness_var, length=120)
        border_scale.pack(side='left', padx=(10, 5))
        tk.Label(border_row1, text="Border Color:", font=("Arial", 10, "bold"), bg='#f0f0f0').pack(side='left', padx=(20, 5))
        self.border_color = "#000000"
        self.border_preview = tk.Label(border_row1, text="  ", bg=self.border_color,
                                      relief='solid', borderwidth=2, width=4, height=1, cursor='hand2')
        self.border_preview.pack(side='left', padx=(0, 5))
        self.border_preview.bind("<Button-1>", lambda e: self.pick_border_color())
        tk.Button(border_row1, text="🎨", command=self.pick_border_color,
                 bg='#34495e', fg='white', font=("Arial", 8), relief='flat').pack(side='left')
        appearance_row = tk.Frame(subtitle_frame, bg='#f0f0f0')
        appearance_row.pack(fill='x', padx=10, pady=8)
        size_frame = tk.Frame(appearance_row, bg='#f0f0f0')
        size_frame.pack(side='left', padx=(0, 30))
        tk.Label(size_frame, text="Base Subtitle Size (pixels):", font=("Arial", 10, "bold"), bg='#f0f0f0').pack(anchor='w')
        self.subtitle_size_var = tk.IntVar(value=24)
        size_scale = tk.Scale(size_frame, from_=12, to=48, resolution=2,
                             orient='horizontal', variable=self.subtitle_size_var, length=180)
        size_scale.pack(side='left')
        self.size_label = tk.Label(size_frame, text="24px", font=("Arial", 10, "bold"), 
                                  bg='#f0f0f0', fg='#2c3e50')
        self.size_label.pack(side='left', padx=(8, 0))
        size_scale.configure(command=lambda val: self.size_label.config(text=f"{int(float(val))}px"))
        color_frame = tk.Frame(appearance_row, bg='#f0f0f0')
        color_frame.pack(side='left')
        tk.Label(color_frame, text="Base Subtitle Color:", font=("Arial", 10, "bold"), bg='#f0f0f0').pack(anchor='w')
        color_control_frame = tk.Frame(color_frame, bg='#f0f0f0')
        color_control_frame.pack(pady=2)
        self.subtitle_color = "#FFFFFF"
        self.color_preview = tk.Label(color_control_frame, text="    ", bg=self.subtitle_color,
                                     relief='solid', borderwidth=2, width=6, height=2, cursor='hand2')
        self.color_preview.pack(side='left', padx=(0, 8))
        self.color_preview.bind("<Button-1>", lambda e: self.pick_subtitle_color())
        color_input_frame = tk.Frame(color_control_frame, bg='#f0f0f0')
        color_input_frame.pack(side='left')
        tk.Button(color_input_frame, text="🎨 Pick Color", command=self.pick_subtitle_color,
                 bg='#f39c12', fg='white', font=("Arial", 9), relief='flat').pack(pady=(0, 2))
        hex_frame = tk.Frame(color_input_frame, bg='#f0f0f0')
        hex_frame.pack()
        tk.Label(hex_frame, text="Hex:", font=("Arial", 9), bg='#f0f0f0').pack(side='left')
        self.hex_var = tk.StringVar(value=self.subtitle_color)
        self.hex_entry = tk.Entry(hex_frame, textvariable=self.hex_var, width=8, font=("Arial", 9))
        self.hex_entry.pack(side='left', padx=2)
        self.hex_entry.bind('<KeyRelease>', self.on_hex_change)
        tk.Button(hex_frame, text="Apply", command=self.apply_hex_color,
                 bg='#27ae60', fg='white', font=("Arial", 8), relief='flat').pack(side='left', padx=(2, 0))

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
        for color, name in preset_colors:
            btn = tk.Button(preset_colors_frame, text="  ", bg=color, width=4, height=2,
                           relief='solid', borderwidth=1, cursor='hand2',
                           command=lambda c=color: self.set_subtitle_color(c))
            btn.pack(side='left', padx=2)
            self.create_tooltip(btn, name)
        self.toggle_word_count()
        button_frame = tk.Frame(self.scrollable_main_frame, bg='#f0f0f0')
        button_frame.pack(pady=25)
        self.process_btn = tk.Button(button_frame, text="🚀 START PROCESSING",
                                    command=self.start_processing, bg='#e74c3c', fg='white',
                                    font=("Arial", 14, "bold"), pady=12, padx=30, relief='flat',
                                    cursor='hand2')
        self.process_btn.pack(side='left', padx=(0, 15))
        self.stop_btn = tk.Button(button_frame, text="⏹️ STOP PROCESSING",
                                 command=self.stop_processing, bg='#e67e22', fg='white',
                                 font=("Arial", 14, "bold"), pady=12, padx=30, state='disabled',
                                 relief='flat', cursor='hand2')
        self.stop_btn.pack(side='left')
        progress_frame = tk.LabelFrame(self.scrollable_main_frame, text="📊 Processing Progress & Logs",
                                      font=("Arial", 12, "bold"), bg='#f0f0f0', padx=15, pady=15)
        progress_frame.pack(fill='both', expand=True, pady=10, padx=10)
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
        log_frame = tk.Frame(progress_frame, bg='#f0f0f0')
        log_frame.pack(fill='both', expand=True, padx=5, pady=5)
        self.log_text = tk.Text(log_frame, height=10, bg='#2c3e50', fg='#ecf0f1',
                               font=("Consolas", 9), wrap=tk.WORD, state=tk.DISABLED)
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        log_control_frame = tk.Frame(progress_frame, bg='#f0f0f0')
        log_control_frame.pack(pady=5)
        tk.Button(log_control_frame, text="🧹 Clear Logs", command=self.clear_logs,
                 bg='#95a5a6', fg='white', font=("Arial", 9), padx=15, pady=5, relief='flat').pack(side='left')
        tk.Button(log_control_frame, text="💾 Save Logs", command=self.save_logs,
                 bg='#3498db', fg='white', font=("Arial", 9), padx=15, pady=5, relief='flat').pack(side='left', padx=(10, 0))

    def create_tooltip(self, widget, text):
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
        selected_indices = self.input_listbox.curselection()
        if selected_indices:
            for index in reversed(selected_indices):
                if 0 <= index < len(self.input_videos):
                    del self.input_videos[index]
            self.update_input_listbox()
        else:
            messagebox.showinfo("No Selection", "Please select videos to remove from the list.")

    def clear_all_videos(self):
        if self.input_videos and messagebox.askquestion("Clear All", 
                                                        "Are you sure you want to clear all selected videos?") == 'yes':
            self.input_videos.clear()
            self.update_input_listbox()

    def update_input_listbox(self):
        self.input_listbox.delete(0, tk.END)
        for video in self.input_videos:
            filename = os.path.basename(video)
            try:
                if os.path.exists(video):
                    size_mb = os.path.getsize(video) / (1024 * 1024)
                    self.input_listbox.insert(tk.END, f"{filename} ({size_mb:.1f} MB)")
                else:
                    self.input_listbox.insert(tk.END, f"{filename} (File not found)")
            except Exception:
                self.input_listbox.insert(tk.END, filename)

    def clear_extra_video(self):
        self.extra_video = None
        self.extra_label.config(text="No extra video selected")

    def clear_logs(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def save_logs(self):
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
        enabled = self.enable_merge_var.get()
        state = 'normal' if enabled else 'disabled'
        self.select_extra_btn.config(state=state)
        self.clear_extra_btn.config(state=state)
        self.extra_label.config(fg='black' if enabled else 'gray')
        if not enabled:
            self.clear_extra_video()

    def toggle_word_count(self):
        mode = self.subtitle_mode_var.get()
        if mode == "multiple" or mode == "mixed":
            self.words_count_frame.pack(fill='x', padx=10, pady=8)
            if mode == "mixed":
                self.mixed_font_frame.pack(fill='x', padx=10, pady=8)
            else:
                self.mixed_font_frame.pack_forget()
        else:
            self.words_count_frame.pack_forget()
            self.mixed_font_frame.pack_forget()

    def pick_subtitle_color(self):
        color = colorchooser.askcolor(title="Choose Subtitle Color",
                                     initialcolor=self.subtitle_color)
        if color[1]:
            self.set_subtitle_color(color[1])

    def pick_border_color(self):
        color = colorchooser.askcolor(title="Choose Border Color",
                                     initialcolor=self.border_color)
        if color[1]:
            self.border_color = color[1].upper()
            self.border_preview.config(bg=self.border_color)

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
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
            self.root.update_idletasks()
        except Exception:
            pass

    def select_input_videos(self):
        files = filedialog.askopenfilenames(
            title="Select Main Input Videos",
            filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi *.m4v *.wmv *.flv")]
        )
        if files:
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
        if not self.input_videos:
            messagebox.showerror("Error", "Please select main input videos")
            return False
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
            subtitle_settings = {
                'color': self.subtitle_color,
                'mode': self.subtitle_mode_var.get(),
                'size': self.subtitle_size_var.get(),
                'words_count': self.words_count_var.get(),
                'enable_borders': self.speech_borders_var.get(),
                'border_color': self.border_color,
                'border_thickness': self.border_thickness_var.get(),
                'mixed_font_settings': {
                    'enable_random_fonts': self.enable_random_fonts_var.get(),
                    'enable_random_colors': self.enable_random_colors_var.get(),
                    'enable_random_sizes': self.enable_random_sizes_var.get(),
                    'enable_effects': self.enable_effects_var.get()
                }
            }
            processor.process_all_videos(
                self.input_videos, self.extra_video if self.enable_merge_var.get() else None, 
                self.output_dir, self.background_music, self.quality_var.get(), self.gpu_var.get(), 
                self.volume_var.get(), self.ducking_var.get(), self.auto_edit_var.get(), 
                subtitle_settings
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

    def load_config(self):
        file = filedialog.askopenfilename(
            title="Select Config JSON",
            filetypes=[("JSON Files", "*.json")]
        )
        if not file:
            return
        try:
            with open(file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.input_videos = config.get('input_videos', [])
            self.update_input_listbox()
            
            self.extra_video = config.get('extra_video')
            self.extra_label.config(text=f"Extra video: {os.path.basename(self.extra_video)}" if self.extra_video else "No extra video selected")
            
            self.background_music = config.get('background_music')
            self.music_label.config(text=f"Background music: {os.path.basename(self.background_music)}" if self.background_music else "No background music selected")
            
            self.output_dir = config.get('output_dir')
            self.output_label.config(text=f"Output folder: {self.output_dir}" if self.output_dir else "No output folder selected")
            
            self.quality_var.set(config.get('quality_preset', 'fast'))
            self.volume_var.set(config.get('music_volume', 0.30))
            self.auto_edit_var.set(config.get('enable_auto_edit', False))
            self.gpu_var.set(config.get('enable_gpu', True))
            self.ducking_var.set(config.get('enable_ducking', True))
            self.speech_borders_var.set(config.get('enable_speech_borders', True))
            self.subtitle_mode_var.set(config.get('subtitle_mode', 'mixed'))
            self.words_count_var.set(config.get('words_count', 3))
            mixed_settings = config.get('mixed_font_settings', {})
            self.enable_random_fonts_var.set(mixed_settings.get('enable_random_fonts', True))
            self.enable_random_colors_var.set(mixed_settings.get('enable_random_colors', True))
            self.enable_random_sizes_var.set(mixed_settings.get('enable_random_sizes', True))
            self.enable_effects_var.set(mixed_settings.get('enable_effects', True))
            self.border_thickness_var.set(config.get('border_thickness', 3))
            self.border_color = config.get('border_color', '#000000')
            self.border_preview.config(bg=self.border_color)
            self.subtitle_size_var.set(config.get('subtitle_size', 24))
            self.subtitle_color = config.get('subtitle_color', '#FFFFFF')
            self.color_preview.config(bg=self.subtitle_color)
            self.hex_var.set(self.subtitle_color)
            self.enable_merge_var.set(config.get('enable_merge', False))
            
            self.toggle_merge_options()
            self.toggle_word_count()
            
            messagebox.showinfo("Success", "Config loaded successfully! You can now start processing.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {str(e)}")

    def save_config(self):
        config = {
            "input_videos": self.input_videos,
            "extra_video": self.extra_video,
            "background_music": self.background_music,
            "output_dir": self.output_dir,
            "quality_preset": self.quality_var.get(),
            "music_volume": self.volume_var.get(),
            "enable_auto_edit": self.auto_edit_var.get(),
            "enable_gpu": self.gpu_var.get(),
            "enable_ducking": self.ducking_var.get(),
            "enable_speech_borders": self.speech_borders_var.get(),
            "subtitle_mode": self.subtitle_mode_var.get(),
            "words_count": self.words_count_var.get(),
            "mixed_font_settings": {
                "enable_random_fonts": self.enable_random_fonts_var.get(),
                "enable_random_colors": self.enable_random_colors_var.get(),
                "enable_random_sizes": self.enable_random_sizes_var.get(),
                "enable_effects": self.enable_effects_var.get()
            },
            "border_thickness": self.border_thickness_var.get(),
            "border_color": self.border_color,
            "subtitle_size": self.subtitle_size_var.get(),
            "subtitle_color": self.subtitle_color,
            "enable_merge": self.enable_merge_var.get()
        }
        file = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            title="Save Config JSON"
        )
        if file:
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Success", f"Config saved to: {file}")

# --- Video Processing Class ---

class OptimizedVideoProcessor:
    def __init__(self, progress_queue, video_title_map, stop_event):
        self.progress_queue = progress_queue
        self.video_title_map = video_title_map
        self.whisper_model = None
        self.stop_event = stop_event
        self.font_families = [
            "Impact", "Arial Black", "Comic Sans MS", "Times New Roman",
            "Courier New", "Georgia", "Verdana", "Trebuchet MS",
            "Lucida Console", "Palatino Linotype", "Book Antiqua", "Franklin Gothic Medium"
        ]
        self.color_palette = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
            "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
            "#F8C471", "#82E0AA", "#F1948A", "#85929E", "#D5DBDB"
        ]

    def update_progress(self, percentage):
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
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"&H00{b:02X}{g:02X}{r:02X}"
        except Exception:
            return "&H00FFFFFF"

    def format_ass_time(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds * 100) % 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def generate_mixed_font_styles(self, words, settings):
        styled_words = []
        for i, word_data in enumerate(words):
            word = word_data.get("word", "").strip().upper()
            if not word:
                continue
            style_tags = ""
            if settings['mixed_font_settings']['enable_random_fonts']:
                font = random.choice(self.font_families)
                style_tags += f"{{\\fn{font}}}"
            if settings['mixed_font_settings']['enable_random_colors']:
                color = random.choice(self.color_palette)
                ass_color = self.hex_to_ass_color(color)
                style_tags += f"{{\\c{ass_color}}}"
            if settings['mixed_font_settings']['enable_random_sizes']:
                base_size = settings['size']
                size_variation = random.randint(-8, 12)
                new_size = max(12, base_size + size_variation)
                style_tags += f"{{\\fs{new_size}}}"
            if settings['mixed_font_settings']['enable_effects']:
                if random.random() < 0.3:
                    style_tags += "{\\b1}"
                if random.random() < 0.2:
                    style_tags += "{\\i1}"
                if random.random() < 0.1:
                    style_tags += "{\\u1}"
            if settings['enable_borders']:
                border_color = self.hex_to_ass_color(settings['border_color'])
                thickness = settings['border_thickness']
                style_tags += f"{{\\3c{border_color}\\bord{thickness}}}"
            styled_word = {
                "word": word,
                "start": word_data["start"],
                "end": word_data["end"],
                "style": style_tags
            }
            styled_words.append(styled_word)
        return styled_words

    def generate_ass_subtitles_enhanced(self, content, ass_path, settings):
        if self.check_stop():
            return
        try:
            mode = settings['mode']
            subtitle_color = settings['color']
            subtitle_size = settings['size']
            words_count = settings['words_count']
            base_ass_color = self.hex_to_ass_color(subtitle_color)
            border_settings = ""
            if settings['enable_borders']:
                border_color = self.hex_to_ass_color(settings['border_color'])
                thickness = settings['border_thickness']
                border_settings = f",BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Default,Impact,{subtitle_size},{base_ass_color},{border_color},-1,0,0,0,100,100,0,0,1,{thickness},1,2,10,10,90,1"
                border_settings += f"\nStyle: SpeechBorder,Impact,{subtitle_size + 2},{base_ass_color},{border_color},-1,0,0,0,100,100,0,0,1,{thickness + 1},2,2,10,10,90,1"
            else:
                border_settings = f",BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Default,Impact,{subtitle_size},{base_ass_color},&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,90,1"
            with open(ass_path, "w", encoding="utf-8") as f:
                f.write(f"""[Script Info]
Title: Enhanced Subtitles with Mixed Fonts and Speech Recognition
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour{border_settings}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
                if mode == "mixed":
                    styled_words = self.generate_mixed_font_styles(content, settings)
                    if words_count > 1:
                        for i in range(0, len(styled_words), words_count):
                            if self.check_stop():
                                break
                            group = styled_words[i:i + words_count]
                            if group:
                                start_time = group[0]["start"]
                                end_time = group[-1]["end"]
                                combined_text = ""
                                for word_data in group:
                                    combined_text += f"{word_data['style']}{word_data['word']} "
                                combined_text = combined_text.strip()
                                style_name = "SpeechBorder" if settings['enable_borders'] else "Default"
                                f.write(f"Dialogue: 0,{self.format_ass_time(start_time)},{self.format_ass_time(end_time)},{style_name},,0,0,0,,{combined_text}\n")
                    else:
                        for word_data in styled_words:
                            if self.check_stop():
                                break
                            style_name = "SpeechBorder" if settings['enable_borders'] else "Default"
                            styled_text = f"{word_data['style']}{word_data['word']}"
                            f.write(f"Dialogue: 0,{self.format_ass_time(word_data['start'])},{self.format_ass_time(word_data['end'])},{style_name},,0,0,0,,{styled_text}\n")
                elif mode == "single":
                    for w in content:
                        if self.check_stop():
                            break
                        try:
                            word = w.get("word", "").strip().upper()
                            start, end = w.get("start", 0), w.get("end", 0)
                            if word and end > start:
                                style_name = "SpeechBorder" if settings['enable_borders'] else "Default"
                                f.write(f"Dialogue: 0,{self.format_ass_time(start)},{self.format_ass_time(end)},{style_name},,0,0,0,,{word}\n")
                        except Exception as e:
                            logging.warning(f"⚠️ Error writing subtitle: {e}")
                            continue
                else:
                    grouped_subs = self.generate_grouped_subtitles(content, words_count)
                    for sub in grouped_subs:
                        if self.check_stop():
                            break
                        try:
                            text = sub.get("text", "").strip().upper()
                            start, end = sub.get("start", 0), sub.get("end", 0)
                            if text and end > start:
                                style_name = "SpeechBorder" if settings['enable_borders'] else "Default"
                                f.write(f"Dialogue: 0,{self.format_ass_time(start)},{self.format_ass_time(end)},{style_name},,0,0,0,,{text}\n")
                        except Exception as e:
                            logging.warning(f"⚠️ Error writing grouped subtitle: {e}")
                            continue
            mode_text = {"single": "single word", "multiple": f"{words_count} words per subtitle", "mixed": "mixed font styles"}[mode]
            border_text = " with speech border boxes" if settings['enable_borders'] else ""
            logging.info(f"✅ Generated enhanced ASS subtitles with {mode_text}{border_text}")
        except Exception as e:
            logging.error(f"❌ Enhanced ASS subtitle generation failed: {e}", exc_info=True)
            raise

    def check_ffmpeg_availability(self):
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
                                "start": max(0, w.start),
                                "end": max(w.start, w.end),
                                "confidence": getattr(w, 'probability', 0.5)
                            })
            logging.info(f"✅ Transcribed {len(words)} words with speech recognition confidence")
            return words
        except Exception as e:
            logging.error(f"❌ Transcription failed: {e}", exc_info=True)
            return []

    def generate_grouped_subtitles(self, words, words_per_group):
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
                    avg_confidence = sum(w.get("confidence", 0.5) for w in group) / len(group)
                    if end_time > start_time and text.strip():
                        grouped_subtitles.append({
                            "text": text.strip().upper(),
                            "start": start_time,
                            "end": end_time,
                            "confidence": avg_confidence
                        })
                except Exception as e:
                    logging.warning(f"⚠️ Error grouping subtitle segment: {e}")
                    continue
        return grouped_subtitles

    def _copy_file_safely(self, src, dst):
        try:
            if not os.path.exists(src):
                raise FileNotFoundError(f"Source file not found: {src}")
            dst_dir = os.path.dirname(dst)
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(src, dst)
            logging.info(f"📋 Copied original video to output: {os.path.basename(dst)}")
        except Exception as copy_error:
            logging.error(f"❌ Failed to copy video: {copy_error}")
            raise

    def run_subprocess_with_timeout(self, cmd, timeout=None, check_stop_interval=1):
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
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd, output=stdout, stderr=stderr)
            return process
        except Exception as e:
            if self.check_stop():
                return None
            raise

    def add_background_music_with_ducking(self, video_path, music_path, output_path, words, volume=0.15, enable_ducking=True):
        if self.check_stop():
            return False
        try:
            logging.info(f"🎵 Adding background music: {os.path.basename(music_path)}", extra={'is_status': True})
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
                logging.info("🎵 Adding music with smart ducking based on speech recognition...")
                cmd = [
                    "ffmpeg", "-y", "-loglevel", "warning", "-i", video_path,
                    "-stream_loop", "-1", "-i", music_path,
                    "-filter_complex", f"[1:a]volume={volume}[music];[0:a]asplit[original][sidechain];[music][sidechain]sidechaincompress=threshold=0.003:ratio=20:attack=5:release=50[ducked_music];[original][ducked_music]amix=inputs=2:duration=first[audio_out]",
                    "-map", "0:v", "-map", "[audio_out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_path
                ]
            process = self.run_subprocess_with_timeout(cmd, timeout=3600)
            if process is None:
                return False
            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logging.info(f"✅ Background music added successfully with speech-aware ducking (Size: {size_mb:.1f}MB)")
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
        if self.check_stop():
            return
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            concat_file = temp_dir / "concat_list.txt"
            temp_main = temp_dir / "temp_main.mp4"
            temp_extra = temp_dir / "temp_extra.mp4"
            try:
                logging.info("🔄 Preparing videos for merge...", extra={'is_status': True})
                for input_vid, output_vid in [(main_video, temp_main), (extra_video, temp_extra)]:
                    if self.check_stop():
                        return
                    cmd = [
                        "ffmpeg", "-y", "-loglevel", "error", "-i", str(input_vid),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k",
                        "-r", "30", "-vsync", "cfr", str(output_vid)
                    ]
                    process = self.run_subprocess_with_timeout(cmd, timeout=1800)
                    if process is None:
                        return
                    if not os.path.exists(output_vid):
                        raise Exception(f"Failed to normalize video: {input_vid}")
                if self.check_stop():
                    return
                with open(concat_file, "w", encoding="utf-8") as f:
                    f.write(f"file '{os.path.abspath(temp_main).replace(os.sep, '/')}'\n")
                    f.write(f"file '{os.path.abspath(temp_extra).replace(os.sep, '/')}'\n")
                logging.info("🔗 Merging normalized videos...", extra={'is_status': True})
                cmd = [
                    "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(concat_file), "-c", "copy", "-avoid_negative_ts", "make_zero", output_path
                ]
                try:
                    process = self.run_subprocess_with_timeout(cmd, timeout=1800)
                    if process is None:
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
                    if process is None:
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
                        enable_auto_edit, subtitle_settings):
        if self.check_stop():
            return
        base_name = Path(input_video).stem
        clean_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip() or f"video_{hash(base_name)}"
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            auto_edited = temp_dir / f"auto_{clean_name}.mp4"
            audio_path = temp_dir / f"audio_{clean_name}.wav"
            ass_path = temp_dir / f"subs_{clean_name}.ass"
            final_with_subs = temp_dir / f"subs_{clean_name}.mp4"
            final_with_music = temp_dir / f"music_{clean_name}.mp4"
            merged_output = temp_dir / f"merged_{clean_name}.mp4"
            try:
                if self.check_stop():
                    return
                self.check_ffmpeg_availability()
                current_video_path = Path(input_video)

                # --------------------------
                # AUTO-EDITOR PART UPDATED
                # --------------------------
                if enable_auto_edit:
                    logging.info(f"✂️ Auto-editing: {os.path.basename(input_video)}", extra={'is_status': True})
                    try:
                        cmd = [
                            "auto-editor", str(input_video),
                            "--output", str(auto_edited),
                            "--frame-rate", "30",
                            "--silent-speed", "99999",
                            "--video-codec", "libx264",
                            "--margin", "0.2s",
                            "--progress", "ascii",
                            "--no-open"  # 🚀 prevent auto-opening
                        ]


                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1
                        )

                        start = time.time()
                        for line in process.stdout:
                            logging.info(f"[auto-editor] {line.strip()}")
                            if self.check_stop():
                                process.kill()
                                return
                            if time.time() - start > 1800:  # 30 min timeout
                                process.kill()
                                raise TimeoutError("auto-editor took too long")

                        process.wait()
                        if process.returncode == 0 and os.path.exists(auto_edited):
                            logging.info("✅ Auto-editing completed successfully.")
                            current_video_path = auto_edited
                        else:
                            raise Exception("Auto-editor failed or did not create output file")

                    except Exception as e:
                        if self.check_stop():
                            return
                        logging.warning(f"⚠️ Auto-editor issue: {e}. Using original video.")
                        try:
                            self._copy_file_safely(input_video, auto_edited)
                            current_video_path = auto_edited
                        except Exception as copy_error:
                            logging.error(f"❌ Failed to copy video after auto-editor failure: {copy_error}")
                            raise
                else:
                    logging.info("ℹ️ Auto-editing disabled, using original video.")
                    try:
                        self._copy_file_safely(input_video, auto_edited)
                        current_video_path = auto_edited
                    except Exception as copy_error:
                        logging.error(f"❌ Failed to copy original video: {copy_error}")
                        raise

                # --------------------------
                # REST OF YOUR PIPELINE
                # --------------------------
                if self.check_stop():
                    return
                logging.info("🔊 Extracting audio for transcription...", extra={'is_status': True})
                cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(current_video_path), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(audio_path)]
                process = self.run_subprocess_with_timeout(cmd, timeout=600)
                if process is None:
                    return
                if not os.path.exists(audio_path):
                    raise Exception("Failed to extract audio")

                if self.check_stop():
                    return
                logging.info("🧠 Performing enhanced speech recognition...", extra={'is_status': True})
                words = self.transcribe_audio_optimized(str(audio_path))

                if self.check_stop():
                    return
                if words:
                    try:
                        self.generate_ass_subtitles_enhanced(words, str(ass_path), subtitle_settings)
                        if self.check_stop():
                            return
                        mode_text = {
                            "single": "single word",
                            "multiple": f"{subtitle_settings['words_count']} words per subtitle",
                            "mixed": "mixed font styles with creative effects"
                        }[subtitle_settings['mode']]
                        border_text = " with speech recognition border boxes" if subtitle_settings['enable_borders'] else ""
                        logging.info(f"📝 Adding {mode_text} enhanced subtitles{border_text}...", extra={'is_status': True})
                        subtitle_filter = f"ass='{str(ass_path).replace('\\', '/').replace(':', '\\:')}'"
                        ffmpeg_cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(current_video_path), "-vf", subtitle_filter]
                        if use_gpu:
                            try:
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
                        if process is None:
                            return
                        if os.path.exists(final_with_subs):
                            current_video_path = final_with_subs
                            logging.info(f"✅ Enhanced {mode_text} subtitles with speech recognition added successfully.")
                        else:
                            raise Exception("Failed to add subtitles")
                    except Exception as e:
                        if self.check_stop():
                            return
                        logging.warning(f"⚠️ Subtitle addition failed: {e}. Continuing without subtitles.")
                        try:
                            self._copy_file_safely(current_video_path, final_with_subs)
                            current_video_path = final_with_subs
                        except Exception as copy_error:
                            logging.error(f"❌ Failed to copy video after subtitle failure: {copy_error}")
                            raise
                else:
                    logging.info("ℹ️ No speech words detected, skipping subtitle generation.")
                    try:
                        self._copy_file_safely(current_video_path, final_with_subs)
                        current_video_path = final_with_subs
                    except Exception as copy_error:
                        logging.error(f"❌ Failed to copy video without subtitles: {copy_error}")
                        raise

                if self.check_stop():
                    return
                if background_music:
                    success_music = self.add_background_music_with_ducking(
                        str(current_video_path), background_music, str(final_with_music),
                        words, volume=music_volume, enable_ducking=enable_ducking
                    )
                    if success_music:
                        current_video_path = final_with_music
                    else:
                        logging.info("ℹ️ Proceeding without background music.")
                else:
                    logging.info("ℹ️ No background music selected, skipping music addition.")

                if self.check_stop():
                    return
                if extra_video:
                    self.merge_videos_fast(str(current_video_path), extra_video, output_path)
                else:
                    shutil.copy2(current_video_path, output_path)
                    logging.info(f"📁 Saved processed video: {output_path}")
            except Exception as e:
                logging.error(f"❌ Processing failed for {input_video}: {e}", exc_info=True)
                raise

    def process_all_videos(self, input_videos, extra_video, output_dir, background_music,
                           quality_preset, use_gpu, music_volume, enable_ducking,
                           enable_auto_edit, subtitle_settings):
        total = len(input_videos)
        for idx, input_video in enumerate(input_videos, start=1):
            if self.check_stop():
                break
            filename = Path(input_video).stem
            output_path = Path(output_dir) / f"{filename}_processed.mp4"
            logging.info(f"▶️ Processing [{idx}/{total}]: {input_video}", extra={'is_status': True})
            try:
                self.process_single_video(
                    input_video, str(output_path), extra_video, background_music,
                    quality_preset, use_gpu, music_volume, enable_ducking,
                    enable_auto_edit, subtitle_settings
                )
                progress_percent = int((idx / total) * 100)
                self.update_progress(progress_percent)
            except Exception:
                logging.error(f"❌ Skipping video due to error: {input_video}")
                continue
        self.update_progress(100)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoProcessorGUI(root)
    root.mainloop()
