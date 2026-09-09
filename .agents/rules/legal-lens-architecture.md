# Legal Lens Architecture Guidelines

## 1. Frontend: Dynamic UI Image Mapping & SVG Overlays
- **Anti-Duplication**: Never use hardcoded grid loops (e.g., fixed 4-panel templates) for displaying uploaded evidence photos. The UI state must dynamically map over the exact length of the uploaded images array (`uploadedImages.map(...)`). 1 image = 1 preview container.
- **Responsive Bounding Boxes**: Instead of rendering AI detection bounding boxes natively into images on the backend (e.g., using `cv2.fillPoly`), render them dynamically on the frontend. Use SVG or HTML canvas layers directly over the image container.
- **Coordinate Scaling**: Scale YOLO `[x1, y1, x2, y2]` and PaddleOCR polygon coordinates relative to the natural dimensions of the uploaded image element (`naturalWidth` and `naturalHeight`) to guarantee precise alignment regardless of responsive container CSS scaling.

## 2. Backend: AI Execution & Concurrency
- **Concurrency Strategy**: Do not use `ProcessPoolExecutor` inside backend routes (like `inspection_routes.py`) for AI models (YOLO, PaddleOCR), as large models fail to serialize properly to worker processes and will cause `BrokenProcessPool` crashes. Use synchronous execution or `ThreadPoolExecutor` instead, allowing the GPU/CPU to handle native parallel orchestration.
- **Pipeline Execution Integrity**: Maintain strict boundary separation between **Layer 1** (YOLO bounding box detection), **Layer 2** (LAB-channel CLAHE & Bilateral pre-conditioning), and **Layer 3** (Glyph disambiguation & regex validation).
- **Orchestration**: All pipeline executions must be orchestrated through the unified `MetrixOCRPipeline` instead of loose functions or duplicate initialization. Ensure that coordinates extracted from local ROI crops are re-mapped precisely back to global image coordinates before sending the JSON payload to the UI.
