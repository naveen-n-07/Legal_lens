"""
config.py - Configuration settings for AI Package Verification System
"""

import os

# Camera Settings
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))  # Default webcam index (0 for primary built-in/USB camera)
FRAME_WIDTH = 1280                                   # Desired frame width in pixels
FRAME_HEIGHT = 720                                   # Desired frame height in pixels
WINDOW_TITLE = "AI Package Verification System - Phase 1 Webcam Feed"

# System Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
