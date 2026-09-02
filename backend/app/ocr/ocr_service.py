"""
ocr_service.py - Multi-Pass OCR Engine Service for METRIX-LM Packaging Compliance
Integrates RapidOCR (PP-OCRv4 ONNX), PaddleOCR, and PyTesseract with non-destructive
multi-variant OpenCV preprocessing, spatial deduplication, and structured extraction.
"""

import sys
import logging
import numpy as np  # type: ignore
from typing import Dict, Any, List, Optional, Tuple

from app.ocr.preprocessing import OpenCVPreprocessor
from app.ocr.declaration_extractor import DeclarationExtractor

logger = logging.getLogger("metrix_ocr")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class PaddleOCRService:
    _engine_instance = None
    _engine_name: str = "UNINITIALIZED"

    @classmethod
    def get_ocr_engine(cls):
        """
        Initializes and returns the primary OCR engine.
        Priority:
        1. RapidOCR (PaddleOCR PP-OCRv4 ONNX - fast, zero DLL compilation issues, Python 3.14 compatible)
        2. PaddleOCR (native PaddlePaddle)
        3. PyTesseract (Tesseract OCR fallback)
        """
        if cls._engine_instance is None:
            logger.info("[OCR] Initializing OCR engine...")

            # 1. Try RapidOCR (PP-OCRv4 ONNX)
            try:
                from rapidocr_onnxruntime import RapidOCR  # type: ignore
                cls._engine_instance = RapidOCR()
                cls._engine_name = "RapidOCR (PP-OCRv4 ONNX)"
                logger.info(f"[OCR] Engine: {cls._engine_name}")
                logger.info("[OCR] OCR engine initialized successfully")
                return cls._engine_instance
            except Exception as e:
                logger.warning(f"[OCR] RapidOCR initialization note: {e}")

            # 2. Try PaddleOCR
            try:
                from paddleocr import PaddleOCR  # type: ignore
                cls._engine_instance = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
                cls._engine_name = "PaddleOCR"
                logger.info(f"[OCR] Engine: {cls._engine_name}")
                logger.info("[OCR] OCR engine initialized successfully")
                return cls._engine_instance
            except Exception as e:
                logger.warning(f"[OCR] PaddleOCR initialization note: {e}")

            # 3. Try PyTesseract
            try:
                import pytesseract  # type: ignore
                # Test if tesseract executable is reachable
                cls._engine_instance = pytesseract
                cls._engine_name = "PyTesseract"
                logger.info(f"[OCR] Engine: {cls._engine_name}")
                logger.info("[OCR] OCR engine initialized successfully")
                return cls._engine_instance
            except Exception as e:
                logger.warning(f"[OCR] PyTesseract initialization note: {e}")

            logger.error("[OCR][ERROR] No OCR engine could be initialized!")
            cls._engine_name = "UNAVAILABLE"

        return cls._engine_instance

    @classmethod
    def get_engine_name(cls) -> str:
        if cls._engine_instance is None:
            cls.get_ocr_engine()
        return cls._engine_name

    @staticmethod
    def _run_single_variant_ocr(engine, img: np.ndarray, scale: float, variant_name: str) -> List[Dict[str, Any]]:
        """
        Runs OCR on a single image variant and maps bounding box coordinates back to original scale.
        """
        detections = []
        engine_name = PaddleOCRService.get_engine_name()

        if "RapidOCR" in engine_name and callable(engine):
            try:
                result, elapse = engine(img)
                if result:
                    for item in result:
                        box = item[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                        text = str(item[1]).strip()
                        conf = round(float(item[2]) * 100.0, 2)
                        
                        if not text:
                            continue

                        # Map coordinates back to original scale
                        x1 = int(round(min(pt[0] for pt in box) / scale))
                        y1 = int(round(min(pt[1] for pt in box) / scale))
                        x2 = int(round(max(pt[0] for pt in box) / scale))
                        y2 = int(round(max(pt[1] for pt in box) / scale))

                        detections.append({
                            "text": text,
                            "confidence": conf,
                            "bbox": [x1, y1, x2, y2],
                            "variant": variant_name
                        })
            except Exception as e:
                logger.warning(f"[OCR] Error in RapidOCR variant {variant_name}: {e}")

        elif "PaddleOCR" in engine_name and hasattr(engine, "ocr"):
            try:
                ocr_out = engine.ocr(img, cls=True)
                if ocr_out and len(ocr_out) > 0 and ocr_out[0]:
                    for line in ocr_out[0]:
                        box = line[0]
                        text_pair = line[1]
                        text = str(text_pair[0]).strip()
                        conf = round(float(text_pair[1]) * 100.0, 2)
                        if not text:
                            continue

                        x1 = int(round(min(pt[0] for pt in box) / scale))
                        y1 = int(round(min(pt[1] for pt in box) / scale))
                        x2 = int(round(max(pt[0] for pt in box) / scale))
                        y2 = int(round(max(pt[1] for pt in box) / scale))

                        detections.append({
                            "text": text,
                            "confidence": conf,
                            "bbox": [x1, y1, x2, y2],
                            "variant": variant_name
                        })
            except Exception as e:
                logger.warning(f"[OCR] Error in PaddleOCR variant {variant_name}: {e}")

        elif "PyTesseract" in engine_name:
            try:
                import pytesseract  # type: ignore
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                n_boxes = len(data['text'])
                for i in range(n_boxes):
                    text = data['text'][i].strip()
                    conf = float(data['conf'][i])
                    if conf > 0 and text:
                        x = int(round(data['left'][i] / scale))
                        y = int(round(data['top'][i] / scale))
                        w = int(round(data['width'][i] / scale))
                        h = int(round(data['height'][i] / scale))
                        detections.append({
                            "text": text,
                            "confidence": round(conf, 2),
                            "bbox": [x, y, x + w, y + h],
                            "variant": variant_name
                        })
            except Exception as e:
                logger.warning(f"[OCR] Error in PyTesseract variant {variant_name}: {e}")

        return detections

    @staticmethod
    def _deduplicate_detections(all_detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates overlapping OCR detections across variants, prioritizing higher confidence.
        """
        if not all_detections:
            return []

        # Sort by confidence descending
        sorted_dets = sorted(all_detections, key=lambda d: d.get("confidence", 0), reverse=True)
        unique_dets = []

        for det in sorted_dets:
            bbox = det["bbox"]
            text = det["text"].strip()
            if not text:
                continue

            is_duplicate = False
            for u in unique_dets:
                u_bbox = u["bbox"]
                u_text = u["text"].strip()

                # Calculate bounding box IoU / overlap
                x_left = max(bbox[0], u_bbox[0])
                y_top = max(bbox[1], u_bbox[1])
                x_right = min(bbox[2], u_bbox[2])
                y_bottom = min(bbox[3], u_bbox[3])

                if x_right > x_left and y_bottom > y_top:
                    intersection = (x_right - x_left) * (y_bottom - y_top)
                    area1 = max(1, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
                    area2 = max(1, (u_bbox[2] - u_bbox[0]) * (u_bbox[3] - u_bbox[1]))
                    overlap_ratio = intersection / min(area1, area2)

                    # If significant spatial overlap or identical normalized text in same vertical band
                    if overlap_ratio > 0.45 or (text.upper() == u_text.upper() and abs(bbox[1] - u_bbox[1]) < 25):
                        is_duplicate = True
                        break

            if not is_duplicate:
                unique_dets.append(det)

        # Sort top-to-bottom, left-to-right for natural reading order
        unique_dets = sorted(unique_dets, key=lambda d: (d["bbox"][1] // 18, d["bbox"][0]))
        return unique_dets

    @classmethod
    def extract_multi_pass_ocr(cls, raw_img: np.ndarray, variants: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes multi-pass OCR on pre-generated variants and returns merged detections, full_text, and overall_confidence.
        """
        engine = cls.get_ocr_engine()
        all_variant_detections = []
        for v in variants:
            v_name = v["name"]
            v_img = v["image"]
            v_scale = v["scale_factor"]
            dets = cls._run_single_variant_ocr(engine, v_img, v_scale, v_name)
            all_variant_detections.extend(dets)

        merged_detections = cls._deduplicate_detections(all_variant_detections)
        full_text_list = [d["text"] for d in merged_detections]
        full_text = "\n".join(full_text_list)
        conf_scores = [d["confidence"] for d in merged_detections]
        overall_conf = round(sum(conf_scores) / max(len(conf_scores), 1), 2) if conf_scores else 0.0

        return {
            "detections": merged_detections,
            "full_text": full_text,
            "overall_confidence": overall_conf
        }

    @classmethod
    def extract_text(cls, img: np.ndarray) -> Dict[str, Any]:
        """
        Convenience method to run multi-pass OCR directly on a NumPy image array.
        """
        if img is None or img.size == 0:
            return {"detections": [], "full_text": "", "overall_confidence": 0.0}
        variants = OpenCVPreprocessor.generate_ocr_variants(img)
        return cls.extract_multi_pass_ocr(img, variants)

    @staticmethod
    def process_image(image_bytes: bytes, filename: str = "package_label.jpg") -> Dict[str, Any]:
        """
        Executes complete non-destructive OpenCV multi-pass OCR and statutory declaration extraction.
        """
        logger.info(f"[SCAN] Image received: {filename} ({len(image_bytes)/(1024):.1f} KB)")

        # 1. Load image without corruption
        raw_img, img_info = OpenCVPreprocessor.validate_and_load_image(image_bytes)
        h, w = img_info["height"], img_info["width"]
        logger.info(f"[SCAN] Image dimensions: {w}x{h}")

        # 2. Quality evaluation
        quality = OpenCVPreprocessor.evaluate_quality_metrics(raw_img)
        logger.info(f"[SCAN] Image quality: score={quality['quality_score']}/100, blur_var={quality['blur_variance']}, brightness={quality['brightness_status']}")

        # 3. Check OCR Engine
        engine = PaddleOCRService.get_ocr_engine()
        engine_name = PaddleOCRService.get_engine_name()
        if engine is None or engine_name == "UNAVAILABLE":
            logger.error("[OCR][ERROR] OCR engine unavailable")
            return {
                "success": False,
                "error": {
                    "code": "OCR_ENGINE_UNAVAILABLE",
                    "message": "No compatible OCR engine (RapidOCR / PaddleOCR / PyTesseract) could be initialized on server."
                }
            }

        # 4. Generate Non-Destructive Preprocessing Variants
        logger.info("[PREPROCESS] Generating OCR variants...")
        variants = OpenCVPreprocessor.generate_ocr_variants(raw_img)
        logger.info(f"[PREPROCESS] Variants generated: {[v['name'] for v in variants]}")

        # 5. Multi-Pass OCR execution across variants
        all_variant_detections = []
        for v in variants:
            v_name = v["name"]
            v_img = v["image"]
            v_scale = v["scale_factor"]
            logger.info(f"[OCR] Processing variant: {v_name} (scale: {v_scale}x)")
            dets = PaddleOCRService._run_single_variant_ocr(engine, v_img, v_scale, v_name)
            all_variant_detections.extend(dets)

        # 6. Deduplicate & order detections
        merged_detections = PaddleOCRService._deduplicate_detections(all_variant_detections)
        logger.info(f"[OCR] Detected text regions: {len(merged_detections)} unique lines (from {len(all_variant_detections)} raw variant hits)")

        full_text_list = [d["text"] for d in merged_detections]
        full_text = "\n".join(full_text_list)
        logger.info(f"[OCR] Raw text length: {len(full_text)} characters")

        conf_scores = [d["confidence"] for d in merged_detections]
        overall_conf = round(sum(conf_scores) / max(len(conf_scores), 1), 2)
        logger.info(f"[OCR] Overall confidence: {overall_conf}%")

        # 7. Extract Declarations
        logger.info("[EXTRACTION] Extracting declarations...")
        declarations = DeclarationExtractor.parse_declarations(full_text, merged_detections)
        logger.info(f"[EXTRACTION] MRP: {declarations.get('mrp', {}).get('value')}")
        logger.info(f"[EXTRACTION] Net Quantity: {declarations.get('net_quantity', {}).get('value')}")
        logger.info(f"[EXTRACTION] Dates: Mfg={declarations.get('manufacturing_date', {}).get('value')}, Exp={declarations.get('expiry_date', {}).get('value')}")
        logger.info(f"[EXTRACTION] Batch: {declarations.get('batch_number', {}).get('value')}")
        logger.info(f"[EXTRACTION] Manufacturer: {declarations.get('manufacturer', {}).get('value')}")
        logger.info(f"[EXTRACTION] Consumer Care: {declarations.get('consumer_care', {}).get('value')}")
        logger.info("[API] Returning OCR + declarations")

        # Create low-confidence warning if needed
        warning_msg = None
        if overall_conf < 75.0:
            warning_msg = "Text could not be read with high confidence (<75%). Please capture a clearer photo or require officer verification."
        elif len(merged_detections) == 0:
            warning_msg = "OCR completed, but no legible text was detected in the uploaded image."

        return {
            "success": True,
            "ocr": {
                "engine": engine_name,
                "status": "ready",
                "full_text": full_text,
                "overall_confidence": overall_conf,
                "detections": merged_detections
            },
            "full_text": full_text,
            "raw_text": full_text,
            "overall_confidence": overall_conf,
            "low_confidence_warning": warning_msg,
            "results": merged_detections,
            "ocr_results": merged_detections,
            "declarations": declarations,
            "extracted_declarations": declarations,
            "quality": quality,
            "preprocessing": {
                "original_size": (w, h),
                "variants_processed": [v["name"] for v in variants],
                "total_variant_detections": len(all_variant_detections),
                "unique_detections": len(merged_detections)
            }
        }
