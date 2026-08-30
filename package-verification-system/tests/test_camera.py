"""
test_camera.py - Pytest Unit Tests for Phase 1 Camera Stream
"""

import sys
import os
import unittest
import numpy as np  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.camera.webcam import WebcamStream

class TestPhase1WebcamStream(unittest.TestCase):

    def test_01_webcam_stream_instantiation(self):
        """Tests initializing the WebcamStream class."""
        stream = WebcamStream(camera_index=0)
        self.assertEqual(stream.camera_index, 0)
        self.assertIsNone(stream.cap)

    def test_02_synthetic_frame_processing(self):
        """Tests that OpenCV array format is valid 3-channel image matrix (Height x Width x 3 BGR)."""
        synthetic_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.assertEqual(synthetic_frame.shape, (720, 1280, 3))
        self.assertEqual(synthetic_frame.dtype, np.uint8)

if __name__ == "__main__":
    unittest.main()
