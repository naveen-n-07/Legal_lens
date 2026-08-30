"""
main.py - Main Entry Point for AI Package Verification System (Phase 1)
"""

import sys
import os

# Ensure package-verification-system is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.camera.webcam import WebcamStream

def main():
    print("\n-----------------------------------------------------------")
    print(" AI Package Verification System — Phase 1: Webcam Setup")
    print("-----------------------------------------------------------\n")

    webcam = WebcamStream()
    
    if webcam.start():
        webcam.run_live_feed()
    else:
        print("\n[DIAGNOSTIC HINT]")
        print("Camera device could not be opened. Please check:")
        print("1. Is a webcam plugged into your device?")
        print("2. Is another app (Zoom, Teams, Skype, Camera App) using your webcam?")
        print("3. Check Windows Privacy Settings -> Camera Permissions -> Allow Desktop Apps.")

if __name__ == "__main__":
    main()
