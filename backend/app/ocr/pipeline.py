"""
pipeline.py - Unified End-to-End Legal Metrology OCR Pipeline
Chains YOLOv8, Preprocessor (Layer 2), PaddleOCR (Layer 1), and Postprocessor (Layer 3).
"""

import cv2
import logging
import threading
import numpy as np
from typing import Dict, Any, List

from app.package_detection.yolo_detector import YoloRegionDetector
from app.ocr.ocr_engine import LegalMetrologyOCR
from app.ocr.postprocessor import OCRPostProcessor
from app.ocr.declaration_extractor import StatutoryExtractor

logger = logging.getLogger("metrix_pipeline")

# ---------------------------------------------------------------------------
# YOLO class-name normalizer
# Maps the custom class labels produced by the fine-tuned best.pt model to
# the statutory routing keys expected by Layer-3 post-processing.
# Add / adjust entries whenever the training class set changes.
# ---------------------------------------------------------------------------
_YOLO_LABEL_MAP: Dict[str, str] = {
    # Fine-tuned model generic labels → statutory region keys
    "text":               "statutory_block",
    "paragraphs":         "statutory_block",
    "paragraph":          "statutory_block",
    "label_region":       "statutory_block",
    "label":              "statutory_block",
    # Specific region labels (already correct — pass through)
    "mrp_block":          "mrp_block",
    "mrp":                "mrp_block",
    "price":              "mrp_block",
    "dates_block":        "dates_block",
    "date":               "dates_block",
    "expiry":             "dates_block",
    "mfg":                "dates_block",
    "fssai_logo":         "fssai_logo",
    "fssai_block":        "fssai_block",
    "fssai":              "fssai_block",
    "ingredient_block":   "ingredient_block",
    "ingredients":        "ingredient_block",
    "net_quantity_block": "net_quantity_block",
    "net_weight":         "net_quantity_block",
    "quantity":           "net_quantity_block",
    "nutrition_block":    "nutrition_block",
    "nutrition":          "nutrition_block",
    "barcode_block":      "barcode_block",
    "barcode":            "barcode_block",
    "qr_code":            "barcode_block",
    "package":            "package",
}

def _normalize_yolo_label(raw_label: str) -> str:
    """Return a statutory routing key for a raw YOLO class name."""
    return _YOLO_LABEL_MAP.get(raw_label.lower().strip(), "statutory_block")


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

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

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
        pipeline_results: Dict[str, Any] = {
            "mrp": None,
            "fssai_license": None,
            "manufacturing_date": None,
            "expiry_date": None,
            "batch_number": None,
            "raw_detections": [],
            "statutory_rois": []
        }

        # 1. YOLO Region Detection
        try:
            raw_crops = self.yolo.get_statutory_crops(image, conf_threshold=0.25)
        except Exception as e:
            logger.error(f"[PIPELINE][YOLO] Error during Region Detection: {e}")
            raw_crops = []

        # Normalize YOLO class names → statutory routing labels
        statutory_crops = []
        for c in raw_crops:
            normalized = _normalize_yolo_label(c.get("label", ""))
            statutory_crops.append({**c, "label": normalized})

        # Always insert full-image crop to guarantee zero missed text (manufacturer address, consumer care, net weight, etc.)
        h_orig, w_orig = image.shape[:2]
        statutory_crops.insert(0, {
            "label": "statutory_block",
            "bbox": [0, 0, w_orig, h_orig],
            "confidence": 1.0,
            "crop": image
        })

        logger.info(f"[PIPELINE] YOLO detected {len(raw_crops)} ROIs. Running OCR on {len(statutory_crops)} crops (including full-image pass)...")

        # 2 & 3. Layer 2 Preprocessing & Layer 1 Inference
        try:
            structured_tokens = self.ocr_engine.extract_from_yolo_crops(image, statutory_crops)
            
            # Multi-Orientation OCR Pass (Rotated 90 degrees clockwise for vertical pouch side-seals)
            try:
                img_rot90 = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
                tokens_rot90 = self.ocr_engine.extract(img_rot90)
                for t in tokens_rot90:
                    poly_rot = t.get("bounding_box") or []
                    poly_orig = []
                    for pt in poly_rot:
                        xr, yr = pt[0], pt[1]
                        xo = yr
                        yo = h_orig - 1 - xr
                        poly_orig.append([xo, yo])
                    structured_tokens.append({
                        "text": t.get("text"),
                        "confidence": t.get("confidence"),
                        "polygon": poly_orig,
                        "bbox": poly_orig,
                        "source_region": "statutory_block"
                    })
            except Exception as e_rot:
                logger.warning(f"[PIPELINE][OCR] Rotated pass error: {e_rot}")

            # Spatial and textual deduplication of extracted tokens across full-image & crop passes
            deduped_tokens = []
            seen_entries = set()
            for t in structured_tokens:
                txt = (t.get("text") or "").strip().lower()
                poly = t.get("polygon") or []
                poly_key = ""
                if poly and len(poly) > 0:
                    cx = int(sum(pt[0] for pt in poly) / len(poly))
                    cy = int(sum(pt[1] for pt in poly) / len(poly))
                    poly_key = f"{cx // 15}_{cy // 15}"
                
                key = (txt, poly_key)
                if txt and key not in seen_entries:
                    seen_entries.add(key)
                    deduped_tokens.append(t)
            
            structured_tokens = deduped_tokens
            pipeline_results["raw_detections"] = structured_tokens
            # Preserve label, bbox AND confidence so the dashboard can render boxes
            pipeline_results["statutory_rois"] = [
                {"label": c["label"], "bbox": c["bbox"], "confidence": c.get("confidence", 1.0)}
                for c in statutory_crops if c["label"] != "statutory_block" or c["bbox"] != [0, 0, w_orig, h_orig]
            ]
        except Exception as e:
            logger.error(f"[PIPELINE][OCR] Error during Layer 1 & 2 Execution: {e}")
            return {**pipeline_results, "success": False, "error": str(e)}

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
                        pipeline_results["fssai_license"] = {"value": pp_fssai, "bbox": token.get("bbox")}
                        logger.info(f"[PIPELINE][LAYER 3] Validated FSSAI License: {pp_fssai}")

            # MRP Extraction (Rule 6(1)(a) — confidence-gated, three-way verdict)
            if region in ["mrp_block", "statutory_block"]:
                if not pipeline_results["mrp"]:
                    token_conf = float(token.get("confidence", 100.0))
                    if token_conf <= 1.0:
                        token_conf = token_conf * 100.0  # normalize 0-1 → 0-100
                    pp_mrp = OCRPostProcessor.extract_mrp(text, confidence=token_conf)
                    if pp_mrp is not None and pp_mrp.get("value") is not None:
                        pipeline_results["mrp"] = {
                            "value": pp_mrp.get("value"),
                            "price_formatted": pp_mrp.get("price_formatted"),
                            "bbox": token.get("bbox"),
                            "confidence": token_conf,
                            "tax_in_mrp_block": pp_mrp.get("tax_in_mrp_block", False),
                            "mrp_format_valid": pp_mrp.get("mrp_format_valid", True),
                            "verdict": pp_mrp.get("verdict", "CANNOT_VERIFY"),
                            "reason": pp_mrp.get("reason", ""),
                            "raw_line": text
                        }
                        logger.info(f"[PIPELINE][LAYER 3] MRP verdict: {pp_mrp.get('verdict')} — {pp_mrp.get('value')}")

            # Dates Extraction
            if region in ["dates_block", "statutory_block"]:
                pp_dates = OCRPostProcessor.extract_dates(text)
                if pp_dates.get("mfg") and not pipeline_results["manufacturing_date"]:
                    pipeline_results["manufacturing_date"] = {"value": pp_dates["mfg"], "bbox": token.get("bbox")}
                    logger.info(f"[PIPELINE][LAYER 3] Validated MFG Date: {pp_dates['mfg']}")
                if pp_dates.get("exp") and not pipeline_results["expiry_date"]:
                    pipeline_results["expiry_date"] = {"value": pp_dates["exp"], "bbox": token.get("bbox")}
                    logger.info(f"[PIPELINE][LAYER 3] Validated EXP Date: {pp_dates['exp']}")
                    
            # Global Fallback Check (In case YOLO localized everything into one 'package' or generic block)
            if region in ["package"] or True: # Run globally to be safe
                if not pipeline_results["fssai_license"]:
                    pp_fssai = OCRPostProcessor.extract_fssai(text)
                    if pp_fssai: pipeline_results["fssai_license"] = {"value": pp_fssai, "bbox": token.get("bbox")}

                if not pipeline_results["mrp"]:
                    token_conf = float(token.get("confidence", 100.0))
                    if token_conf <= 1.0:
                        token_conf = token_conf * 100.0
                    pp_mrp = OCRPostProcessor.extract_mrp(text, confidence=token_conf)
                    if pp_mrp is not None and pp_mrp.get("value") is not None:
                        pipeline_results["mrp"] = {
                            "value": pp_mrp.get("value"),
                            "price_formatted": pp_mrp.get("price_formatted"),
                            "bbox": token.get("bbox"),
                            "confidence": token_conf,
                            "tax_in_mrp_block": pp_mrp.get("tax_in_mrp_block", False),
                            "mrp_format_valid": pp_mrp.get("mrp_format_valid", True),
                            "verdict": pp_mrp.get("verdict", "CANNOT_VERIFY"),
                            "reason": pp_mrp.get("reason", ""),
                            "raw_line": text
                        }

                pp_dates = OCRPostProcessor.extract_dates(text)
                if pp_dates.get("mfg") and not pipeline_results["manufacturing_date"]:
                    pipeline_results["manufacturing_date"] = {"value": pp_dates["mfg"], "bbox": token.get("bbox")}
                if pp_dates.get("exp") and not pipeline_results["expiry_date"]:
                    pipeline_results["expiry_date"] = {"value": pp_dates["exp"], "bbox": token.get("bbox")}

        # StatutoryExtractor Fallback for MRP if not found by single-token pass
        if not pipeline_results.get("mrp") or not pipeline_results["mrp"].get("value"):
            try:
                _static_extractor = StatutoryExtractor()
                _parsed = _static_extractor.extract_declarations(structured_tokens)
                _mrp_decl = _parsed.get("mrp")
                if _mrp_decl and _mrp_decl.get("value"):
                    tax_stated = _mrp_decl.get("tax_inclusive_stated", False) or _mrp_decl.get("tax_in_mrp_block", False)
                    verdict_str = "CONFORMING" if tax_stated else "VIOLATION"
                    val_num = float(_mrp_decl.get("value"))
                    pipeline_results["mrp"] = {
                        "value": val_num,
                        "price_formatted": f"{val_num:.2f}",
                        "bbox": _mrp_decl.get("bounding_box"),
                        "confidence": float(_mrp_decl.get("confidence", 90.0)),
                        "tax_in_mrp_block": tax_stated,
                        "mrp_format_valid": True,
                        "verdict": verdict_str,
                        "reason": f"MRP ₹ {val_num:.2f} detected with mandatory tax-inclusion clause." if tax_stated else f"MRP ₹ {val_num:.2f} detected but tax-inclusion clause missing.",
                        "raw_line": str(_mrp_decl.get("raw_line", ""))
                    }
                    logger.info(f"[PIPELINE][LAYER 3] StatutoryExtractor fallback MRP: ₹{val_num:.2f} ({verdict_str})")
            except Exception as e_mrp:
                logger.warning(f"[PIPELINE][MRP] Fallback StatutoryExtractor error: {e_mrp}")

        # Global Tax Clause Verification across all tokens
        if pipeline_results.get("mrp") and pipeline_results["mrp"].get("value"):
            all_text_blobs = " ".join(str(token.get("text", "")) for token in structured_tokens)
            if OCRPostProcessor._TAX_PHRASE_RE.search(all_text_blobs):
                pipeline_results["mrp"]["tax_in_mrp_block"] = True
                pipeline_results["mrp"]["verdict"] = "CONFORMING"
                val = pipeline_results["mrp"]["value"]
                pipeline_results["mrp"]["reason"] = (
                    f"MRP ₹ {val:.2f} detected with mandatory tax-inclusion clause "
                    f"'Inclusive of all taxes'. Rule 6(1)(a) satisfied."
                )

        logger.info("[PIPELINE] End-to-End Extraction Complete.")

        # Batch Number Extraction via StatutoryExtractor (if not already found via Layer 3)
        if not pipeline_results["batch_number"] and structured_tokens:
            try:
                _static_extractor = StatutoryExtractor()
                _parsed = _static_extractor.extract_declarations(structured_tokens)
                _batch = _parsed.get("batch_number")
                if _batch and _batch.get("value"):
                    pipeline_results["batch_number"] = _batch
                    logger.info(f"[PIPELINE][BATCH] Extracted Batch/Lot: {_batch['value']}")
                else:
                    # Explicitly mark as not found so downstream can FAIL the rule
                    pipeline_results["batch_number"] = {"value": None, "detected": False}
            except Exception as e:
                logger.warning(f"[PIPELINE][BATCH] StatutoryExtractor error: {e}")
                pipeline_results["batch_number"] = {"value": None, "detected": False}

        # Net Quantity Extraction via StatutoryExtractor
        if structured_tokens:
            try:
                _static_extractor = StatutoryExtractor()
                _parsed = _static_extractor.extract_declarations(structured_tokens)
                _nq = _parsed.get("net_quantity")
                if _nq and _nq.get("value"):
                    pipeline_results["net_quantity"] = _nq
                    logger.info(f"[PIPELINE][NET_QTY] Extracted Net Quantity: {_nq.get('value')} {_nq.get('unit')}")
            except Exception as e_nq:
                logger.warning(f"[PIPELINE][NET_QTY] StatutoryExtractor error: {e_nq}")

        # Return a FLAT dict so the worker can read top-level keys directly
        # (raw_detections, statutory_rois, mrp, fssai_license, batch_number, etc.)
        return {**pipeline_results, "success": True}

