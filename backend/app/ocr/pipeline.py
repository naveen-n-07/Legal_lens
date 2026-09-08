"""
pipeline.py - Unified End-to-End Legal Metrology OCR Pipeline
Chains YOLOv8, Preprocessor (Layer 2), PaddleOCR (Layer 1), and Postprocessor (Layer 3).
"""

import logging
import numpy as np
from typing import Dict, Any, List

from app.package_detection.yolo_detector import YoloRegionDetector
from app.ocr.ocr_engine import LegalMetrologyOCR
from app.ocr.postprocessor import OCRPostProcessor

logger = logging.getLogger("metrix_pipeline")
if not logger.handlers:
    import sys
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)


class MetrixOCRPipeline:
    """
    Unified execution controller for the METRIX-LM Pan-India Legal Metrology Inspection Engine.
    Coordinates YOLO localization, OpenCV conditioning, PaddleOCR text extraction, and
    Anti-Hallucination regex sanitization into a single secure inference path.
    """

    def __init__(self):
        # Initialize Layer 1 (PaddleOCR Engine)
        self.ocr_engine = LegalMetrologyOCR()
        
        # Initialize YOLOv8 Detector
        self.yolo = YoloRegionDetector.get_instance()

    def process(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Executes the end-to-end 3-layer statutory compliance OCR pipeline.
        
        :param image: Raw input packaging image (BGR numpy array).
        :return: Structured JSON payload containing validated compliance values.
        """
        if image is None or image.size == 0:
            return {"success": False, "error": "Invalid image"}

        logger.info("[PIPELINE] Starting End-to-End OCR Extraction...")
        
        # Output structure
        pipeline_results = {
            "mrp": None,
            "fssai_license": None,
            "manufacturing_date": None,
            "expiry_date": None,
            "raw_detections": [],
            "statutory_rois": []
        }

        # 1. YOLO Region Detection
        try:
            statutory_crops = self.yolo.get_statutory_crops(image)
        except Exception as e:
            logger.error(f"[PIPELINE][YOLO] Error during Region Detection: {e}")
            statutory_crops = []

        if not statutory_crops:
            logger.warning("[PIPELINE] No statutory regions detected by YOLO. Proceeding with fallback extraction if necessary.")
            # Depending on business rules, we could run full-image OCR here, but for this strict pipeline we rely on YOLO.
            return {"success": True, "data": pipeline_results}

        logger.info(f"[PIPELINE] YOLO detected {len(statutory_crops)} ROIs. Passing to Layer 1 & 2 Engine...")

        # 2 & 3. Layer 2 Preprocessing & Layer 1 Inference
        # (This handles the CLAHE preprocessor & strict PaddleOCR inference internally, mapping coords back)
        try:
            structured_tokens = self.ocr_engine.extract_from_yolo_crops(image, statutory_crops)
            pipeline_results["raw_detections"] = structured_tokens
            pipeline_results["statutory_rois"] = [{"label": c["label"], "bbox": c["bbox"]} for c in statutory_crops]
        except Exception as e:
            logger.error(f"[PIPELINE][OCR] Error during Layer 1 & 2 Execution: {e}")
            return {"success": False, "error": str(e)}

        # 4. Layer 3 Post-Processing (Glyph Disambiguation & Regex)
        logger.info("[PIPELINE] Layer 1 & 2 complete. Passing raw tokens to Layer 3 Postprocessor...")
        
        for token in structured_tokens:
            text = token.get("text", "")
            region = token.get("source_region", "")
            
            if not text:
                continue

            # Route tokens through strict regex parsers based on YOLO source region hints
            # or apply them globally if YOLO labeling is generic.
            
            # FSSAI Extraction
            if region in ["fssai_logo", "fssai_block", "statutory_block"]:
                if not pipeline_results["fssai_license"]:
                    pp_fssai = OCRPostProcessor.extract_fssai(text)
                    if pp_fssai:
                        pipeline_results["fssai_license"] = pp_fssai
                        logger.info(f"[PIPELINE][LAYER 3] Validated FSSAI License: {pp_fssai}")

            # MRP Extraction
            if region in ["mrp_block", "statutory_block"]:
                if not pipeline_results["mrp"]:
                    pp_mrp = OCRPostProcessor.extract_mrp(text)
                    if pp_mrp is not None:
                        pipeline_results["mrp"] = pp_mrp
                        logger.info(f"[PIPELINE][LAYER 3] Validated MRP: {pp_mrp}")

            # Dates Extraction
            if region in ["dates_block", "statutory_block"]:
                pp_dates = OCRPostProcessor.extract_dates(text)
                if pp_dates.get("mfg") and not pipeline_results["manufacturing_date"]:
                    pipeline_results["manufacturing_date"] = pp_dates["mfg"]
                    logger.info(f"[PIPELINE][LAYER 3] Validated MFG Date: {pp_dates['mfg']}")
                if pp_dates.get("exp") and not pipeline_results["expiry_date"]:
                    pipeline_results["expiry_date"] = pp_dates["exp"]
                    logger.info(f"[PIPELINE][LAYER 3] Validated EXP Date: {pp_dates['exp']}")
                    
            # Global Fallback Check (In case YOLO localized everything into one 'package' or generic block)
            if region in ["package"] or True: # Run globally to be safe
                if not pipeline_results["fssai_license"]:
                    pp_fssai = OCRPostProcessor.extract_fssai(text)
                    if pp_fssai: pipeline_results["fssai_license"] = pp_fssai

                if not pipeline_results["mrp"]:
                    pp_mrp = OCRPostProcessor.extract_mrp(text)
                    if pp_mrp is not None: pipeline_results["mrp"] = pp_mrp

                pp_dates = OCRPostProcessor.extract_dates(text)
                if pp_dates.get("mfg") and not pipeline_results["manufacturing_date"]:
                    pipeline_results["manufacturing_date"] = pp_dates["mfg"]
                if pp_dates.get("exp") and not pipeline_results["expiry_date"]:
                    pipeline_results["expiry_date"] = pp_dates["exp"]

        logger.info("[PIPELINE] End-to-End Extraction Complete.")
        return {"success": True, "data": pipeline_results}

