# AI Package Verification System — Phase 1: Project Setup & Webcam Capture

Welcome to **Phase 1** of building your real-world **AI Package Verification System**!

In this phase, we establish the modular project structure and implement the core **Camera Capture Module** using Python and OpenCV.

---

## 📁 Project Directory Structure

```text
package-verification-system/
│
├── app/
│   ├── main.py              # Application Entry Point
│   ├── camera/
│   │   ├── __init__.py
│   │   └── webcam.py        # OpenCV Video Capture Manager
│   └── utils/
│
├── config/
│   └── config.py            # Resolution, Camera Index & System Paths
│
├── logs/                    # Automated System Logs
├── outputs/                 # Captured Image Artifacts
├── tests/
│   └── test_camera.py       # Pytest Unit Tests
│
├── requirements.txt         # Dependencies
└── README.md
```

---

## 🎓 Beginner Core Concepts Explained

### 1. What is an Image Frame?
A digital video feed is just a rapid sequence of still pictures called **frames** displayed one after another (usually 30 frames per second). Each frame is stored as a 3D numerical matrix of **pixels**.

### 2. What is OpenCV (`cv2`)?
OpenCV (*Open Source Computer Vision Library*) is the industry-standard Python library used for reading camera feeds, processing image arrays, drawing bounding boxes, and displaying graphical windows.

### 3. Key OpenCV Functions Used:
- **`cv2.VideoCapture(index)`**: Connects Python to your physical USB or built-in webcam.
- **`cap.isOpened()`**: Checks if the camera hardware is powered on and accessible.
- **`cap.read()`**: Grabs the next frame from the camera stream.
- **`cv2.imshow(title, frame)`**: Opens a pop-up desktop window showing the live camera image.
- **`cv2.waitKey(1)`**: Waits 1 millisecond for a keyboard keypress (`'q'` or `ESC`) to exit.
- **`cap.release()` & `cv2.destroyAllWindows()`**: Frees the camera hardware so other software can use it.

---

## 🚀 Execution & Setup Instructions

### 1. Install Dependencies
```bash
pip install -r c:\SIH\package-verification-system\requirements.txt
```

### 2. Run Phase 1 Application
```bash
python c:\SIH\package-verification-system\app\main.py
```

### 3. Run Automated Unit Tests
```bash
python -m unittest c:\SIH\package-verification-system\tests\test_camera.py
```
