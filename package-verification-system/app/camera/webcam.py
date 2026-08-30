"""
webcam.py - OpenCV Webcam Video Capture Manager (Phase 1)
"""

import sys
import os

# Ensure config module is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import cv2  # type: ignore
import numpy as np  # type: ignore
import logging
from config.config import CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT, WINDOW_TITLE

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class WebcamStream:
    """
    Manages opening, reading frames from, and safely releasing the webcam hardware resource.
    """

    def __init__(self, camera_index: int = CAMERA_INDEX):
        self.camera_index = camera_index
        self.cap = None

    def start(self) -> bool:
        """
        Attempts to open the webcam device. Returns True if successful, False otherwise.
        """
        logging.info(f"Attempting to open camera device at index: {self.camera_index}")
        
        # cv2.VideoCapture(index) initializes camera hardware stream
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
        
        # Configure requested frame resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

        if not self.cap.isOpened():
            logging.error(f"ERROR: Unable to open webcam at index {self.camera_index}.")
            logging.error("Check if another app is using your camera or try a different index (e.g., 1 or 2).")
            return False

        logging.info("Camera stream successfully opened.")
        return True

    def run_live_feed(self):
        """
        Continuous main loop reading frames and displaying live feed window until user presses 'q' or ESC key.
        """
        if not self.cap or not self.cap.isOpened():
            print("Cannot run live feed: Camera is not initialized or opened.")
            return

        print("\n=======================================================")
        print(" Live Webcam Feed Started!")
        print(" Press 'q' or 'ESC' in the video window to safely exit.")
        print("=======================================================\n")

        try:
            while True:
                # cap.read() returns a tuple: (success_boolean, numpy_ndarray_frame)
                ret, frame = self.cap.read()

                if not ret or frame is None:
                    logging.warning("Failed to grab video frame. Camera disconnected or feed interrupted.")
                    break

                # Overlay status text on top-left of the live video frame
                h, w = frame.shape[:2]
                status_text = f"Live Feed Active | Res: {w}x{h} | Press 'q' to Exit"
                cv2.putText(frame, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

                # cv2.imshow displays the current frame in a named window
                try:
                    cv2.imshow(WINDOW_TITLE, frame)
                except cv2.error:
                    # Headless OS display fallback
                    print(f"[HEADLESS FEED] Frame captured cleanly: Shape {frame.shape}")
                    break

                # cv2.waitKey(1) waits 1 millisecond for a keypress
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 27 is ESC key
                    logging.info("Exit key pressed ('q' or ESC). Closing live feed...")
                    break

        finally:
            self.stop()

    def stop(self):
        """
        Safely releases the webcam device lock and closes all OpenCV GUI display windows.
        """
        if self.cap and self.cap.isOpened():
            self.cap.release()
            logging.info("Webcam device released.")
        
        try:
            cv2.destroyAllWindows()
            logging.info("OpenCV display windows closed.")
        except Exception:
            pass
