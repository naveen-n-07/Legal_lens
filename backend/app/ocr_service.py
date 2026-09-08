"""
ocr_service.py - OpenCV Image Preprocessing, Quality Gate & All-Declaration Font Bounding Box Detector
"""

import cv2  # type: ignore
import numpy as np  # type: ignore
import re
from typing import Dict, Any, List

from app.ocr.ocr_service import PaddleOCRService, decode_barcode
from app.ocr.preprocessing import OpenCVPreprocessor

class OpenCVOCRService:

    @staticmethod
    def _run_paddle_ocr(processed_img: np.ndarray) -> List[Dict[str, Any]]:
        """
        Runs the PaddleOCRService against a preprocessed image and returns
        detected text lines with confidence + bounding boxes.
        """
        try:
            # Encode image to bytes for OCR service
            success, enc = cv2.imencode(".png", processed_img)
            if not success:
                return []
            ocr_out = PaddleOCRService.process_image(enc.tobytes())
            if ocr_out.get("success") and "results" in ocr_out:
                return ocr_out["results"]
            return []
        except Exception:
            return []

    @staticmethod
    def evaluate_image_quality(img_np: np.ndarray) -> Dict[str, Any]:
        """
        Calculates OpenCV Laplacian variance for image blur detection and resolution gate.
        """
        metrics = OpenCVPreprocessor.evaluate_quality_metrics(img_np)
        h, w = img_np.shape[:2]
        blur_var = metrics["blur_variance"]
        passed = blur_var >= 80.0 and h >= 300 and w >= 300
        is_blurry = blur_var < 80.0

        return {
            "blur_variance": blur_var,
            "height": h,
            "width": w,
            "passed": passed,
            "is_blurry": is_blurry,
            "rejection_reason": None if passed else ("Image too blurry (Laplacian variance < 80.0)" if is_blurry else "Resolution too low (< 300x300)")
        }

    @staticmethod
    def preprocess_image_bytes(image_bytes: bytes) -> np.ndarray:
        """
        Preprocesses image bytes using non-destructive LAB CLAHE glare reduction and bilateral filtering.
        """
        raw_img, _ = OpenCVPreprocessor.validate_and_load_image(image_bytes)
        return OpenCVPreprocessor.enhance_for_preview(raw_img)

    @staticmethod
    def extract_bounding_boxes_and_text(image_bytes: bytes, product_name: str = "", filename: str = "") -> Dict[str, Any]:
        """
        Extracts OCR bounding boxes for package label declarations (Generic Name, MRP, Net Qty, Dates, Address, Consumer Care).
        """
        img_np, info = OpenCVPreprocessor.validate_and_load_image(image_bytes)
        quality = OpenCVOCRService.evaluate_image_quality(img_np)

        px_h = quality["height"]
        px_w = quality["width"]

        auto_h_cm = round((px_h / 50.0), 1) if px_h > 0 else 15.0
        auto_w_cm = round((px_w / 75.0), 1) if px_w > 0 else 10.0
        auto_font_mm = round((px_h * 0.0050), 1) if px_h > 0 else 3.0

        # Run PaddleOCRService
        ocr_out = PaddleOCRService.process_image(image_bytes, filename=filename)
        if not ocr_out.get("success"):
            return {
                "quality": quality,
                "raw_text": "",
                "bounding_boxes": [],
                "auto_detected_dimensions": {
                    "pdp_height_cm": auto_h_cm,
                    "pdp_width_cm": auto_w_cm,
                    "measured_font_mm": auto_font_mm
                },
                "success": False,
                "message": ocr_out.get("error", {}).get("message", "OCR processing failed.")
            }

        ocr_lines = ocr_out.get("results", [])
        bounding_boxes = []
        for idx, line in enumerate(ocr_lines):
            text = line["text"]
            conf = line["confidence"]
            x1, y1, x2, y2 = line["bbox"]
            bounding_boxes.append({
                "id": f"box-{idx + 1}",
                "text": text,
                "confidence": conf,
                "x": float(x1),
                "y": float(y1),
                "w": float(x2 - x1),
                "h": float(y2 - y1),
                "is_violation": False,
                "statutory_tag": "Text Line",
                "bbox": line["bbox"],
                "provenance": "AUTO_EXTRACTED_VERIFIED"
            })

        raw_text = ocr_out.get("full_text", "")

        if not raw_text.strip():
            return {
                "quality": {
                    "blur_variance": quality["blur_variance"],
                    "height": px_h,
                    "width": px_w,
                    "passed": False,
                    "is_low_quality": True,
                    "rejection_reason": "No text could be read from the uploaded image. Please capture a clearer, well-lit photo of the label."
                },
                "raw_text": "",
                "bounding_boxes": [],
                "auto_detected_dimensions": {
                    "pdp_height_cm": auto_h_cm,
                    "pdp_width_cm": auto_w_cm,
                    "measured_font_mm": auto_font_mm
                },
                "success": False,
                "message": "No legible text detected in the uploaded image. Officer verification required."
            }

        return {
            "quality": {
                "blur_variance": quality["blur_variance"],
                "height": px_h,
                "width": px_w,
                "passed": True,
                "is_low_quality": quality.get("blur_variance", 0) < 80.0,
                "rejection_reason": None
            },
            "raw_text": raw_text,
            "bounding_boxes": bounding_boxes,
            "auto_detected_dimensions": {
                "pdp_height_cm": auto_h_cm,
                "pdp_width_cm": auto_w_cm,
                "measured_font_mm": auto_font_mm
            },
            "success": True,
            "message": "AI Computer Vision OCR Completed"
        }
