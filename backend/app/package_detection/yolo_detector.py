"""
yolo_detector.py - YOLOv8 Statutory Region Detection & ROI Cropping Engine (Stage 8)
Extracts high-resolution Regions of Interest (ROIs) such as mrp_block, dates_block,
and fssai_logo from flexible and wrinkled packaging to bypass plastic glare and folds.
"""

import os
import logging
import cv2  # type: ignore
import numpy as np  # type: ignore
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("metrix_yolo")

# ---------------------------------------------------------------------------
# Explicit absolute model path — resolved once at import time.
# Depth from this file: yolo_detector.py → package_detection → app → backend
#                       → Legal_lens → [workspace_root] → weights/best.pt
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))          # …/package_detection
_BACKEND_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))      # …/backend
_WORKSPACE_ROOT = os.path.dirname(_BACKEND_DIR)                 # …/Legal_lens
_ABSOLUTE_MODEL_PATH = os.path.join(_WORKSPACE_ROOT, "weights", "best.pt")

logger.info(f"[YOLO][Init] Resolved absolute model path: {_ABSOLUTE_MODEL_PATH} "
            f"(exists={os.path.exists(_ABSOLUTE_MODEL_PATH)})")

# Known statutory packaging regions to detect
STATUTORY_CLASSES = [
    "mrp_block",
    "dates_block",
    "fssai_logo",
    "fssai_block",
    "ingredient_block",
    "net_quantity_block",
    "nutrition_block",
    "barcode_block",
    "package"
]

class YoloRegionDetector:
    """
    YOLOv8 Region of Interest (ROI) detector for packaged commodities.
    Prioritizes fine-tuned weights (runs/detect/train/weights/best.pt),
    falling back to standard YOLOv8 or heuristic OpenCV contour ROI extraction.
    """
    _instance = None
    _model = None
    _model_path_used: Optional[str] = None

    def __init__(self, weights_path: Optional[str] = None):
        self.weights_path = weights_path
        self._load_model()

    @classmethod
    def get_instance(cls, weights_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = cls(weights_path)
        return cls._instance

    def _resolve_weights_path(self) -> str:
        """
        Locates the best available YOLO model weights.
        Priority:
          1. Explicitly passed weights_path argument
          2. Module-level _ABSOLUTE_MODEL_PATH (BASE_DIR-anchored, most reliable)
          3. Legacy training output & generic fallback candidates
        """
        if self.weights_path and os.path.exists(self.weights_path):
            logger.info(f"[YOLO] Using caller-supplied weights: {self.weights_path}")
            return self.weights_path

        # Primary: module-level absolute path (never affected by cwd changes)
        if os.path.exists(_ABSOLUTE_MODEL_PATH):
            logger.info(f"[YOLO] Using anchored model path: {_ABSOLUTE_MODEL_PATH}")
            return _ABSOLUTE_MODEL_PATH

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        workspace_root = os.path.dirname(base_dir)

        candidate_paths = [
            os.path.join(workspace_root, "weights", "best.pt"),
            os.path.join(base_dir, "weights", "best.pt"),
            os.path.join(workspace_root, "Legal_lens", "weights", "best.pt"),
            os.path.join(base_dir, "runs", "detect", "train", "weights", "best.pt"),
            os.path.join(workspace_root, "runs", "detect", "train", "weights", "best.pt"),
            os.path.join(os.getcwd(), "runs", "detect", "train", "weights", "best.pt"),
            os.path.join(base_dir, "models_trained", "package_detector", "weights", "best.pt"),
            os.path.join(workspace_root, "models_trained", "package_detector", "weights", "best.pt"),
            os.path.join(base_dir, "yolov8n.pt"),
            "yolov8n.pt"
        ]

        for p in candidate_paths:
            if os.path.exists(p):
                logger.info(f"[YOLO] Found model weights at: {p}")
                return p

        # Default fallback standard model name for Ultralytics auto-download
        return "yolov8n.pt"

    def _load_model(self):
        """
        Loads Ultralytics YOLO model with graceful fallback.
        """
        weights = self._resolve_weights_path()
        self._model_path_used = weights

        try:
            from ultralytics import YOLO  # type: ignore
            logger.info(f"[YOLO] Loading YOLOv8 model from {weights}...")
            self._model = YOLO(weights)
            logger.info(f"[YOLO] Model loaded successfully: {weights}")
        except Exception as e:
            logger.warning(f"[YOLO] Ultralytics YOLO loading unavailable ({e}). Using OpenCV morphological ROI fallback.")
            self._model = "OPENCV_FALLBACK"

    def is_yolo_available(self) -> bool:
        return self._model is not None and self._model != "OPENCV_FALLBACK"

    def get_statutory_crops(
        self,
        image: np.ndarray,
        conf_threshold: float = 0.25,
        min_crop_size: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Runs inference on the packaging image, identifies regions like mrp_block,
        dates_block, fssai_logo, and returns cropped numpy image arrays of just those regions.

        Returns:
            List of dicts:
            [
                {
                    "label": "mrp_block",
                    "bbox": [x1, y1, x2, y2],
                    "confidence": 0.92,
                    "crop": np.ndarray  # Cropped image slice
                },
                ...
            ]
        """
        if image is None or image.size == 0:
            return []

        h, w = image.shape[:2]
        crops: List[Dict[str, Any]] = []

        # 1. Ultralytics YOLO Inference
        if self.is_yolo_available() and hasattr(self._model, "predict"):
            try:
                results = self._model.predict(image, conf=conf_threshold, iou=0.45, agnostic_nms=True, verbose=False)
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    names = results[0].names or {}

                    for box in boxes:
                        coords = box.xyxy[0].cpu().numpy().astype(int)
                        conf = float(box.conf[0].cpu().numpy())
                        cls_id = int(box.cls[0].cpu().numpy())
                        cls_name = names.get(cls_id, f"region_{cls_id}")

                        x1 = max(0, int(coords[0]))
                        y1 = max(0, int(coords[1]))
                        x2 = min(w, int(coords[2]))
                        y2 = min(h, int(coords[3]))

                        # Ensure valid crop dimensions
                        if (x2 - x1) >= min_crop_size and (y2 - y1) >= min_crop_size:
                            crop_np = image[y1:y2, x1:x2].copy()
                            crops.append({
                                "label": cls_name,
                                "bbox": [x1, y1, x2, y2],
                                "confidence": round(conf, 4),
                                "crop": crop_np
                            })
            except Exception as e:
                logger.warning(f"[YOLO] Inference error: {e}")

        # 2. OpenCV Fallback: If no custom regions detected or model not available,
        # detect high-contrast packaging clusters (e.g. date stamps, MRP panels, logos)
        if not crops:
            crops = self._extract_opencv_statutory_regions(image, min_crop_size=min_crop_size)

        return crops

    def get_crop_arrays(self, image: np.ndarray, conf_threshold: float = 0.25) -> List[np.ndarray]:
        """
        Convenience method that returns just the list of cropped numpy image arrays.
        """
        crop_dicts = self.get_statutory_crops(image, conf_threshold=conf_threshold)
        return [c["crop"] for c in crop_dicts if c.get("crop") is not None and c["crop"].size > 0]

    def _extract_opencv_statutory_regions(self, image: np.ndarray, min_crop_size: int = 30) -> List[Dict[str, Any]]:
        """
        Heuristic ROI segmenter that localizes high-density declaration blocks
        (MRP panel, stamp clusters, legal declaration panels) on wrinkled packaging.
        """
        h, w = image.shape[:2]
        regions: List[Dict[str, Any]] = []

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            # Gradient & morphological closing to connect closely spaced text lines into single block
            kernel_grad = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel_grad)

            _, thresh = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 7))
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_close)

            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            candidates = []
            for cnt in contours:
                x, y, cw, ch = cv2.boundingRect(cnt)
                area = cw * ch
                # Filter out single letters and whole-page boundaries
                if (
                    cw >= min_crop_size and 
                    ch >= 15 and 
                    area >= (min_crop_size * 20) and 
                    area <= (w * h * 0.50)
                ):
                    aspect = cw / float(max(ch, 1))
                    if 0.5 <= aspect <= 10.0:
                        candidates.append((x, y, cw, ch, area))

            # Sort by area descending and pick top distinct declaration clusters
            candidates.sort(key=lambda c: c[4], reverse=True)
            for idx, (x, y, cw, ch, _) in enumerate(candidates[:4]):
                # Add slight padding around the detected block to avoid clipping characters
                pad_x = int(cw * 0.05)
                pad_y = int(ch * 0.05)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(w, x + cw + pad_x)
                y2 = min(h, y + ch + pad_y)

                crop_np = image[y1:y2, x1:x2].copy()
                if crop_np.size > 0:
                    # Assign candidate heuristic label
                    label = "statutory_block"
                    if y1 > (h * 0.5) and x1 > (w * 0.4):
                        label = "mrp_dates_block"
                    elif y1 < (h * 0.4):
                        label = "header_block"

                    regions.append({
                        "label": label,
                        "bbox": [x1, y1, x2, y2],
                        "confidence": 0.85,
                        "crop": crop_np
                    })
        except Exception as err:
            logger.warning(f"[YOLO Fallback] Heuristic ROI segmentation exception: {err}")

        return regions
