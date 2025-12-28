import sys
import os

# Fix for compiled executable - set working directory
if getattr(sys, 'frozen', False) or '__compiled__' in globals():
    # Running as compiled executable
    application_path = os.path.dirname(sys.executable)
    os.chdir(application_path)
else:
    # Running as script
    application_path = os.path.dirname(os.path.abspath(__file__))

# Now import the rest
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter
import numpy as np
from sklearn.cluster import KMeans
from collections import defaultdict, Counter
import cv2
from scipy import ndimage
import json
import os
import random
import time
from datetime import datetime


class ColorByNumberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎨 Happy Coloring - Color by Number Pro")
        self.root.geometry("1600x1000")
        self.root.configure(bg="#1a1a2e")
        
        # App state
        self.original_image = None
        self.processed_image = None
        self.template_image = None
        self.display_image = None
        self.color_palette = {}
        self.original_colors = {}  # Store original image colors for comparison
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
        self.view_mode = tk.StringVar(value="template")  # template, progress, original
        
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
        
        # Canvas drag state
        self.drag_start = None
        self.is_panning = False
        
        # Color matching options
        self.use_exact_colors = tk.BooleanVar(value=True)
        self.fill_micro_holes = tk.BooleanVar(value=True)
        self.min_region_size = tk.IntVar(value=30)
        
        self.setup_styles()
        self.setup_ui()
        self.setup_bindings()
        
    def setup_styles(self):
        """Setup modern styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Color scheme
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
            'error': '#ff4444'
        }
        
        style.configure('TFrame', background=self.colors['bg_dark'])
        style.configure('TLabel', background=self.colors['bg_dark'], 
                       foreground=self.colors['text'], font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=8)
        style.configure('Header.TLabel', font=('Segoe UI', 18, 'bold'), 
                       foreground=self.colors['accent'])
        style.configure('SubHeader.TLabel', font=('Segoe UI', 11), 
                       foreground=self.colors['accent2'])
        style.configure('Status.TLabel', font=('Segoe UI', 9), 
                       foreground=self.colors['text_dim'])
        style.configure('Success.TLabel', foreground=self.colors['success'])
        style.configure('Warning.TLabel', foreground=self.colors['warning'])
        
        style.configure('TLabelframe', background=self.colors['bg_dark'])
        style.configure('TLabelframe.Label', background=self.colors['bg_dark'],
                       foreground=self.colors['accent2'], font=('Segoe UI', 10, 'bold'))
        
        style.configure('TCheckbutton', background=self.colors['bg_dark'],
                       foreground=self.colors['text'])
        style.configure('TRadiobutton', background=self.colors['bg_dark'],
                       foreground=self.colors['text'])
        
    def setup_ui(self):
        """Setup the main UI components"""
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls
        self.setup_left_panel()
        
        # Center panel - Canvas
        self.setup_center_panel()
        
        # Right panel - Palette & Preview
        self.setup_right_panel()
        
        # Status bar
        self.setup_status_bar()
        
    def setup_left_panel(self):
        """Setup left control panel"""
        self.left_panel = ttk.Frame(self.main_frame, width=320)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self.left_panel.pack_propagate(False)
        
        # Scrollable container
        left_canvas = tk.Canvas(self.left_panel, bg=self.colors['bg_dark'], 
                               highlightthickness=0, width=300)
        left_scrollbar = ttk.Scrollbar(self.left_panel, orient=tk.VERTICAL, 
                                       command=left_canvas.yview)
        self.left_scrollable = ttk.Frame(left_canvas)
        
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        left_canvas.create_window((0, 0), window=self.left_scrollable, anchor=tk.NW, width=290)
        self.left_scrollable.bind("<Configure>", 
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        left_canvas.bind_all("<MouseWheel>", _on_mousewheel, add='+')
        
        # Header
        header = ttk.Label(self.left_scrollable, text="🎨 Color by Number", 
                          style='Header.TLabel')
        header.pack(pady=(0, 15))
        
        # File operations
        self.setup_file_frame()
        
        # Template settings
        self.setup_settings_frame()
        
        # Advanced options
        self.setup_advanced_frame()
        
        # Animation controls
        self.setup_animation_frame()
        
        # Recording controls
        self.setup_recording_frame()
        
        # Tools
        self.setup_tools_frame()
        
        # View controls
        self.setup_view_frame()
        
    def setup_file_frame(self):
        """Setup file operations frame"""
        file_frame = ttk.LabelFrame(self.left_scrollable, text="📁 File Operations", padding=10)
        file_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Button(file_frame, text="📂 Load Image", 
                  command=self.load_image).pack(fill=tk.X, pady=2)
        ttk.Button(file_frame, text="🎲 Sample Image", 
                  command=self.create_sample).pack(fill=tk.X, pady=2)
        
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="💾 Save", 
                  command=self.save_progress).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(btn_frame, text="📥 Load", 
                  command=self.load_progress).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(btn_frame, text="🖼️ Export", 
                  command=self.export_image).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
    def setup_settings_frame(self):
        """Setup template settings frame"""
        settings_frame = ttk.LabelFrame(self.left_scrollable, text="⚙️ Template Settings", padding=10)
        settings_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Number of colors
        ttk.Label(settings_frame, text="Number of Colors:").pack(anchor=tk.W)
        color_frame = ttk.Frame(settings_frame)
        color_frame.pack(fill=tk.X)
        
        self.color_count_var = tk.IntVar(value=10)
        color_slider = ttk.Scale(color_frame, from_=5, to=25, variable=self.color_count_var,
                                orient=tk.HORIZONTAL, command=self.on_color_count_change)
        color_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.color_count_label = ttk.Label(color_frame, text="10", width=3)
        self.color_count_label.pack(side=tk.RIGHT)
        
        # Generate button
        self.generate_btn = ttk.Button(settings_frame, text="🔄 Generate Template",
                                       command=self.generate_template)
        self.generate_btn.pack(fill=tk.X, pady=(10, 0))
        
    def setup_advanced_frame(self):
        """Setup advanced options frame"""
        adv_frame = ttk.LabelFrame(self.left_scrollable, text="🔧 Advanced Options", padding=10)
        adv_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Exact color matching
        ttk.Checkbutton(adv_frame, text="Use exact colors from image",
                       variable=self.use_exact_colors).pack(anchor=tk.W)
        
        # Fill micro holes
        ttk.Checkbutton(adv_frame, text="Fill micro holes",
                       variable=self.fill_micro_holes).pack(anchor=tk.W)
        
        # Minimum region size
        ttk.Label(adv_frame, text="Min region size:").pack(anchor=tk.W, pady=(5, 0))
        size_frame = ttk.Frame(adv_frame)
        size_frame.pack(fill=tk.X)
        
        size_slider = ttk.Scale(size_frame, from_=10, to=200, variable=self.min_region_size,
                               orient=tk.HORIZONTAL)
        size_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.size_label = ttk.Label(size_frame, text="30", width=4)
        self.size_label.pack(side=tk.RIGHT)
        
        self.min_region_size.trace('w', lambda *args: self.size_label.config(
            text=str(self.min_region_size.get())))
        
    def setup_animation_frame(self):
        """Setup animation controls"""
        anim_frame = ttk.LabelFrame(self.left_scrollable, text="🎬 Animation", padding=10)
        anim_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Speed control
        ttk.Label(anim_frame, text="Speed (ms):").pack(anchor=tk.W)
        speed_frame = ttk.Frame(anim_frame)
        speed_frame.pack(fill=tk.X)
        
        self.speed_var = tk.IntVar(value=200)
        speed_slider = ttk.Scale(speed_frame, from_=20, to=500, variable=self.speed_var,
                                orient=tk.HORIZONTAL, command=self.on_speed_change)
        speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.speed_label = ttk.Label(speed_frame, text="200", width=4)
        self.speed_label.pack(side=tk.RIGHT)
        
        # Fill order
        ttk.Label(anim_frame, text="Fill Order:").pack(anchor=tk.W, pady=(5, 0))
        self.order_var = tk.StringVar(value="random")
        order_frame = ttk.Frame(anim_frame)
        order_frame.pack(fill=tk.X)
        
        for text, value in [("Random", "random"), ("By Color", "by_color"), ("By Size", "by_size")]:
            ttk.Radiobutton(order_frame, text=text, variable=self.order_var,
                           value=value).pack(side=tk.LEFT, padx=2)
        
        # Control buttons
        btn_frame = ttk.Frame(anim_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.play_btn = ttk.Button(btn_frame, text="▶", width=4, command=self.start_animation)
        self.play_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        self.pause_btn = ttk.Button(btn_frame, text="⏸", width=4, command=self.pause_animation,
                                   state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹", width=4, command=self.stop_animation,
                                  state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        self.next_btn = ttk.Button(btn_frame, text="⏭", width=4, command=self.fill_next_region)
        self.next_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
    def setup_recording_frame(self):
        """Setup recording controls"""
        rec_frame = ttk.LabelFrame(self.left_scrollable, text="🎥 Recording", padding=10)
        rec_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # FPS control
        ttk.Label(rec_frame, text="FPS:").pack(anchor=tk.W)
        fps_frame = ttk.Frame(rec_frame)
        fps_frame.pack(fill=tk.X)
        
        self.fps_var = tk.IntVar(value=10)
        fps_slider = ttk.Scale(fps_frame, from_=5, to=30, variable=self.fps_var,
                              orient=tk.HORIZONTAL)
        fps_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.fps_label = ttk.Label(fps_frame, text="10", width=3)
        self.fps_label.pack(side=tk.RIGHT)
        self.fps_var.trace('w', lambda *args: self.fps_label.config(text=str(self.fps_var.get())))
        
        # Control buttons
        btn_frame = ttk.Frame(rec_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.rec_btn = ttk.Button(btn_frame, text="🔴 Record", command=self.toggle_recording)
        self.rec_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        self.save_video_btn = ttk.Button(btn_frame, text="💾 Save", command=self.save_video,
                                        state=tk.DISABLED)
        self.save_video_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        # Quick actions
        ttk.Button(rec_frame, text="🎬 Record Full Animation",
                  command=self.record_full_animation).pack(fill=tk.X, pady=2)
        
        # Status
        self.rec_status = ttk.Label(rec_frame, text="Ready", style='Status.TLabel')
        self.rec_status.pack()
        
    def setup_tools_frame(self):
        """Setup tools frame"""
        tools_frame = ttk.LabelFrame(self.left_scrollable, text="🛠️ Tools", padding=10)
        tools_frame.pack(fill=tk.X, pady=5, padx=5)
        
        btn_frame = ttk.Frame(tools_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="↩️", width=4, command=self.undo).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(btn_frame, text="↪️", width=4, command=self.redo).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(btn_frame, text="🗑️", width=4, command=self.clear_all).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(btn_frame, text="💡", width=4, command=self.show_hint).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
    def setup_view_frame(self):
        """Setup view controls"""
        view_frame = ttk.LabelFrame(self.left_scrollable, text="🔍 View", padding=10)
        view_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # View mode
        mode_frame = ttk.Frame(view_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 5))
        
        for text, value in [("Template", "template"), ("Progress", "progress"), ("Original", "original")]:
            ttk.Radiobutton(mode_frame, text=text, variable=self.view_mode,
                           value=value, command=self.update_view_mode).pack(side=tk.LEFT, padx=2)
        
        # Zoom controls
        zoom_frame = ttk.Frame(view_frame)
        zoom_frame.pack(fill=tk.X)
        
        ttk.Button(zoom_frame, text="➕", width=4, 
                  command=lambda: self.zoom(1.25)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(zoom_frame, text="➖", width=4,
                  command=lambda: self.zoom(0.8)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(zoom_frame, text="🔄", width=4,
                  command=self.reset_view).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        self.zoom_label = ttk.Label(view_frame, text="100%", style='Status.TLabel')
        self.zoom_label.pack()
        
        # Progress
        ttk.Label(view_frame, text="Progress:", style='Status.TLabel').pack(anchor=tk.W, pady=(10, 0))
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(view_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X)
        self.progress_label = ttk.Label(view_frame, text="0%", style='Status.TLabel')
        self.progress_label.pack()
        
    def setup_center_panel(self):
        """Setup center canvas panel"""
        self.center_panel = ttk.Frame(self.main_frame)
        self.center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Canvas frame with border
        canvas_container = tk.Frame(self.center_panel, bg=self.colors['accent'], padx=2, pady=2)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_container, bg=self.colors['bg_medium'], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        self.instructions = ttk.Label(self.center_panel,
            text="📌 Load image → Generate template → Select color → Click to fill | Scroll: Zoom | Right-drag: Pan",
            style='SubHeader.TLabel')
        self.instructions.pack(pady=5)
        
    def setup_right_panel(self):
        """Setup right panel with palette and preview"""
        self.right_panel = ttk.Frame(self.main_frame, width=220)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.right_panel.pack_propagate(False)
        
        # Original image preview
        preview_frame = ttk.LabelFrame(self.right_panel, text="📷 Original", padding=5)
        preview_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.preview_canvas = tk.Canvas(preview_frame, width=190, height=120,
                                        bg=self.colors['bg_medium'], highlightthickness=1,
                                        highlightbackground=self.colors['accent2'])
        self.preview_canvas.pack()
        
        # Palette header
        ttk.Label(self.right_panel, text="🎨 Color Palette", style='Header.TLabel').pack(pady=(0, 5))
        
        # Palette container with scrollbar
        palette_container = ttk.Frame(self.right_panel)
        palette_container.pack(fill=tk.BOTH, expand=True)
        
        palette_canvas = tk.Canvas(palette_container, bg=self.colors['bg_dark'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(palette_container, orient=tk.VERTICAL, command=palette_canvas.yview)
        
        self.palette_frame = ttk.Frame(palette_canvas)
        
        palette_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        palette_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        palette_canvas.create_window((0, 0), window=self.palette_frame, anchor=tk.NW, width=190)
        self.palette_frame.bind("<Configure>",
            lambda e: palette_canvas.configure(scrollregion=palette_canvas.bbox("all")))
        
        self.palette_canvas = palette_canvas
        
        # Selected color display
        selected_frame = ttk.LabelFrame(self.right_panel, text="✓ Selected", padding=5)
        selected_frame.pack(fill=tk.X, pady=10)
        
        self.selected_color_canvas = tk.Canvas(selected_frame, width=180, height=50,
                                               bg=self.colors['bg_medium'], highlightthickness=1)
        self.selected_color_canvas.pack()
        
        self.selected_color_label = ttk.Label(selected_frame, text="None selected")
        self.selected_color_label.pack()
        
    def setup_status_bar(self):
        """Setup status bar"""
        status_frame = tk.Frame(self.root, bg=self.colors['bg_light'], height=25)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = tk.Label(status_frame, text="Ready", bg=self.colors['bg_light'],
                                     fg=self.colors['text_dim'], font=('Segoe UI', 9))
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.region_count_label = tk.Label(status_frame, text="Regions: 0",
                                           bg=self.colors['bg_light'], fg=self.colors['text_dim'],
                                           font=('Segoe UI', 9))
        self.region_count_label.pack(side=tk.RIGHT, padx=10)
        
    def setup_bindings(self):
        """Setup event bindings"""
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
        """Update status bar"""
        colors = {
            "info": self.colors['text_dim'],
            "success": self.colors['success'],
            "warning": self.colors['warning'],
            "error": self.colors['error']
        }
        self.status_label.config(text=message, fg=colors.get(status_type, self.colors['text_dim']))
        self.root.update()
        
    def on_color_count_change(self, value):
        """Update color count label"""
        count = int(float(value))
        self.color_count_label.config(text=str(count))
        self.num_colors = count
        
    def on_speed_change(self, value):
        """Update animation speed"""
        speed = int(float(value))
        self.animation_speed = speed
        self.speed_label.config(text=str(speed))
        
    def update_view_mode(self):
        """Update display based on view mode"""
        mode = self.view_mode.get()
        
        if mode == "original" and self.original_image:
            self.display_image = self.original_image.copy()
        elif mode == "template" and self.template_image:
            self.display_image = self.template_image.copy()
            # Overlay colored regions
            if self.colored_regions:
                img_array = np.array(self.display_image)
                for region_id in self.colored_regions:
                    if region_id in self.regions:
                        region_info = self.regions[region_id]
                        color = self.color_palette[region_info['color_num']]
                        img_array[region_info['mask']] = color
                self.display_image = Image.fromarray(img_array)
        elif mode == "progress" and self.processed_image:
            self.display_image = self.processed_image.copy()
            
        self.update_canvas()
        
    def create_sample(self):
        """Create a sample image for testing"""
        width, height = 500, 500
        img = Image.new('RGB', (width, height), '#87CEEB')
        draw = ImageDraw.Draw(img)
        
        # Sky gradient effect
        for y in range(height // 2):
            r = int(135 + (y / (height/2)) * 30)
            g = int(206 + (y / (height/2)) * 20)
            b = int(235 + (y / (height/2)) * 10)
            draw.line([(0, y), (width, y)], fill=(min(255, r), min(255, g), min(255, b)))
        
        # Sun with gradient
        sun_center = (400, 80)
        for r in range(60, 0, -2):
            intensity = int(255 - (60-r) * 2)
            draw.ellipse([sun_center[0]-r, sun_center[1]-r, sun_center[0]+r, sun_center[1]+r],
                        fill=(255, intensity, 0))
        
        # Mountains
        draw.polygon([(0, 350), (150, 180), (300, 350)], fill='#2E7D32', outline='#1B5E20')
        draw.polygon([(180, 350), (350, 150), (520, 350)], fill='#43A047', outline='#2E7D32')
        
        # Grass field
        draw.rectangle([0, 350, 500, 500], fill='#66BB6A')
        
        # House
        draw.rectangle([140, 260, 280, 380], fill='#8D6E63', outline='#5D4037', width=2)
        draw.polygon([(130, 260), (210, 180), (290, 260)], fill='#C62828', outline='#B71C1C', width=2)
        draw.rectangle([190, 310, 230, 380], fill='#5D4037')  # Door
        draw.rectangle([155, 280, 180, 310], fill='#81D4FA', outline='#0288D1', width=2)  # Window
        draw.rectangle([240, 280, 265, 310], fill='#81D4FA', outline='#0288D1', width=2)  # Window
        
        # Tree
        draw.rectangle([380, 280, 410, 380], fill='#6D4C41')
        draw.ellipse([340, 180, 450, 300], fill='#2E7D32')
        
        # Flowers
        flower_colors = ['#E91E63', '#FF5722', '#FFEB3B', '#9C27B0']
        for i, (x, y) in enumerate([(60, 370), (100, 385), (420, 360), (460, 375)]):
            draw.ellipse([x-12, y-12, x+12, y+12], fill=flower_colors[i % len(flower_colors)])
            draw.ellipse([x-5, y-5, x+5, y+5], fill='#FFEB3B')
        
        # Clouds
        for cx, cy in [(80, 70), (220, 50), (320, 90)]:
            for dx, dy in [(0, 0), (25, -8), (50, 0), (15, 12), (35, 10)]:
                draw.ellipse([cx+dx-18, cy+dy-12, cx+dx+18, cy+dy+12], fill='white')
        
        self.original_image = img
        self.update_preview()
        self.display_original()
        self.set_status("Sample image created! Click 'Generate Template' to continue.", "success")
        
    def load_image(self):
        """Load an image file"""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")]
        )
        
        if file_path:
            try:
                self.set_status("Loading image...", "info")
                self.original_image = Image.open(file_path).convert("RGB")
                
                # Resize if too large
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
        """Update the original image preview"""
        if self.original_image:
            # Create thumbnail for preview
            preview = self.original_image.copy()
            preview.thumbnail((190, 120), Image.LANCZOS)
            
            self.preview_photo = ImageTk.PhotoImage(preview)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(95, 60, anchor=tk.CENTER, image=self.preview_photo)
            
    def display_original(self):
        """Display the original image on canvas"""
        if self.original_image:
            self.display_image = self.original_image.copy()
            self.view_mode.set("original")
            self.update_canvas()
            
    def generate_template(self):
        """Generate color-by-number template from the loaded image"""
        if not self.original_image:
            messagebox.showwarning("Warning", "Please load an image first!")
            return
            
        try:
            self.set_status("Generating template...", "info")
            self.root.config(cursor="wait")
            self.root.update()
            
            # Stop any ongoing animation
            self.stop_animation()
            
            # Convert to numpy array
            img_array = np.array(self.original_image)
            
            # Apply bilateral filter to reduce noise while preserving edges
            img_filtered = cv2.bilateralFilter(img_array, 9, 75, 75)
            
            # Reshape for clustering
            pixels = img_filtered.reshape(-1, 3)
            
            # Color quantization using KMeans
            n_colors = self.num_colors
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10, max_iter=300)
            labels = kmeans.fit_predict(pixels)
            
            # Get color centers
            cluster_centers = kmeans.cluster_centers_.astype(int)
            
            # Create color palette with better color matching
            self.color_palette = {}
            self.original_colors = {}
            
            for i in range(n_colors):
                cluster_mask = (labels == i)
                cluster_pixels = pixels[cluster_mask]
                
                if self.use_exact_colors.get() and len(cluster_pixels) > 0:
                    # Find the most common color in this cluster
                    # Convert to tuple for counting
                    pixel_tuples = [tuple(p) for p in cluster_pixels]
                    color_counts = Counter(pixel_tuples)
                    
                    # Get top colors and find one closest to centroid
                    top_colors = color_counts.most_common(min(10, len(color_counts)))
                    
                    # Choose the most common color that's close to the centroid
                    centroid = cluster_centers[i]
                    best_color = top_colors[0][0]
                    best_dist = float('inf')
                    
                    for color, count in top_colors:
                        dist = np.sqrt(sum((c1-c2)**2 for c1, c2 in zip(color, centroid)))
                        if count > color_counts.most_common(1)[0][1] * 0.5:  # At least 50% as common
                            if dist < best_dist:
                                best_dist = dist
                                best_color = color
                    
                    # Also try median color for more representative result
                    median_color = tuple(np.median(cluster_pixels, axis=0).astype(int))
                    
                    # Use the color with better saturation (more vibrant)
                    best_sat = max(best_color) - min(best_color)
                    median_sat = max(median_color) - min(median_color)
                    
                    if median_sat > best_sat * 1.2:
                        final_color = median_color
                    else:
                        final_color = best_color
                        
                    self.color_palette[i + 1] = final_color
                else:
                    self.color_palette[i + 1] = tuple(cluster_centers[i])
                
                self.original_colors[i + 1] = tuple(cluster_centers[i])
            
            # Reshape labels back to image shape
            self.region_labels = labels.reshape(img_array.shape[:2])
            
            # Create segmented regions with micro hole filling
            self.regions = self.create_regions()
            
            # Fill any remaining micro holes
            if self.fill_micro_holes.get():
                self.fill_remaining_holes()
            
            # Create template image
            self.create_template_image()
            
            # Store processed image for progress view
            self.processed_image = self.create_colored_image()
            
            # Reset coloring state
            self.colored_regions = {}
            self.history = []
            self.history_index = -1
            self.recorded_frames = []
            
            # Update UI
            self.update_palette()
            self.view_mode.set("template")
            self.update_canvas()
            self.update_progress()
            
            self.root.config(cursor="")
            self.region_count_label.config(text=f"Regions: {len(self.regions)}")
            self.set_status(f"Template generated: {n_colors} colors, {len(self.regions)} regions", "success")
            
        except Exception as e:
            self.root.config(cursor="")
            self.set_status(f"Failed to generate template: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to generate template: {str(e)}")
            
    def create_colored_image(self):
        """Create fully colored image for reference"""
        height, width = self.region_labels.shape
        colored = np.zeros((height, width, 3), dtype=np.uint8)
        
        for color_num, color in self.color_palette.items():
            mask = (self.region_labels == (color_num - 1))
            colored[mask] = color
            
        return Image.fromarray(colored)
            
    def create_regions(self):
        """Create connected regions for each color with micro hole handling"""
        regions = {}
        region_id = 0
        min_size = self.min_region_size.get()
        
        height, width = self.region_labels.shape
        all_assigned = np.zeros((height, width), dtype=bool)
        
        for color_num in range(self.num_colors):
            # Create mask for this color
            mask = (self.region_labels == color_num).astype(np.uint8)
            
            # Apply morphological closing to fill small holes within regions
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            
            # Find connected components
            labeled, num_features = ndimage.label(mask)
            
            for i in range(1, num_features + 1):
                region_mask = (labeled == i)
                region_size = np.sum(region_mask)
                
                if region_size >= min_size:
                    # Fill small holes within this region
                    filled_mask = ndimage.binary_fill_holes(region_mask)
                    
                    # Calculate centroid
                    centroid = ndimage.center_of_mass(filled_mask)
                    
                    regions[region_id] = {
                        'mask': filled_mask,
                        'color_num': color_num + 1,
                        'size': np.sum(filled_mask),
                        'centroid': centroid
                    }
                    
                    all_assigned |= filled_mask
                    region_id += 1
        
        # Handle orphan pixels (not assigned to any region)
        orphan_mask = ~all_assigned
        if np.any(orphan_mask):
            self.assign_orphan_pixels(regions, orphan_mask)
            
        return regions
    
    def assign_orphan_pixels(self, regions, orphan_mask):
        """Assign orphan pixels to nearest regions"""
        if not regions:
            return
            
        height, width = orphan_mask.shape
        orphan_coords = np.where(orphan_mask)
        
        if len(orphan_coords[0]) == 0:
            return
        
        # Create a combined mask of all regions
        all_regions_mask = np.zeros((height, width), dtype=np.int32)
        for region_id, region_info in regions.items():
            all_regions_mask[region_info['mask']] = region_id + 1
        
        # Use distance transform to find nearest region for each orphan pixel
        # Dilate existing regions to claim nearby orphan pixels
        for _ in range(10):  # Iteratively expand regions
            kernel = np.ones((3, 3), np.uint8)
            dilated = cv2.dilate(all_regions_mask.astype(np.uint8), kernel, iterations=1)
            
            # Only expand into orphan areas
            new_assignments = dilated.astype(np.int32)
            new_assignments[all_regions_mask > 0] = all_regions_mask[all_regions_mask > 0]
            
            # Update region masks
            for region_id, region_info in regions.items():
                new_mask = (new_assignments == region_id + 1)
                if np.sum(new_mask) > np.sum(region_info['mask']):
                    region_info['mask'] = new_mask
                    region_info['size'] = np.sum(new_mask)
            
            all_regions_mask = new_assignments
            
            # Check if all orphans are assigned
            if not np.any((all_regions_mask == 0) & orphan_mask):
                break
    
    def fill_remaining_holes(self):
        """Fill any remaining unassigned pixels"""
        if not self.regions:
            return
            
        height, width = self.region_labels.shape
        assigned = np.zeros((height, width), dtype=bool)
        
        for region_info in self.regions.values():
            assigned |= region_info['mask']
        
        unassigned = ~assigned
        
        if np.any(unassigned):
            # Find the nearest region for each unassigned pixel
            # Use the original labels to guide assignment
            unassigned_coords = np.where(unassigned)
            
            for y, x in zip(unassigned_coords[0], unassigned_coords[1]):
                original_label = self.region_labels[y, x]
                target_color = original_label + 1
                
                # Find region with matching color that's closest
                best_region = None
                best_dist = float('inf')
                
                for region_id, region_info in self.regions.items():
                    if region_info['color_num'] == target_color:
                        cy, cx = region_info['centroid']
                        dist = (y - cy) ** 2 + (x - cx) ** 2
                        if dist < best_dist:
                            best_dist = dist
                            best_region = region_id
                
                # If no matching color region, find any closest region
                if best_region is None:
                    for region_id, region_info in self.regions.items():
                        cy, cx = region_info['centroid']
                        dist = (y - cy) ** 2 + (x - cx) ** 2
                        if dist < best_dist:
                            best_dist = dist
                            best_region = region_id
                
                if best_region is not None:
                    # Add pixel to region
                    mask = self.regions[best_region]['mask'].copy()
                    mask[y, x] = True
                    self.regions[best_region]['mask'] = mask
                    self.regions[best_region]['size'] += 1
        
    def create_template_image(self):
        """Create the template image with outlines and numbers"""
        height, width = self.region_labels.shape
        
        # Create white background
        self.template_image = Image.new('RGB', (width, height), 'white')
        
        # Draw region outlines
        edges = self.detect_edges()
        
        # Convert template to array for edge drawing
        template_array = np.array(self.template_image)
        template_array[edges] = [60, 60, 60]  # Dark gray edges
        
        # Ensure no white holes - fill with light gray for unassigned areas
        assigned = np.zeros((height, width), dtype=bool)
        for region_info in self.regions.values():
            assigned |= region_info['mask']
        
        # Fill unassigned areas with nearest region color (light version)
        if np.any(~assigned):
            unassigned_coords = np.where(~assigned)
            for y, x in zip(unassigned_coords[0], unassigned_coords[1]):
                if not edges[y, x]:
                    template_array[y, x] = [240, 240, 240]  # Light gray for safety
        
        self.template_image = Image.fromarray(template_array)
        draw = ImageDraw.Draw(self.template_image)
        
        # Try to load a font
        try:
            font_size = max(10, min(width, height) // 50)
            font = ImageFont.truetype("arial.ttf", font_size)
            small_font = ImageFont.truetype("arial.ttf", max(8, font_size - 2))
        except:
            font = ImageFont.load_default()
            small_font = font
        
        # Draw numbers in regions
        for region_id, region_info in self.regions.items():
            centroid = region_info['centroid']
            color_num = region_info['color_num']
            size = region_info['size']
            
            # Adjust font based on region size
            if size > 500:
                use_font = font
            elif size > 200:
                use_font = small_font
            else:
                continue  # Skip tiny regions
                
            y, x = int(centroid[0]), int(centroid[1])
            text = str(color_num)
            
            # Get text bounding box
            bbox = draw.textbbox((x, y), text, font=use_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Center the text
            text_x = x - text_width // 2
            text_y = y - text_height // 2
            
            # Check if position is within region
            if 0 <= y < height and 0 <= x < width:
                # Draw text outline for visibility
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx != 0 or dy != 0:
                            draw.text((text_x + dx, text_y + dy), text, fill='white', font=use_font)
                draw.text((text_x, text_y), text, fill='#333333', font=use_font)
        
        self.display_image = self.template_image.copy()
        
    def detect_edges(self):
        """Detect edges between different colored regions"""
        labels = self.region_labels.astype(np.float32)
        
        sobel_x = cv2.Sobel(labels, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(labels, cv2.CV_64F, 0, 1, ksize=3)
        
        edges = np.sqrt(sobel_x**2 + sobel_y**2) > 0
        
        # Ensure consistent edge thickness
        kernel = np.ones((2, 2), np.uint8)
        edges = cv2.dilate(edges.astype(np.uint8), kernel, iterations=1).astype(bool)
        
        return edges
        
    def update_palette(self):
        """Update the color palette display"""
        for widget in self.palette_frame.winfo_children():
            widget.destroy()
            
        self.palette_buttons = {}
        
        for num, color in self.color_palette.items():
            frame = tk.Frame(self.palette_frame, bg=self.colors['bg_dark'], pady=2)
            frame.pack(fill=tk.X, padx=2)
            
            color_hex = '#{:02x}{:02x}{:02x}'.format(*color)
            
            # Number
            num_label = tk.Label(frame, text=str(num), font=('Segoe UI', 11, 'bold'),
                                bg=self.colors['bg_dark'], fg='white', width=2)
            num_label.pack(side=tk.LEFT)
            
            # Color button (shows palette color)
            color_btn = tk.Button(frame, bg=color_hex, width=6, height=1,
                                 relief=tk.RAISED, bd=2, activebackground=color_hex,
                                 command=lambda n=num: self.select_color(n))
            color_btn.pack(side=tk.LEFT, padx=2)
            
            # Original color indicator (small square)
            if num in self.original_colors:
                orig_hex = '#{:02x}{:02x}{:02x}'.format(*self.original_colors[num])
                orig_indicator = tk.Canvas(frame, width=12, height=20, 
                                          bg=self.colors['bg_dark'], highlightthickness=0)
                orig_indicator.pack(side=tk.LEFT, padx=1)
                orig_indicator.create_rectangle(0, 2, 12, 18, fill=orig_hex, outline='gray')
            
            # Count and progress
            count = sum(1 for r in self.regions.values() if r['color_num'] == num)
            count_label = tk.Label(frame, text=f"({count})", font=('Segoe UI', 8),
                                  bg=self.colors['bg_dark'], fg='gray')
            count_label.pack(side=tk.LEFT, padx=2)
            
            progress_label = tk.Label(frame, text="○", font=('Segoe UI', 12),
                                     bg=self.colors['bg_dark'], fg='gray')
            progress_label.pack(side=tk.RIGHT)
            
            self.palette_buttons[num] = {
                'frame': frame,
                'button': color_btn,
                'progress': progress_label,
                'color_hex': color_hex
            }
            
    def select_color(self, color_num):
        """Select a color from the palette"""
        self.selected_color_num = color_num
        
        # Update button appearances
        for num, widgets in self.palette_buttons.items():
            if num == color_num:
                widgets['button'].config(relief=tk.SUNKEN, bd=4)
                widgets['frame'].config(bg=self.colors['bg_light'])
            else:
                widgets['button'].config(relief=tk.RAISED, bd=2)
                widgets['frame'].config(bg=self.colors['bg_dark'])
        
        # Update selected color display
        color = self.color_palette.get(color_num, (128, 128, 128))
        color_hex = '#{:02x}{:02x}{:02x}'.format(*color)
        
        self.selected_color_canvas.delete("all")
        self.selected_color_canvas.create_rectangle(5, 5, 175, 45, fill=color_hex, outline='white')
        self.selected_color_canvas.create_text(90, 25, text=f"#{color_num}",
                                               fill='white' if sum(color) < 400 else 'black',
                                               font=('Segoe UI', 12, 'bold'))
        
        self.selected_color_label.config(text=f"RGB: {color}")
        self.set_status(f"Selected color #{color_num}", "info")
        
    def on_canvas_click(self, event):
        """Handle canvas click for coloring"""
        if self.is_animating:
            return
            
        if not self.regions or not self.selected_color_num:
            if not self.regions:
                messagebox.showinfo("Info", "Please generate a template first!")
            else:
                messagebox.showinfo("Info", "Please select a color from the palette!")
            return
            
        # Convert canvas coordinates to image coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        img_x = int((canvas_x - self.pan_offset[0]) / self.zoom_level)
        img_y = int((canvas_y - self.pan_offset[1]) / self.zoom_level)
        
        # Find clicked region
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
        """Find region at given coordinates"""
        if not self.regions:
            return None
            
        height, width = self.region_labels.shape
        if 0 <= x < width and 0 <= y < height:
            for region_id, region_info in self.regions.items():
                if region_id not in self.colored_regions and region_info['mask'][y, x]:
                    return region_id
        return None
        
    def fill_region(self, region_id, save_history=True):
        """Fill a region with its color"""
        if save_history:
            self.save_state()
        
        region_info = self.regions[region_id]
        color_num = region_info['color_num']
        color = self.color_palette[color_num]
        
        self.colored_regions[region_id] = color_num
        
        # Update display image
        img_array = np.array(self.display_image)
        mask = region_info['mask']
        img_array[mask] = color
        self.display_image = Image.fromarray(img_array)
        
        self.update_palette_progress()
        
    def flash_region(self, region_id, color):
        """Flash a region to indicate wrong color"""
        original = self.display_image.copy()
        
        region_info = self.regions[region_id]
        img_array = np.array(self.display_image)
        mask = region_info['mask']
        
        # Flash with red tint
        img_array[mask] = [255, 100, 100]
        self.display_image = Image.fromarray(img_array)
        self.update_canvas()
        
        self.root.after(200, lambda: self.restore_image(original))
        
    def restore_image(self, image):
        """Restore image after flash"""
        self.display_image = image
        self.update_canvas()
        
    # ==================== Animation Methods ====================
    
    def get_fill_order(self):
        """Get the order to fill regions based on selected method"""
        uncolored = [r for r in self.regions if r not in self.colored_regions]
        
        if self.order_var.get() == "random":
            random.shuffle(uncolored)
        elif self.order_var.get() == "by_color":
            uncolored.sort(key=lambda r: self.regions[r]['color_num'])
        elif self.order_var.get() == "by_size":
            uncolored.sort(key=lambda r: self.regions[r]['size'], reverse=True)
            
        return uncolored
        
    def start_animation(self):
        """Start the auto-complete animation"""
        if not self.regions:
            messagebox.showwarning("Warning", "Please generate a template first!")
            return
            
        if self.is_animating:
            return
            
        self.is_animating = True
        self.animation_paused = False
        
        self.play_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        
        self.fill_order = self.get_fill_order()
        self.current_fill_index = 0
        
        self.set_status("Animation started...", "info")
        self.animate_next()
        
    def animate_next(self):
        """Animate the next region fill"""
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
        
        # Schedule next fill
        self.root.after(self.animation_speed, self.animate_next)
        
    def pause_animation(self):
        """Pause the animation"""
        if self.is_animating:
            self.animation_paused = not self.animation_paused
            
            if self.animation_paused:
                self.pause_btn.config(text="▶")
                self.set_status("Animation paused", "warning")
            else:
                self.pause_btn.config(text="⏸")
                self.set_status("Animation resumed", "info")
                self.animate_next()
                
    def stop_animation(self):
        """Stop the animation"""
        self.is_animating = False
        self.animation_paused = False
        
        self.play_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED, text="⏸")
        self.stop_btn.config(state=tk.DISABLED)
        self.set_status("Animation stopped", "info")
        
    def toggle_animation(self):
        """Toggle animation play/pause with spacebar"""
        if self.is_animating:
            self.pause_animation()
        else:
            self.start_animation()
            
    def fill_next_region(self):
        """Fill the next uncolored region"""
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
        """Toggle video recording"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
            
    def start_recording(self):
        """Start recording frames"""
        if not self.display_image:
            messagebox.showwarning("Warning", "Please generate a template first!")
            return
            
        self.is_recording = True
        self.recorded_frames = []
        self.record_start_time = time.time()
        
        self.rec_btn.config(text="⏹ Stop")
        self.save_video_btn.config(state=tk.DISABLED)
        self.rec_status.config(text="🔴 Recording...", style='Warning.TLabel')
        
        # Capture initial frame
        self.capture_frame()
        self.set_status("Recording started", "warning")
        
    def stop_recording(self):
        """Stop recording"""
        self.is_recording = False
        
        self.rec_btn.config(text="🔴 Record")
        self.save_video_btn.config(state=tk.NORMAL if self.recorded_frames else tk.DISABLED)
        
        duration = time.time() - self.record_start_time if self.record_start_time else 0
        self.rec_status.config(text=f"Recorded {len(self.recorded_frames)} frames ({duration:.1f}s)",
                              style='Status.TLabel')
        self.set_status(f"Recording stopped: {len(self.recorded_frames)} frames", "info")
        
    def capture_frame(self):
        """Capture current frame for recording"""
        if self.is_recording and self.display_image:
            frame = self.display_image.copy()
            self.recorded_frames.append(frame)
            
    def save_video(self):
        """Save recorded frames as video"""
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
            
    def save_as_video(self, file_path):
        """Save frames as MP4/AVI video"""
        if not self.recorded_frames:
            return
            
        frame = self.recorded_frames[0]
        width, height = frame.size
        
        if file_path.lower().endswith('.mp4'):
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        else:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            
        out = cv2.VideoWriter(file_path, fourcc, self.fps_var.get(), (width, height))
        
        for frame in self.recorded_frames:
            frame_array = np.array(frame)
            frame_bgr = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
            out.write(frame_bgr)
            
        out.release()
        
    def save_as_gif(self, file_path):
        """Save frames as animated GIF"""
        if not self.recorded_frames:
            return
            
        duration = int(1000 / self.fps_var.get())
        
        frames = []
        max_size = 500
        
        for frame in self.recorded_frames:
            if max(frame.size) > max_size:
                ratio = max_size / max(frame.size)
                new_size = (int(frame.width * ratio), int(frame.height * ratio))
                frame = frame.resize(new_size, Image.LANCZOS)
            
            frame = frame.convert('P', palette=Image.ADAPTIVE, colors=256)
            frames.append(frame)
            
        frames[0].save(
            file_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0
        )
        
    def record_full_animation(self):
        """Record a full animation from start to finish"""
        if not self.regions:
            messagebox.showwarning("Warning", "Please generate a template first!")
            return
            
        if messagebox.askyesno("Record Animation",
                               "This will clear current progress and record the full coloring animation. Continue?"):
            # Reset to template
            self.colored_regions = {}
            self.display_image = self.template_image.copy()
            self.update_canvas()
            self.update_progress()
            
            # Start recording
            self.start_recording()
            
            # Capture template state
            for _ in range(self.fps_var.get()):
                self.capture_frame()
            
            # Start animation
            self.start_animation()
            
    # ==================== Canvas & Display Methods ====================
    
    def update_canvas(self):
        """Update the canvas display"""
        if not self.display_image:
            return
            
        # Apply zoom
        width = int(self.display_image.width * self.zoom_level)
        height = int(self.display_image.height * self.zoom_level)
        
        resized = self.display_image.resize((width, height), Image.NEAREST)
        
        self.photo = ImageTk.PhotoImage(resized)
        
        self.canvas.delete("all")
        self.canvas.create_image(self.pan_offset[0], self.pan_offset[1],
                                anchor=tk.NW, image=self.photo)
        
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
    def update_progress(self):
        """Update progress bar"""
        if not self.regions:
            return
            
        total_regions = len(self.regions)
        colored_regions = len(self.colored_regions)
        
        progress = (colored_regions / total_regions) * 100 if total_regions > 0 else 0
        self.progress_var.set(progress)
        self.progress_label.config(text=f"{progress:.1f}% ({colored_regions}/{total_regions})")
        
    def update_palette_progress(self):
        """Update palette to show completed colors"""
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
                    widgets['progress'].config(text="✓", fg=self.colors['success'])
                elif progress['done'] > 0:
                    widgets['progress'].config(text="◐", fg=self.colors['warning'])
                else:
                    widgets['progress'].config(text="○", fg="gray")
                    
    def check_completion(self):
        """Check if coloring is complete"""
        return len(self.colored_regions) == len(self.regions)
        
    def on_completion(self):
        """Handle completion of coloring"""
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
        """Save current state for undo"""
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
            
        state = {
            'colored_regions': self.colored_regions.copy(),
            'display_image': self.display_image.copy()
        }
        self.history.append(state)
        self.history_index = len(self.history) - 1
        
    def undo(self):
        """Undo last action"""
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
        """Redo last undone action"""
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
        """Clear all colored regions"""
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
        """Show a hint for the next region to color"""
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
        """Flash a region as a hint"""
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
        """Zoom in or out"""
        new_zoom = self.zoom_level * factor
        if 0.2 <= new_zoom <= 5.0:
            self.zoom_level = new_zoom
            self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
            self.update_canvas()
            
    def reset_view(self):
        """Reset zoom and pan"""
        self.zoom_level = 1.0
        self.pan_offset = [0, 0]
        self.zoom_label.config(text="100%")
        self.update_canvas()
        
    def start_pan(self, event):
        """Start panning"""
        self.drag_start = (event.x, event.y)
        self.is_panning = True
        
    def do_pan(self, event):
        """Pan the canvas"""
        if self.is_panning and self.drag_start:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.pan_offset[0] += dx
            self.pan_offset[1] += dy
            self.drag_start = (event.x, event.y)
            self.update_canvas()
            
    def end_pan(self, event):
        """End panning"""
        self.is_panning = False
        self.drag_start = None
        
    def on_mousewheel(self, event):
        """Handle mouse wheel for zooming"""
        if event.delta > 0:
            self.zoom(1.15)
        else:
            self.zoom(0.85)
            
    # ==================== Save/Load ====================
    
    def save_progress(self):
        """Save current progress to file"""
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
        """Load progress from file"""
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
        """Export the colored image"""
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
    root = tk.Tk()
    app = ColorByNumberApp(root)
    
    # Menu bar
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
        "✨ New Features:\n"
        "• Better color matching to original\n"
        "• No more white micro holes\n"
        "• Original image preview\n"
        "• View mode switching\n\n"
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