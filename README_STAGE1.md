# METRIX-LM — Stage 1: Packaged Commodity / Product Packet Detection

This module implements **Stage 1: Packaged Commodity Detection** for **SIH 2026 Problem Statement 26034** (*“Software System to check compliance of Packaged Commodities under Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images and labels”*).

---

## 📌 Objective & Scope

Stage 1 locates and isolates the packaged commodity from an input photograph so that subsequent OCR and legal compliance modules can process it cleanly.

- **Accepts**: Photograph from mobile camera or web file upload (`JPG`, `JPEG`, `PNG`).
- **Detects**: Single or multiple product packets (`package` class) via **Ultralytics YOLO**.
- **Outputs**: Bounding box coordinates, confidence score, and cropped package image saved to `/results/`.
- **Preserves**: Original photograph for audit trail.

---

## 📁 Directory Structure

```text
c:/SIH/
├── dataset/
│   ├── data.yaml              # YOLOv8 Dataset Configuration
│   ├── images/ (train/val/test)
│   └── labels/ (train/val/test)
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── detection_routes.py   # POST /api/detect-package
│   │   ├── package_detection/
│   │   │   ├── detector.py          # YOLO Inference Engine & OpenCV Cropper
│   │   │   ├── schemas.py           # Pydantic Schemas
│   │   │   └── train.py             # YOLO Model Trainer
│   │   └── main.py                  # FastAPI Entry Point (Mounts /results)
│   └── results/                     # Cropped & Annotated Artifact Storage
├── frontend/
│   └── src/
│       └── pages/
│           └── PackageDetection.jsx # Stage 1 React UI Visualizer
├── .env.example
├── README_STAGE1.md
└── test_metrix_lm.py                # Automated Integration Test Suite
```

---

## ⚙️ Configurable Parameters (`.env`)

```env
CONFIDENCE_THRESHOLD=0.50
YOLO_MODEL_PATH="yolov8n.pt"
DATABASE_URL="sqlite:///./metrix_lm.db"
```

---

## 🔌 API Endpoint Gateway

### `POST /api/detect-package`

- **Headers**: `Content-Type: multipart/form-data`
- **Body**: `image` (binary file)

#### Sample Success Response JSON (`200 OK`):
```json
{
  "success": true,
  "detections": [
    {
      "class_name": "package",
      "confidence": 0.96,
      "bounding_box": {
        "x1": 120,
        "y1": 80,
        "x2": 720,
        "y2": 850
      },
      "crop_url": "/results/crop_1_1725000000.jpg"
    }
  ],
  "message": "Packaged commodity detected successfully.",
  "original_image_url": "/results/original_1725000000.jpg",
  "annotated_image_url": "/results/annotated_1725000000.jpg"
}
```

#### Sample No Package Detected Response JSON:
```json
{
  "success": false,
  "detections": [],
  "message": "No packaged commodity detected. Please capture a clearer image."
}
```

---

## 🚀 Execution & Testing Instructions

### 1. Run Automated Unit & Integration Tests
```bash
python c:\SIH\test_metrix_lm.py
```

### 2. Launch Development Stack
```bash
npm run dev
```

- **React Web Portal Stage 1 Detection Page**: [http://localhost:3000/detect-package](http://localhost:3000/detect-package)
- **FastAPI Interactive Swagger Docs**: [http://localhost:8000/docs#/Stage%201%3A%20Package%20Detection/detect_package_api_detect_package_post](http://localhost:8000/docs)
