import sys
import os
import re

# Fix for compiled executable - set working directory
if getattr(sys, 'frozen', False) or '__compiled__' in globals():
    application_path = os.path.dirname(sys.executable)
    os.chdir(application_path)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import numpy as np
from sklearn.cluster import KMeans
from collections import defaultdict, Counter
import cv2
from scipy import ndimage
import json
import random
import time
from datetime import datetime


# Set appearance and theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ColorByNumberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎨 Happy Coloring - Color by Number Pro")
        self.root.geometry("1600x1000")
        
        # Theme colors
        self.colors = {
            'bg_dark': '#1a1a2e',
            'bg_medium': '#16213e',
            'bg_light': '#0f3460',
            'accent': '#e94560',
            'accent2': '#00d9ff',
            'text': '#ffffff',
            'text_dim': '#a0a0a0',
            'success': '#00ff88',
            'warning': '#ffaa00',
            'error': '#ff4444',
            'card': '#252542'
        }

        # App state
        self.original_image = None
        self.processed_image = None
        self.template_image = None
        self.display_image = None
        self.color_palette = {}
        self.original_colors = {}
        self.regions = None
        self.region_labels = None
        self.colored_regions = {}
        self.selected_color_num = None
        self.zoom_level = 1.0
        self.pan_offset = [0, 0]
        self.history = []
        self.history_index = -1
        self.num_colors = 10

        # View mode
        self.view_mode = ctk.StringVar(value="template")

        # Animation state
        self.is_animating = False
        self.animation_speed = 200
        self.animation_paused = False
        self.animation_order = "random"

        # Recording state
        self.is_recording = False
        self.recorded_frames = []
        self.record_fps = 10
        self.record_start_time = None

        # Recording output options
        self.rec_resolution_var = ctk.StringVar(value="Original")
        self.rec_quality_var = ctk.StringVar(value="High")

        # Canvas drag state
        self.drag_start = None
        self.is_panning = False

        # Color matching options
        self.use_exact_colors = ctk.BooleanVar(value=True)
        self.fill_micro_holes = ctk.BooleanVar(value=True)
        self.min_region_size = ctk.IntVar(value=30)

        # Slider variables
        self.color_count_var = ctk.IntVar(value=10)
        self.speed_var = ctk.IntVar(value=200)
        self.fps_var = ctk.IntVar(value=10)
        self.order_var = ctk.StringVar(value="random")
        self.progress_var = ctk.DoubleVar(value=0)

        self.setup_ui()
        self.setup_bindings()

    def setup_ui(self):
        # Main container
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.setup_left_panel()
        self.setup_center_panel()
        self.setup_right_panel()
        self.setup_status_bar()

    def setup_left_panel(self):
        # Left panel with scrollable frame
        self.left_panel = ctk.CTkFrame(self.main_frame, width=320, corner_radius=15)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self.left_panel.pack_propagate(False)

        # Scrollable container
        self.left_scrollable = ctk.CTkScrollableFrame(
            self.left_panel, 
            width=290,
            fg_color="transparent"
        )
        self.left_scrollable.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Header
        header_frame = ctk.CTkFrame(self.left_scrollable, fg_color="transparent")
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        ctk.CTkLabel(
            header_frame, 
            text="🎨 Color by Number",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors['accent']
        ).pack()
        
        ctk.CTkLabel(
            header_frame,
            text="Professional Edition",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_dim']
        ).pack()

        self.setup_file_section()
        self.setup_settings_section()
        self.setup_advanced_section()
        self.setup_animation_section()
        self.setup_recording_section()
        self.setup_tools_section()
        self.setup_view_section()

    def create_section_frame(self, parent, title, icon=""):
        """Create a styled section frame with title"""
        frame = ctk.CTkFrame(parent, corner_radius=10, fg_color=self.colors['card'])
        frame.pack(fill=tk.X, pady=8, padx=2)
        
        # Title bar
        title_frame = ctk.CTkFrame(frame, fg_color="transparent")
        title_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            title_frame,
            text=f"{icon} {title}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors['accent2']
        ).pack(anchor=tk.W)
        
        # Content frame
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        return content

    def setup_file_section(self):
        content = self.create_section_frame(self.left_scrollable, "File Operations", "📁")
        
        ctk.CTkButton(
            content, 
            text="📂 Load Image",
            command=self.load_image,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(fill=tk.X, pady=3)
        
        ctk.CTkButton(
            content,
            text="🎲 Sample Image",
            command=self.create_sample,
            height=36,
            corner_radius=8,
            fg_color=self.colors['bg_light'],
            hover_color=self.colors['bg_medium']
        ).pack(fill=tk.X, pady=3)

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=3)
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            btn_frame, text="💾 Save", command=self.save_progress,
            width=80, height=32, corner_radius=8
        ).grid(row=0, column=0, padx=2, sticky="ew")
        
        ctk.CTkButton(
            btn_frame, text="📥 Load", command=self.load_progress,
            width=80, height=32, corner_radius=8
        ).grid(row=0, column=1, padx=2, sticky="ew")
        
        ctk.CTkButton(
            btn_frame, text="🖼️ Export", command=self.export_image,
            width=80, height=32, corner_radius=8
        ).grid(row=0, column=2, padx=2, sticky="ew")

    def setup_settings_section(self):
        content = self.create_section_frame(self.left_scrollable, "Template Settings", "⚙️")

        # Color count slider
        slider_frame = ctk.CTkFrame(content, fg_color="transparent")
        slider_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(
            slider_frame,
            text="Number of Colors:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor=tk.W)

        slider_row = ctk.CTkFrame(slider_frame, fg_color="transparent")
        slider_row.pack(fill=tk.X)

        self.color_slider = ctk.CTkSlider(
            slider_row,
            from_=5, to=25,
            number_of_steps=20,
            variable=self.color_count_var,
            command=self.on_color_count_change,
            width=200
        )
        self.color_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.color_count_label = ctk.CTkLabel(
            slider_row, text="10", width=30,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors['accent']
        )
        self.color_count_label.pack(side=tk.RIGHT)

        # Generate button
        self.generate_btn = ctk.CTkButton(
            content,
            text="🔄 Generate Template",
            command=self.generate_template,
            height=40,
            corner_radius=10,
            fg_color=self.colors['accent'],
            hover_color="#c73e54",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.generate_btn.pack(fill=tk.X, pady=(10, 0))

    def setup_advanced_section(self):
        content = self.create_section_frame(self.left_scrollable, "Advanced Options", "🔧")

        self.exact_colors_cb = ctk.CTkCheckBox(
            content,
            text="Use exact colors from image",
            variable=self.use_exact_colors,
            font=ctk.CTkFont(size=12)
        )
        self.exact_colors_cb.pack(anchor=tk.W, pady=3)

        self.fill_holes_cb = ctk.CTkCheckBox(
            content,
            text="Fill micro holes",
            variable=self.fill_micro_holes,
            font=ctk.CTkFont(size=12)
        )
        self.fill_holes_cb.pack(anchor=tk.W, pady=3)

        # Min region size
        size_frame = ctk.CTkFrame(content, fg_color="transparent")
        size_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(
            size_frame,
            text="Min region size:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor=tk.W)

        size_row = ctk.CTkFrame(size_frame, fg_color="transparent")
        size_row.pack(fill=tk.X)

        self.size_slider = ctk.CTkSlider(
            size_row,
            from_=10, to=200,
            number_of_steps=19,
            variable=self.min_region_size,
            command=self.on_size_change,
            width=200
        )
        self.size_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.size_label = ctk.CTkLabel(
            size_row, text="30", width=40,
            font=ctk.CTkFont(size=12)
        )
        self.size_label.pack(side=tk.RIGHT)

    def setup_animation_section(self):
        content = self.create_section_frame(self.left_scrollable, "Animation", "🎬")

        # Speed control
        speed_frame = ctk.CTkFrame(content, fg_color="transparent")
        speed_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(
            speed_frame,
            text="Speed (ms):",
            font=ctk.CTkFont(size=12)
        ).pack(anchor=tk.W)

        speed_row = ctk.CTkFrame(speed_frame, fg_color="transparent")
        speed_row.pack(fill=tk.X)

        self.speed_slider = ctk.CTkSlider(
            speed_row,
            from_=20, to=500,
            number_of_steps=48,
            variable=self.speed_var,
            command=self.on_speed_change,
            width=200
        )
        self.speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.speed_label = ctk.CTkLabel(
            speed_row, text="200", width=40,
            font=ctk.CTkFont(size=12)
        )
        self.speed_label.pack(side=tk.RIGHT)

        # Fill order
        order_frame = ctk.CTkFrame(content, fg_color="transparent")
        order_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(
            order_frame,
            text="Fill Order:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor=tk.W, pady=(0, 5))

        order_row = ctk.CTkFrame(order_frame, fg_color="transparent")
        order_row.pack(fill=tk.X)

        for text, value in [("Random", "random"), ("By Color", "by_color"), ("By Size", "by_size")]:
            ctk.CTkRadioButton(
                order_row,
                text=text,
                variable=self.order_var,
                value=value,
                font=ctk.CTkFont(size=11)
            ).pack(side=tk.LEFT, padx=5)

        # Control buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=8)
        btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.play_btn = ctk.CTkButton(
            btn_frame, text="▶", width=50, height=36,
            command=self.start_animation,
            fg_color=self.colors['success'],
            hover_color="#00cc6f",
            font=ctk.CTkFont(size=16)
        )
        self.play_btn.grid(row=0, column=0, padx=2)

        self.pause_btn = ctk.CTkButton(
            btn_frame, text="⏸", width=50, height=36,
            command=self.pause_animation,
            state="disabled",
            fg_color=self.colors['warning'],
            hover_color="#cc8800",
            font=ctk.CTkFont(size=16)
        )
        self.pause_btn.grid(row=0, column=1, padx=2)

        self.stop_btn = ctk.CTkButton(
            btn_frame, text="⏹", width=50, height=36,
            command=self.stop_animation,
            state="disabled",
            fg_color=self.colors['error'],
            hover_color="#cc3333",
            font=ctk.CTkFont(size=16)
        )
        self.stop_btn.grid(row=0, column=2, padx=2)

        self.next_btn = ctk.CTkButton(
            btn_frame, text="⏭", width=50, height=36,
            command=self.fill_next_region,
            font=ctk.CTkFont(size=16)
        )
        self.next_btn.grid(row=0, column=3, padx=2)

    def setup_recording_section(self):
        content = self.create_section_frame(self.left_scrollable, "Recording", "🎥")

        # Resolution
        res_frame = ctk.CTkFrame(content, fg_color="transparent")
        res_frame.pack(fill=tk.X, pady=3)

        ctk.CTkLabel(
            res_frame, text="Resolution:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor=tk.W)

        self.resolution_combo = ctk.CTkComboBox(
            res_frame,
            variable=self.rec_resolution_var,
            values=[
                "Original",
                "720p (1280x720)",
                "1080p (1920x1080)",
                "1440p (2560x1440)",
                "4K (3840x2160)"
            ],
            width=250,
            height=30
        )
        self.resolution_combo.pack(fill=tk.X, pady=2)

        # Quality
        qual_frame = ctk.CTkFrame(content, fg_color="transparent")
        qual_frame.pack(fill=tk.X, pady=3)

        ctk.CTkLabel(
            qual_frame, text="Quality:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor=tk.W)

        self.quality_combo = ctk.CTkComboBox(
            qual_frame,
            variable=self.rec_quality_var,
            values=["Low", "Medium", "High", "Ultra"],
            width=250,
            height=30
        )
        self.quality_combo.pack(fill=tk.X, pady=2)

        # FPS
        fps_frame = ctk.CTkFrame(content, fg_color="transparent")
        fps_frame.pack(fill=tk.X, pady=3)

        ctk.CTkLabel(
            fps_frame, text="FPS:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor=tk.W)

        fps_row = ctk.CTkFrame(fps_frame, fg_color="transparent")
        fps_row.pack(fill=tk.X)

        self.fps_slider = ctk.CTkSlider(
            fps_row,
            from_=5, to=30,
            number_of_steps=25,
            variable=self.fps_var,
            command=self.on_fps_change,
            width=200
        )
        self.fps_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.fps_label = ctk.CTkLabel(
            fps_row, text="10", width=30,
            font=ctk.CTkFont(size=12)
        )
        self.fps_label.pack(side=tk.RIGHT)

        # Record buttons
        rec_btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        rec_btn_frame.pack(fill=tk.X, pady=5)
        rec_btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.rec_btn = ctk.CTkButton(
            rec_btn_frame,
            text="🔴 Record",
            command=self.toggle_recording,
            height=34,
            fg_color="#cc0000",
            hover_color="#990000"
        )
        self.rec_btn.grid(row=0, column=0, padx=2, sticky="ew")

        self.save_video_btn = ctk.CTkButton(
            rec_btn_frame,
            text="💾 Save",
            command=self.save_video,
            state="disabled",
            height=34
        )
        self.save_video_btn.grid(row=0, column=1, padx=2, sticky="ew")

        ctk.CTkButton(
            content,
            text="🎬 Record Full Animation",
            command=self.record_full_animation,
            height=36,
            fg_color=self.colors['bg_light'],
            hover_color=self.colors['bg_medium']
        ).pack(fill=tk.X, pady=3)

        self.rec_status = ctk.CTkLabel(
            content,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color=self.colors['text_dim']
        )
        self.rec_status.pack(pady=2)

    def setup_tools_section(self):
        content = self.create_section_frame(self.left_scrollable, "Tools", "🛠️")

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill=tk.X)
        btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        tools = [
            ("↩️", self.undo, "Undo"),
            ("↪️", self.redo, "Redo"),
            ("🗑️", self.clear_all, "Clear"),
            ("💡", self.show_hint, "Hint")
        ]

        for i, (icon, cmd, tooltip) in enumerate(tools):
            btn = ctk.CTkButton(
                btn_frame,
                text=icon,
                command=cmd,
                width=50,
                height=40,
                font=ctk.CTkFont(size=18)
            )
            btn.grid(row=0, column=i, padx=3, pady=3)

    def setup_view_section(self):
        content = self.create_section_frame(self.left_scrollable, "View", "🔍")

        # View mode
        mode_frame = ctk.CTkFrame(content, fg_color="transparent")
        mode_frame.pack(fill=tk.X, pady=5)

        for text, value in [("Template", "template"), ("Progress", "progress"), ("Original", "original")]:
            ctk.CTkRadioButton(
                mode_frame,
                text=text,
                variable=self.view_mode,
                value=value,
                command=self.update_view_mode,
                font=ctk.CTkFont(size=11)
            ).pack(side=tk.LEFT, padx=8)

        # Zoom controls
        zoom_frame = ctk.CTkFrame(content, fg_color="transparent")
        zoom_frame.pack(fill=tk.X, pady=5)
        zoom_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            zoom_frame, text="➕", width=60, height=32,
            command=lambda: self.zoom(1.25)
        ).grid(row=0, column=0, padx=2)

        ctk.CTkButton(
            zoom_frame, text="➖", width=60, height=32,
            command=lambda: self.zoom(0.8)
        ).grid(row=0, column=1, padx=2)

        ctk.CTkButton(
            zoom_frame, text="🔄", width=60, height=32,
            command=self.reset_view
        ).grid(row=0, column=2, padx=2)

        self.zoom_label = ctk.CTkLabel(
            content, text="Zoom: 100%",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_dim']
        )
        self.zoom_label.pack(pady=5)

        # Progress bar
        progress_frame = ctk.CTkFrame(content, fg_color="transparent")
        progress_frame.pack(fill=tk.X, pady=5)

        ctk.CTkLabel(
            progress_frame,
            text="Progress:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor=tk.W)

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            variable=self.progress_var,
            height=15,
            corner_radius=8,
            progress_color=self.colors['success']
        )
        self.progress_bar.pack(fill=tk.X, pady=3)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="0%",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors['accent2']
        )
        self.progress_label.pack()

    def setup_center_panel(self):
        self.center_panel = ctk.CTkFrame(self.main_frame, corner_radius=15)
        self.center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Canvas container with gradient border effect
        canvas_outer = ctk.CTkFrame(
            self.center_panel,
            corner_radius=12,
            fg_color=self.colors['accent']
        )
        canvas_outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas_inner = ctk.CTkFrame(
            canvas_outer,
            corner_radius=10,
            fg_color=self.colors['bg_medium']
        )
        canvas_inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.canvas = tk.Canvas(
            canvas_inner,
            bg=self.colors['bg_medium'],
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Instructions
        self.instructions = ctk.CTkLabel(
            self.center_panel,
            text="📌 Load image → Generate template → Select color → Click to fill | Scroll: Zoom | Right-drag: Pan",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['accent2']
        )
        self.instructions.pack(pady=8)

    def setup_right_panel(self):
        self.right_panel = ctk.CTkFrame(self.main_frame, width=240, corner_radius=15)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.right_panel.pack_propagate(False)

        # Preview section
        preview_frame = ctk.CTkFrame(self.right_panel, corner_radius=10, fg_color=self.colors['card'])
        preview_frame.pack(fill=tk.X, padx=10, pady=10)

        ctk.CTkLabel(
            preview_frame,
            text="📷 Original Preview",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors['accent2']
        ).pack(pady=(8, 5))

        preview_container = ctk.CTkFrame(preview_frame, fg_color=self.colors['bg_medium'], corner_radius=8)
        preview_container.pack(padx=10, pady=(0, 10))

        self.preview_canvas = tk.Canvas(
            preview_container,
            width=200,
            height=130,
            bg=self.colors['bg_medium'],
            highlightthickness=0
        )
        self.preview_canvas.pack(padx=2, pady=2)

        # Palette header
        palette_header = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        palette_header.pack(fill=tk.X, padx=10, pady=(5, 0))

        ctk.CTkLabel(
            palette_header,
            text="🎨 Color Palette",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['accent']
        ).pack()

        # Scrollable palette
        self.palette_scroll = ctk.CTkScrollableFrame(
            self.right_panel,
            fg_color="transparent",
            corner_radius=10
        )
        self.palette_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Selected color display
        selected_frame = ctk.CTkFrame(self.right_panel, corner_radius=10, fg_color=self.colors['card'])
        selected_frame.pack(fill=tk.X, padx=10, pady=10)

        ctk.CTkLabel(
            selected_frame,
            text="✓ Selected Color",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.colors['accent2']
        ).pack(pady=(8, 5))

        self.selected_color_canvas = tk.Canvas(
            selected_frame,
            width=200,
            height=50,
            bg=self.colors['bg_medium'],
            highlightthickness=0
        )
        self.selected_color_canvas.pack(pady=5)

        self.selected_color_label = ctk.CTkLabel(
            selected_frame,
            text="None selected",
            font=ctk.CTkFont(size=11),
            text_color=self.colors['text_dim']
        )
        self.selected_color_label.pack(pady=(0, 10))

    def setup_status_bar(self):
        status_frame = ctk.CTkFrame(self.root, height=30, corner_radius=0, fg_color=self.colors['bg_light'])
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color=self.colors['text_dim']
        )
        self.status_label.pack(side=tk.LEFT, padx=15)

        self.region_count_label = ctk.CTkLabel(
            status_frame,
            text="Regions: 0",
            font=ctk.CTkFont(size=11),
            text_color=self.colors['text_dim']
        )
        self.region_count_label.pack(side=tk.RIGHT, padx=15)

    def setup_bindings(self):
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)
        self.canvas.bind("<ButtonRelease-3>", self.end_pan)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)

        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-s>", lambda e: self.save_progress())
        self.root.bind("<space>", lambda e: self.toggle_animation())

    def set_status(self, message, status_type="info"):
        colors = {
            "info": self.colors['text_dim'],
            "success": self.colors['success'],
            "warning": self.colors['warning'],
            "error": self.colors['error']
        }
        self.status_label.configure(text=message, text_color=colors.get(status_type, self.colors['text_dim']))
        self.root.update()

    def on_color_count_change(self, value):
        count = int(float(value))
        self.color_count_label.configure(text=str(count))
        self.num_colors = count

    def on_speed_change(self, value):
        speed = int(float(value))
        self.animation_speed = speed
        self.speed_label.configure(text=str(speed))

    def on_size_change(self, value):
        self.size_label.configure(text=str(int(float(value))))

    def on_fps_change(self, value):
        self.fps_label.configure(text=str(int(float(value))))

    def update_view_mode(self):
        mode = self.view_mode.get()

        if mode == "original" and self.original_image:
            self.display_image = self.original_image.copy()
        elif mode == "template" and self.template_image:
            self.display_image = self.template_image.copy()
            if self.colored_regions:
                img_array = np.array(self.display_image)
                for region_id in self.colored_regions:
                    if self.regions and region_id in self.regions:
                        region_info = self.regions[region_id]
                        color = self.color_palette[region_info['color_num']]
                        img_array[region_info['mask']] = color
                self.display_image = Image.fromarray(img_array)
        elif mode == "progress" and self.processed_image:
            self.display_image = self.processed_image.copy()

        self.update_canvas()

    def create_sample(self):
        width, height = 500, 500
        img = Image.new('RGB', (width, height), '#87CEEB')
        draw = ImageDraw.Draw(img)

        for y in range(height // 2):
            r = int(135 + (y / (height / 2)) * 30)
            g = int(206 + (y / (height / 2)) * 20)
            b = int(235 + (y / (height / 2)) * 10)
            draw.line([(0, y), (width, y)], fill=(min(255, r), min(255, g), min(255, b)))

        sun_center = (400, 80)
        for r in range(60, 0, -2):
            intensity = int(255 - (60 - r) * 2)
            draw.ellipse([sun_center[0] - r, sun_center[1] - r, sun_center[0] + r, sun_center[1] + r],
                         fill=(255, intensity, 0))

        draw.polygon([(0, 350), (150, 180), (300, 350)], fill='#2E7D32', outline='#1B5E20')
        draw.polygon([(180, 350), (350, 150), (520, 350)], fill='#43A047', outline='#2E7D32')

        draw.rectangle([0, 350, 500, 500], fill='#66BB6A')

        draw.rectangle([140, 260, 280, 380], fill='#8D6E63', outline='#5D4037', width=2)
        draw.polygon([(130, 260), (210, 180), (290, 260)], fill='#C62828', outline='#B71C1C', width=2)
        draw.rectangle([190, 310, 230, 380], fill='#5D4037')
        draw.rectangle([155, 280, 180, 310], fill='#81D4FA', outline='#0288D1', width=2)
        draw.rectangle([240, 280, 265, 310], fill='#81D4FA', outline='#0288D1', width=2)

        draw.rectangle([380, 280, 410, 380], fill='#6D4C41')
        draw.ellipse([340, 180, 450, 300], fill='#2E7D32')

        flower_colors = ['#E91E63', '#FF5722', '#FFEB3B', '#9C27B0']
        for i, (x, y) in enumerate([(60, 370), (100, 385), (420, 360), (460, 375)]):
            draw.ellipse([x - 12, y - 12, x + 12, y + 12], fill=flower_colors[i % len(flower_colors)])
            draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill='#FFEB3B')

        for cx, cy in [(80, 70), (220, 50), (320, 90)]:
            for dx, dy in [(0, 0), (25, -8), (50, 0), (15, 12), (35, 10)]:
                draw.ellipse([cx + dx - 18, cy + dy - 12, cx + dx + 18, cy + dy + 12], fill='white')

        self.original_image = img
        self.update_preview()
        self.display_original()
        self.set_status("Sample image created! Click 'Generate Template' to continue.", "success")

    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")]
        )

        if file_path:
            try:
                self.set_status("Loading image...", "info")
                self.original_image = Image.open(file_path).convert("RGB")

                max_size = 800
                if max(self.original_image.size) > max_size:
                    ratio = max_size / max(self.original_image.size)
                    new_size = (int(self.original_image.width * ratio),
                                int(self.original_image.height * ratio))
                    self.original_image = self.original_image.resize(new_size, Image.LANCZOS)

                self.update_preview()
                self.display_original()
                self.set_status(f"Image loaded: {self.original_image.size[0]}x{self.original_image.size[1]}", "success")

            except Exception as e:
                self.set_status(f"Failed to load image: {str(e)}", "error")
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def update_preview(self):
        if self.original_image:
            preview = self.original_image.copy()
            preview.thumbnail((200, 130), Image.LANCZOS)

            self.preview_photo = ImageTk.PhotoImage(preview)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(100, 65, anchor=tk.CENTER, image=self.preview_photo)

    def display_original(self):
        if self.original_image:
            self.display_image = self.original_image.copy()
            self.view_mode.set("original")
            self.update_canvas()

    def generate_template(self):
        if not self.original_image:
            messagebox.showwarning("Warning", "Please load an image first!")
            return

        try:
            self.set_status("Generating template...", "info")
            self.root.config(cursor="wait")
            self.root.update()

            self.stop_animation()

            img_array = np.array(self.original_image)

            img_filtered = cv2.bilateralFilter(img_array, 9, 75, 75)
            pixels = img_filtered.reshape(-1, 3)

            n_colors = self.num_colors
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10, max_iter=300)
            labels = kmeans.fit_predict(pixels)

            cluster_centers = kmeans.cluster_centers_.astype(int)

            self.color_palette = {}
            self.original_colors = {}

            for i in range(n_colors):
                cluster_mask = (labels == i)
                cluster_pixels = pixels[cluster_mask]

                if self.use_exact_colors.get() and len(cluster_pixels) > 0:
                    pixel_tuples = [tuple(p) for p in cluster_pixels]
                    color_counts = Counter(pixel_tuples)

                    top_colors = color_counts.most_common(min(10, len(color_counts)))
                    centroid = cluster_centers[i]
                    best_color = top_colors[0][0]
                    best_dist = float('inf')

                    most_common_count = color_counts.most_common(1)[0][1]
                    for color, count in top_colors:
                        dist = np.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(color, centroid)))
                        if count > most_common_count * 0.5:
                            if dist < best_dist:
                                best_dist = dist
                                best_color = color

                    median_color = tuple(np.median(cluster_pixels, axis=0).astype(int))
                    best_sat = max(best_color) - min(best_color)
                    median_sat = max(median_color) - min(median_color)

                    final_color = median_color if median_sat > best_sat * 1.2 else best_color
                    self.color_palette[i + 1] = final_color
                else:
                    self.color_palette[i + 1] = tuple(cluster_centers[i])

                self.original_colors[i + 1] = tuple(cluster_centers[i])

            self.region_labels = labels.reshape(img_array.shape[:2])

            self.regions = self.create_regions()

            if self.fill_micro_holes.get():
                self.fill_remaining_holes()

            self.create_template_image()
            self.processed_image = self.create_colored_image()

            self.colored_regions = {}
            self.history = []
            self.history_index = -1
            self.recorded_frames = []

            self.update_palette()
            self.view_mode.set("template")
            self.update_canvas()
            self.update_progress()

            self.root.config(cursor="")
            self.region_count_label.configure(text=f"Regions: {len(self.regions)}")
            self.set_status(f"Template generated: {n_colors} colors, {len(self.regions)} regions", "success")

        except Exception as e:
            self.root.config(cursor="")
            self.set_status(f"Failed to generate template: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to generate template: {str(e)}")

    def create_colored_image(self):
        height, width = self.region_labels.shape
        colored = np.zeros((height, width, 3), dtype=np.uint8)

        for color_num, color in self.color_palette.items():
            mask = (self.region_labels == (color_num - 1))
            colored[mask] = color

        return Image.fromarray(colored)

    def create_regions(self):
        regions = {}
        region_id = 0
        min_size = self.min_region_size.get()

        height, width = self.region_labels.shape
        all_assigned = np.zeros((height, width), dtype=bool)

        for color_num in range(self.num_colors):
            mask = (self.region_labels == color_num).astype(np.uint8)

            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

            labeled, num_features = ndimage.label(mask)

            for i in range(1, num_features + 1):
                region_mask = (labeled == i)
                region_size = np.sum(region_mask)

                if region_size >= min_size:
                    filled_mask = ndimage.binary_fill_holes(region_mask)
                    centroid = ndimage.center_of_mass(filled_mask)

                    regions[region_id] = {
                        'mask': filled_mask,
                        'color_num': color_num + 1,
                        'size': int(np.sum(filled_mask)),
                        'centroid': centroid
                    }

                    all_assigned |= filled_mask
                    region_id += 1

        orphan_mask = ~all_assigned
        if np.any(orphan_mask):
            self.assign_orphan_pixels(regions, orphan_mask)

        return regions

    def assign_orphan_pixels(self, regions, orphan_mask):
        if not regions:
            return

        height, width = orphan_mask.shape

        all_regions_mask = np.zeros((height, width), dtype=np.int32)
        for region_id, region_info in regions.items():
            all_regions_mask[region_info['mask']] = region_id + 1

        for _ in range(10):
            kernel = np.ones((3, 3), np.uint8)
            dilated = cv2.dilate(all_regions_mask.astype(np.uint8), kernel, iterations=1)

            new_assignments = dilated.astype(np.int32)
            new_assignments[all_regions_mask > 0] = all_regions_mask[all_regions_mask > 0]

            for region_id, region_info in regions.items():
                new_mask = (new_assignments == region_id + 1)
                if np.sum(new_mask) > np.sum(region_info['mask']):
                    region_info['mask'] = new_mask
                    region_info['size'] = int(np.sum(new_mask))

            all_regions_mask = new_assignments

            if not np.any((all_regions_mask == 0) & orphan_mask):
                break

    def fill_remaining_holes(self):
        if not self.regions:
            return

        height, width = self.region_labels.shape
        assigned = np.zeros((height, width), dtype=bool)

        for region_info in self.regions.values():
            assigned |= region_info['mask']

        unassigned = ~assigned

        if np.any(unassigned):
            unassigned_coords = np.where(unassigned)

            for y, x in zip(unassigned_coords[0], unassigned_coords[1]):
                original_label = self.region_labels[y, x]
                target_color = original_label + 1

                best_region = None
                best_dist = float('inf')

                for region_id, region_info in self.regions.items():
                    if region_info['color_num'] == target_color:
                        cy, cx = region_info['centroid']
                        dist = (y - cy) ** 2 + (x - cx) ** 2
                        if dist < best_dist:
                            best_dist = dist
                            best_region = region_id

                if best_region is None:
                    for region_id, region_info in self.regions.items():
                        cy, cx = region_info['centroid']
                        dist = (y - cy) ** 2 + (x - cx) ** 2
                        if dist < best_dist:
                            best_dist = dist
                            best_region = region_id

                if best_region is not None:
                    mask = self.regions[best_region]['mask'].copy()
                    mask[y, x] = True
                    self.regions[best_region]['mask'] = mask
                    self.regions[best_region]['size'] += 1

    def create_template_image(self):
        height, width = self.region_labels.shape

        self.template_image = Image.new('RGB', (width, height), 'white')

        edges = self.detect_edges()

        template_array = np.array(self.template_image)
        template_array[edges] = [60, 60, 60]

        assigned = np.zeros((height, width), dtype=bool)
        for region_info in self.regions.values():
            assigned |= region_info['mask']

        if np.any(~assigned):
            unassigned_coords = np.where(~assigned)
            for y, x in zip(unassigned_coords[0], unassigned_coords[1]):
                if not edges[y, x]:
                    template_array[y, x] = [240, 240, 240]

        self.template_image = Image.fromarray(template_array)
        draw = ImageDraw.Draw(self.template_image)

        try:
            font_size = max(10, min(width, height) // 50)
            font = ImageFont.truetype("arial.ttf", font_size)
            small_font = ImageFont.truetype("arial.ttf", max(8, font_size - 2))
        except Exception:
            font = ImageFont.load_default()
            small_font = font

        for region_id, region_info in self.regions.items():
            centroid = region_info['centroid']
            color_num = region_info['color_num']
            size = region_info['size']

            if size > 500:
                use_font = font
            elif size > 200:
                use_font = small_font
            else:
                continue

            y, x = int(centroid[0]), int(centroid[1])
            text = str(color_num)

            bbox = draw.textbbox((x, y), text, font=use_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            text_x = x - text_width // 2
            text_y = y - text_height // 2

            if 0 <= y < height and 0 <= x < width:
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx != 0 or dy != 0:
                            draw.text((text_x + dx, text_y + dy), text, fill='white', font=use_font)
                draw.text((text_x, text_y), text, fill='#333333', font=use_font)

        self.display_image = self.template_image.copy()

    def detect_edges(self):
        """THIN (1-pixel) region borders."""
        labels = self.region_labels.astype(np.int32)
        h, w = labels.shape
        edges = np.zeros((h, w), dtype=bool)

        edges[:, :-1] |= (labels[:, :-1] != labels[:, 1:])
        edges[:-1, :] |= (labels[:-1, :] != labels[1:, :])
        return edges

    def update_palette(self):
        # Clear existing palette
        for widget in self.palette_scroll.winfo_children():
            widget.destroy()

        self.palette_buttons = {}

        for num, color in self.color_palette.items():
            frame = ctk.CTkFrame(
                self.palette_scroll,
                corner_radius=8,
                fg_color=self.colors['card'],
                height=45
            )
            frame.pack(fill=tk.X, pady=3, padx=2)
            frame.pack_propagate(False)

            color_hex = '#{:02x}{:02x}{:02x}'.format(*color)

            # Number label
            num_label = ctk.CTkLabel(
                frame,
                text=str(num),
                font=ctk.CTkFont(size=14, weight="bold"),
                width=25
            )
            num_label.pack(side=tk.LEFT, padx=5)

            # Color button
            color_btn = ctk.CTkButton(
                frame,
                text="",
                width=60,
                height=30,
                corner_radius=6,
                fg_color=color_hex,
                hover_color=color_hex,
                command=lambda n=num: self.select_color(n)
            )
            color_btn.pack(side=tk.LEFT, padx=3)

            # Original color indicator
            if num in self.original_colors:
                orig_hex = '#{:02x}{:02x}{:02x}'.format(*self.original_colors[num])
                orig_canvas = tk.Canvas(
                    frame, width=15, height=25,
                    bg=self.colors['card'],
                    highlightthickness=0
                )
                orig_canvas.pack(side=tk.LEFT, padx=2)
                orig_canvas.create_rectangle(2, 2, 13, 23, fill=orig_hex, outline='gray')

            # Region count
            count = sum(1 for r in self.regions.values() if r['color_num'] == num)
            count_label = ctk.CTkLabel(
                frame,
                text=f"({count})",
                font=ctk.CTkFont(size=10),
                text_color=self.colors['text_dim']
            )
            count_label.pack(side=tk.LEFT, padx=3)

            # Progress indicator
            progress_label = ctk.CTkLabel(
                frame,
                text="○",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            progress_label.pack(side=tk.RIGHT, padx=5)

            self.palette_buttons[num] = {
                'frame': frame,
                'button': color_btn,
                'progress': progress_label,
                'color_hex': color_hex
            }

    def select_color(self, color_num):
        self.selected_color_num = color_num

        for num, widgets in self.palette_buttons.items():
            if num == color_num:
                widgets['frame'].configure(fg_color=self.colors['bg_light'])
                widgets['button'].configure(border_width=3, border_color=self.colors['accent'])
            else:
                widgets['frame'].configure(fg_color=self.colors['card'])
                widgets['button'].configure(border_width=0)

        color = self.color_palette.get(color_num, (128, 128, 128))
        color_hex = '#{:02x}{:02x}{:02x}'.format(*color)

        self.selected_color_canvas.delete("all")
        self.selected_color_canvas.create_rectangle(5, 5, 195, 45, fill=color_hex, outline='white', width=2)
        self.selected_color_canvas.create_text(
            100, 25, text=f"#{color_num}",
            fill='white' if sum(color) < 400 else 'black',
            font=('Segoe UI', 14, 'bold')
        )

        self.selected_color_label.configure(text=f"RGB: {color}")
        self.set_status(f"Selected color #{color_num}", "info")

    def on_canvas_click(self, event):
        if self.is_animating:
            return

        if not self.regions or not self.selected_color_num:
            if not self.regions:
                messagebox.showinfo("Info", "Please generate a template first!")
            else:
                messagebox.showinfo("Info", "Please select a color from the palette!")
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        img_x = int((canvas_x - self.pan_offset[0]) / self.zoom_level)
        img_y = int((canvas_y - self.pan_offset[1]) / self.zoom_level)

        clicked_region = self.find_region_at(img_x, img_y)

        if clicked_region is not None:
            region_info = self.regions[clicked_region]
            correct_color = region_info['color_num']

            if self.selected_color_num == correct_color:
                self.fill_region(clicked_region)
                self.capture_frame()
                self.update_canvas()
                self.update_progress()
                self.set_status(f"Filled region with color #{correct_color}", "success")

                if self.check_completion():
                    self.on_completion()
            else:
                self.flash_region(clicked_region, "red")
                self.set_status(f"Wrong color! This region needs color #{correct_color}", "warning")

    def find_region_at(self, x, y):
        if not self.regions:
            return None

        height, width = self.region_labels.shape
        if 0 <= x < width and 0 <= y < height:
            for region_id, region_info in self.regions.items():
                if region_id not in self.colored_regions and region_info['mask'][y, x]:
                    return region_id
        return None

    def fill_region(self, region_id, save_history=True):
        if save_history:
            self.save_state()

        region_info = self.regions[region_id]
        color_num = region_info['color_num']
        color = self.color_palette[color_num]

        self.colored_regions[region_id] = color_num

        img_array = np.array(self.display_image)
        mask = region_info['mask']
        img_array[mask] = color
        self.display_image = Image.fromarray(img_array)

        self.update_palette_progress()

    def flash_region(self, region_id, color):
        original = self.display_image.copy()

        region_info = self.regions[region_id]
        img_array = np.array(self.display_image)
        mask = region_info['mask']

        img_array[mask] = [255, 100, 100]
        self.display_image = Image.fromarray(img_array)
        self.update_canvas()

        self.root.after(200, lambda: self.restore_image(original))

    def restore_image(self, image):
        self.display_image = image
        self.update_canvas()

    # ==================== Animation Methods ====================

    def get_fill_order(self):
        uncolored = [r for r in self.regions if r not in self.colored_regions]

        if self.order_var.get() == "random":
            random.shuffle(uncolored)
        elif self.order_var.get() == "by_color":
            uncolored.sort(key=lambda r: self.regions[r]['color_num'])
        elif self.order_var.get() == "by_size":
            uncolored.sort(key=lambda r: self.regions[r]['size'], reverse=True)

        return uncolored

    def start_animation(self):
        if not self.regions:
            messagebox.showwarning("Warning", "Please generate a template first!")
            return

        if self.is_animating:
            return

        self.is_animating = True
        self.animation_paused = False

        self.play_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.stop_btn.configure(state="normal")

        self.fill_order = self.get_fill_order()
        self.current_fill_index = 0

        self.set_status("Animation started...", "info")
        self.animate_next()

    def animate_next(self):
        if not self.is_animating or self.animation_paused:
            return

        if self.current_fill_index >= len(self.fill_order):
            self.stop_animation()
            if self.check_completion():
                self.on_completion()
            return

        region_id = self.fill_order[self.current_fill_index]

        if region_id not in self.colored_regions:
            self.fill_region(region_id, save_history=False)
            self.capture_frame()
            self.update_canvas()
            self.update_progress()

        self.current_fill_index += 1
        self.root.after(self.animation_speed, self.animate_next)

    def pause_animation(self):
        if self.is_animating:
            self.animation_paused = not self.animation_paused

            if self.animation_paused:
                self.pause_btn.configure(text="▶")
                self.set_status("Animation paused", "warning")
            else:
                self.pause_btn.configure(text="⏸")
                self.set_status("Animation resumed", "info")
                self.animate_next()

    def stop_animation(self):
        self.is_animating = False
        self.animation_paused = False

        self.play_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled", text="⏸")
        self.stop_btn.configure(state="disabled")
        self.set_status("Animation stopped", "info")

    def toggle_animation(self):
        if self.is_animating:
            self.pause_animation()
        else:
            self.start_animation()

    def fill_next_region(self):
        if not self.regions:
            return

        uncolored = self.get_fill_order()

        if uncolored:
            region_id = uncolored[0]
            self.fill_region(region_id)
            self.capture_frame()
            self.update_canvas()
            self.update_progress()

            color_num = self.regions[region_id]['color_num']
            self.select_color(color_num)

            if self.check_completion():
                self.on_completion()
        else:
            messagebox.showinfo("Complete", "All regions are colored!")

    # ==================== Recording Methods ====================

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if not self.display_image:
            messagebox.showwarning("Warning", "Please generate a template first!")
            return

        self.is_recording = True
        self.recorded_frames = []
        self.record_start_time = time.time()

        self.rec_btn.configure(text="⏹ Stop")
        self.save_video_btn.configure(state="disabled")
        self.rec_status.configure(
            text=f"🔴 Recording... {self.rec_resolution_var.get()} | {self.rec_quality_var.get()}",
            text_color=self.colors['warning']
        )

        self.capture_frame()
        self.set_status("Recording started", "warning")

    def stop_recording(self):
        self.is_recording = False

        self.rec_btn.configure(text="🔴 Record")
        self.save_video_btn.configure(state="normal" if self.recorded_frames else "disabled")

        duration = time.time() - self.record_start_time if self.record_start_time else 0
        self.rec_status.configure(
            text=f"Recorded {len(self.recorded_frames)} frames ({duration:.1f}s)",
            text_color=self.colors['text_dim']
        )
        self.set_status(f"Recording stopped: {len(self.recorded_frames)} frames", "info")

    def capture_frame(self):
        if self.is_recording and self.display_image:
            frame = self.display_image.copy()
            self.recorded_frames.append(frame)

    def save_video(self):
        if not self.recorded_frames:
            messagebox.showwarning("Warning", "No frames recorded!")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[
                ("MP4 files", "*.mp4"),
                ("AVI files", "*.avi"),
                ("GIF files", "*.gif")
            ],
            initialfile=f"coloring_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        if not file_path:
            return

        try:
            self.set_status("Saving video...", "info")
            self.root.config(cursor="wait")
            self.root.update()

            if file_path.lower().endswith('.gif'):
                self.save_as_gif(file_path)
            else:
                self.save_as_video(file_path)

            self.root.config(cursor="")
            self.set_status(f"Video saved: {file_path}", "success")
            messagebox.showinfo("Success", f"Video saved to {file_path}")

        except Exception as e:
            self.root.config(cursor="")
            self.set_status(f"Failed to save video: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to save video: {str(e)}")

    def _parse_resolution_choice(self, choice: str):
        if not choice or choice.strip().lower() == "original":
            return None
        m = re.search(r'(\d+)\s*x\s*(\d+)', choice)
        if not m:
            return None
        return int(m.group(1)), int(m.group(2))

    def _resize_with_letterbox(self, img: Image.Image, target_w: int, target_h: int, fill=(255, 255, 255)):
        img = img.convert("RGB")
        src_w, src_h = img.size
        if src_w <= 0 or src_h <= 0:
            return Image.new("RGB", (target_w, target_h), fill)

        scale = min(target_w / src_w, target_h / src_h)
        new_w = max(1, int(round(src_w * scale)))
        new_h = max(1, int(round(src_h * scale)))

        resized = img.resize((new_w, new_h), Image.LANCZOS)
        out = Image.new("RGB", (target_w, target_h), fill)
        ox = (target_w - new_w) // 2
        oy = (target_h - new_h) // 2
        out.paste(resized, (ox, oy))
        return out

    def _quality_value(self):
        q = (self.rec_quality_var.get() or "High").strip().lower()
        return {
            "low": 35,
            "medium": 60,
            "high": 85,
            "ultra": 95
        }.get(q, 85)

    def _fourcc_candidates(self, ext: str):
        q = (self.rec_quality_var.get() or "High").strip().lower()
        if ext == ".mp4":
            if q in ("high", "ultra"):
                return ["avc1", "H264", "X264", "mp4v"]
            return ["mp4v", "avc1", "H264"]
        else:
            if q in ("high", "ultra"):
                return ["MJPG", "XVID"]
            return ["XVID", "MJPG"]

    def _make_video_writer(self, file_path: str, fps: int, size_wh):
        w, h = size_wh
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in (".mp4", ".avi"):
            ext = ".mp4"

        if ext == ".mp4":
            if w % 2 == 1:
                w -= 1
            if h % 2 == 1:
                h -= 1
        w = max(2, w)
        h = max(2, h)

        last = None
        for code in self._fourcc_candidates(ext):
            try:
                fourcc = cv2.VideoWriter_fourcc(*code)
                out = cv2.VideoWriter(file_path, fourcc, fps, (w, h))
                if out is not None and out.isOpened():
                    try:
                        out.set(cv2.VIDEOWRITER_PROP_QUALITY, float(self._quality_value()))
                    except Exception:
                        pass
                    return out, (w, h), code
                last = out
            except Exception as e:
                last = e

        raise RuntimeError(f"Could not open VideoWriter for {file_path} (last={last})")

    def save_as_video(self, file_path):
        if not self.recorded_frames:
            return

        fps = int(self.fps_var.get())

        choice = self.rec_resolution_var.get()
        res = self._parse_resolution_choice(choice)

        first = self.recorded_frames[0].convert("RGB")
        if res is None:
            out_w, out_h = first.size
        else:
            out_w, out_h = res

        out, (out_w, out_h), _used_codec = self._make_video_writer(file_path, fps, (out_w, out_h))

        try:
            for frame in self.recorded_frames:
                img = frame.convert("RGB")
                if res is None:
                    if img.size != (out_w, out_h):
                        img = img.resize((out_w, out_h), Image.LANCZOS)
                else:
                    img = self._resize_with_letterbox(img, out_w, out_h, fill=(255, 255, 255))

                frame_rgb = np.array(img, dtype=np.uint8)
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                out.write(frame_bgr)
        finally:
            out.release()

    def save_as_gif(self, file_path):
        if not self.recorded_frames:
            return

        fps = int(self.fps_var.get())
        duration = int(1000 / max(1, fps))

        choice = self.rec_resolution_var.get()
        res = self._parse_resolution_choice(choice)

        frames = []
        for frame in self.recorded_frames:
            img = frame.convert("RGB")

            if res is not None:
                tw, th = res
                img = self._resize_with_letterbox(img, tw, th, fill=(255, 255, 255))
            else:
                max_size = 800
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)

            img = img.convert('P', palette=Image.ADAPTIVE, colors=256)
            frames.append(img)

        frames[0].save(
            file_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            optimize=False
        )

    def record_full_animation(self):
        if not self.regions:
            messagebox.showwarning("Warning", "Please generate a template first!")
            return

        if messagebox.askyesno(
            "Record Animation",
            "This will clear current progress and record the full coloring animation. Continue?"
        ):
            self.colored_regions = {}
            self.display_image = self.template_image.copy()
            self.update_canvas()
            self.update_progress()

            self.start_recording()

            for _ in range(self.fps_var.get()):
                self.capture_frame()

            self.start_animation()

    # ==================== Canvas & Display Methods ====================

    def update_canvas(self):
        if not self.display_image:
            return

        width = int(self.display_image.width * self.zoom_level)
        height = int(self.display_image.height * self.zoom_level)

        resized = self.display_image.resize((width, height), Image.NEAREST)

        self.photo = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        self.canvas.create_image(self.pan_offset[0], self.pan_offset[1],
                                 anchor=tk.NW, image=self.photo)

        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def update_progress(self):
        if not self.regions:
            return

        total_regions = len(self.regions)
        colored_regions = len(self.colored_regions)

        progress = (colored_regions / total_regions) if total_regions > 0 else 0
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"{progress*100:.1f}% ({colored_regions}/{total_regions})")

    def update_palette_progress(self):
        color_progress = defaultdict(lambda: {'total': 0, 'done': 0})

        for region_id, region_info in self.regions.items():
            color_num = region_info['color_num']
            color_progress[color_num]['total'] += 1
            if region_id in self.colored_regions:
                color_progress[color_num]['done'] += 1

        for num, widgets in self.palette_buttons.items():
            progress = color_progress[num]
            if progress['total'] > 0:
                if progress['done'] == progress['total']:
                    widgets['progress'].configure(text="✓", text_color=self.colors['success'])
                elif progress['done'] > 0:
                    widgets['progress'].configure(text="◐", text_color=self.colors['warning'])
                else:
                    widgets['progress'].configure(text="○", text_color="gray")

    def check_completion(self):
        return self.regions is not None and len(self.colored_regions) == len(self.regions)

    def on_completion(self):
        self.stop_animation()

        if self.is_recording:
            for _ in range(self.fps_var.get() * 2):
                self.capture_frame()
            self.stop_recording()

        self.set_status("🎉 Coloring complete!", "success")
        messagebox.showinfo("🎉 Congratulations!",
                            f"You completed the coloring!\n\nRecorded {len(self.recorded_frames)} frames.")

    # ==================== History & Tools ====================

    def save_state(self):
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]

        state = {
            'colored_regions': self.colored_regions.copy(),
            'display_image': self.display_image.copy()
        }
        self.history.append(state)
        self.history_index = len(self.history) - 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            state = self.history[self.history_index]
            self.colored_regions = state['colored_regions'].copy()
            self.display_image = state['display_image'].copy()
            self.update_canvas()
            self.update_progress()
            self.update_palette_progress()
            self.set_status("Undo", "info")

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            state = self.history[self.history_index]
            self.colored_regions = state['colored_regions'].copy()
            self.display_image = state['display_image'].copy()
            self.update_canvas()
            self.update_progress()
            self.update_palette_progress()
            self.set_status("Redo", "info")

    def clear_all(self):
        if messagebox.askyesno("Confirm", "Clear all colored regions?"):
            self.stop_animation()
            self.colored_regions = {}
            if self.template_image:
                self.display_image = self.template_image.copy()
            self.update_canvas()
            self.update_progress()
            self.update_palette_progress()
            self.history = []
            self.history_index = -1
            self.set_status("Cleared all regions", "info")

    def show_hint(self):
        if not self.regions:
            return

        uncolored = [r for r in self.regions if r not in self.colored_regions]

        if uncolored:
            region_id = random.choice(uncolored)
            region_info = self.regions[region_id]
            color_num = region_info['color_num']

            self.select_color(color_num)
            self.flash_hint(region_id)
            self.set_status(f"Hint: Look for color #{color_num}", "info")
        else:
            messagebox.showinfo("Hint", "All regions are colored!")

    def flash_hint(self, region_id):
        region_info = self.regions[region_id]
        color_num = region_info['color_num']
        color = self.color_palette[color_num]

        original = self.display_image.copy()

        for i in range(4):
            if i % 2 == 0:
                img_array = np.array(self.display_image)
                mask = region_info['mask']
                light_color = [min(255, c + 80) for c in color]
                img_array[mask] = light_color
                self.display_image = Image.fromarray(img_array)
            else:
                self.display_image = original.copy()

            self.update_canvas()
            self.root.update()
            time.sleep(0.15)

        self.display_image = original
        self.update_canvas()

    # ==================== View Controls ====================

    def zoom(self, factor):
        new_zoom = self.zoom_level * factor
        if 0.2 <= new_zoom <= 5.0:
            self.zoom_level = new_zoom
            self.zoom_label.configure(text=f"Zoom: {int(self.zoom_level * 100)}%")
            self.update_canvas()

    def reset_view(self):
        self.zoom_level = 1.0
        self.pan_offset = [0, 0]
        self.zoom_label.configure(text="Zoom: 100%")
        self.update_canvas()

    def start_pan(self, event):
        self.drag_start = (event.x, event.y)
        self.is_panning = True

    def do_pan(self, event):
        if self.is_panning and self.drag_start:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.pan_offset[0] += dx
            self.pan_offset[1] += dy
            self.drag_start = (event.x, event.y)
            self.update_canvas()

    def end_pan(self, event):
        self.is_panning = False
        self.drag_start = None

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.zoom(1.15)
        else:
            self.zoom(0.85)

    # ==================== Save/Load ====================

    def save_progress(self):
        if not self.original_image:
            messagebox.showwarning("Warning", "No image to save!")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )

        if file_path:
            try:
                data = {
                    'colored_regions': {str(k): v for k, v in self.colored_regions.items()},
                    'color_palette': {str(k): list(v) for k, v in self.color_palette.items()},
                    'num_colors': self.num_colors
                }

                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)

                base_path = file_path.rsplit('.', 1)[0]
                if self.original_image:
                    self.original_image.save(f"{base_path}_original.png")
                if self.display_image:
                    self.display_image.save(f"{base_path}_progress.png")

                self.set_status("Progress saved!", "success")
                messagebox.showinfo("Success", "Progress saved!")
            except Exception as e:
                self.set_status(f"Failed to save: {str(e)}", "error")
                messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def load_progress(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                base_path = file_path.rsplit('.', 1)[0]
                original_path = f"{base_path}_original.png"

                if os.path.exists(original_path):
                    self.original_image = Image.open(original_path).convert("RGB")
                    self.update_preview()

                    self.color_palette = {int(k): tuple(v) for k, v in data['color_palette'].items()}
                    self.num_colors = data['num_colors']
                    self.color_count_var.set(self.num_colors)

                    self.generate_template()

                    self.colored_regions = {int(k): v for k, v in data['colored_regions'].items()}

                    for region_id in self.colored_regions:
                        if region_id in self.regions:
                            region_info = self.regions[region_id]
                            color = self.color_palette[region_info['color_num']]
                            img_array = np.array(self.display_image)
                            img_array[region_info['mask']] = color
                            self.display_image = Image.fromarray(img_array)

                    self.update_canvas()
                    self.update_progress()
                    self.update_palette_progress()

                    self.set_status("Progress loaded!", "success")
                    messagebox.showinfo("Success", "Progress loaded!")
                else:
                    messagebox.showerror("Error", "Original image not found!")
            except Exception as e:
                self.set_status(f"Failed to load: {str(e)}", "error")
                messagebox.showerror("Error", f"Failed to load: {str(e)}")

    def export_image(self):
        if not self.display_image:
            messagebox.showwarning("Warning", "No image to export!")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg")]
        )

        if file_path:
            try:
                self.display_image.save(file_path)
                self.set_status(f"Exported to {file_path}", "success")
                messagebox.showinfo("Success", f"Image exported to {file_path}")
            except Exception as e:
                self.set_status(f"Failed to export: {str(e)}", "error")
                messagebox.showerror("Error", f"Failed to export: {str(e)}")


def main():
    root = ctk.CTk()
    app = ColorByNumberApp(root)

    # Menu bar (using tkinter Menu as CTk doesn't have native menu)
    menu_bar = tk.Menu(root)
    root.config(menu=menu_bar)

    file_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Load Image", command=app.load_image, accelerator="Ctrl+O")
    file_menu.add_command(label="Create Sample", command=app.create_sample)
    file_menu.add_separator()
    file_menu.add_command(label="Save Progress", command=app.save_progress, accelerator="Ctrl+S")
    file_menu.add_command(label="Load Progress", command=app.load_progress)
    file_menu.add_command(label="Export Image", command=app.export_image)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit)

    edit_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Edit", menu=edit_menu)
    edit_menu.add_command(label="Undo", command=app.undo, accelerator="Ctrl+Z")
    edit_menu.add_command(label="Redo", command=app.redo, accelerator="Ctrl+Y")
    edit_menu.add_separator()
    edit_menu.add_command(label="Clear All", command=app.clear_all)

    anim_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Animation", menu=anim_menu)
    anim_menu.add_command(label="Play/Pause", command=app.toggle_animation, accelerator="Space")
    anim_menu.add_command(label="Stop", command=app.stop_animation)
    anim_menu.add_command(label="Fill Next", command=app.fill_next_region)
    anim_menu.add_separator()
    anim_menu.add_command(label="Record Full Animation", command=app.record_full_animation)

    # Appearance menu
    appearance_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Appearance", menu=appearance_menu)
    
    def set_appearance(mode):
        ctk.set_appearance_mode(mode)
    
    appearance_menu.add_command(label="Light Mode", command=lambda: set_appearance("light"))
    appearance_menu.add_command(label="Dark Mode", command=lambda: set_appearance("dark"))
    appearance_menu.add_command(label="System", command=lambda: set_appearance("system"))

    help_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(label="How to Use", command=lambda: messagebox.showinfo(
        "How to Use",
        "🎨 Color by Number Pro\n\n"
        "1. Load an image or create a sample\n"
        "2. Adjust colors and options\n"
        "3. Click 'Generate Template'\n"
        "4. Select a color from the palette\n"
        "5. Click on regions to fill them\n\n"
        "✨ Features:\n"
        "• Modern CustomTkinter UI\n"
        "• Better color matching to original\n"
        "• No more white micro holes\n"
        "• Original image preview\n"
        "• View mode switching\n"
        "• Dark/Light mode support\n\n"
        "⌨️ Shortcuts:\n"
        "• Space: Play/Pause animation\n"
        "• Ctrl+Z: Undo\n"
        "• Ctrl+Y: Redo\n"
        "• Scroll: Zoom\n"
        "• Right-drag: Pan"
    ))

    root.mainloop()


if __name__ == "__main__":
    main()