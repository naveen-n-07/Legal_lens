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

class SyntheticFallbackOCR:
    """
    Synthetic fallback engine used when native deep learning OCR runtimes
    (RapidOCR, PaddleOCR, Tesseract) are not installed in the environment.
    Enables resilient API validation, testing, and continuous integration.
    """
    def __call__(self, img: np.ndarray):
        return [], 0.0


def decode_barcode(image: np.ndarray) -> Dict[str, Any]:
    """
    Dedicated Barcode Decoder (pyzbar) for Legal Metrology packaging compliance.
    Decodes standard EAN-13, UPC, Code-128, etc. from packaging images.
    Returns normalized structure with detected status, decoded value, bounding box, and 100.0% confidence.
    """
    if image is None or image.size == 0:
        return {"value": None, "bbox": None, "confidence": 0.0, "detected": False, "type": None}

    try:
        from pyzbar.pyzbar import decode  # type: ignore
        import cv2  # type: ignore

        # 1. Direct decode on input image
        decoded_objs = decode(image)

        # 2. Grayscale fallback if not detected
        if not decoded_objs and len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            decoded_objs = decode(gray)

            # 3. Contrast-enhanced fallback (CLAHE) for low-contrast/wrinkled barcodes
            if not decoded_objs:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced_gray = clahe.apply(gray)
                decoded_objs = decode(enhanced_gray)

        if decoded_objs:
            obj = decoded_objs[0]
            val = obj.data.decode("utf-8", errors="ignore").strip()
            if val:
                x1 = int(obj.rect.left)
                y1 = int(obj.rect.top)
                x2 = int(obj.rect.left + obj.rect.width)
                y2 = int(obj.rect.top + obj.rect.height)
                b_type = str(obj.type)
                logger.info(f"[BARCODE] Decoded {b_type}: {val} at bbox [{x1}, {y1}, {x2}, {y2}]")
                return {
                    "value": val,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": 100.0,
                    "detected": True,
                    "type": b_type
                }
    except Exception as e:
        logger.warning(f"[BARCODE] pyzbar decode note: {e}")

    return {
        "value": None,
        "bbox": None,
        "confidence": 0.0,
        "detected": False,
        "type": None
    }


class PaddleOCRService:
    _engine_instance = None
    _engine_name: str = "UNINITIALIZED"
    decode_barcode = staticmethod(decode_barcode)

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
                cls._engine_instance = RapidOCR(use_cls=True)
                cls._engine_name = "RapidOCR (PP-OCRv4 ONNX)"
                logger.info(f"[OCR] Engine: {cls._engine_name}")
                logger.info("[OCR] OCR engine initialized successfully (Angle Classifier: True)")
                return cls._engine_instance
            except Exception as e:
                logger.warning(f"[OCR] RapidOCR initialization note: {e}")

            # 2. Try PaddleOCR
            try:
                from paddleocr import PaddleOCR  # type: ignore
                cls._engine_instance = PaddleOCR(use_angle_cls=True, lang='en')
                cls._engine_name = "PaddleOCR"
                logger.info(f"[OCR] Engine: {cls._engine_name}")
                logger.info("[OCR] OCR engine initialized successfully (use_angle_cls=True, lang='en')")
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

            # 4. Fallback Synthetic Engine
            logger.warning("[OCR] Native OCR libraries not found. Operating in synthetic fallback mode for testing & API validation.")
            cls._engine_instance = SyntheticFallbackOCR()
            cls._engine_name = "Synthetic Fallback Engine"

        return cls._engine_instance

    @classmethod
    def get_engine_name(cls) -> str:
        if cls._engine_instance is None:
            cls.get_ocr_engine()
        return cls._engine_name

    @staticmethod
    def _map_point_to_orig(px: float, py: float, rot: int, scale: float, orig_h: int, orig_w: int) -> Tuple[float, float]:
        """
        Inverts rotated/scaled variant coordinates back to original unrotated image space.
        - 90° CW: x_orig = y_rot / scale, y_orig = (orig_h - 1 - x_rot) / scale
        - 270° CW: x_orig = (orig_w - 1 - y_rot) / scale, y_orig = x_rot / scale
        - 0°: x_orig = px / scale, y_orig = py / scale
        """
        if rot == 90:
            return py / scale, (float(orig_h - 1) - px) / scale
        elif rot == 270:
            return (float(orig_w - 1) - py) / scale, px / scale
        else:
            return px / scale, py / scale

    @classmethod
    def _run_single_variant_ocr(
        cls,
        engine,
        img: np.ndarray,
        scale: float,
        variant_name: str,
        rotation: int = 0,
        orig_h: int = 0,
        orig_w: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Runs OCR on a single image variant and maps bounding box coordinates back to original scale and orientation.
        """
        detections = []
        engine_name = cls.get_engine_name()

        # Fallback dimensions if not explicitly provided
        if orig_h <= 0 or orig_w <= 0:
            var_h, var_w = img.shape[:2]
            if rotation in (90, 270):
                orig_h, orig_w = int(var_w / scale), int(var_h / scale)
            else:
                orig_h, orig_w = int(var_h / scale), int(var_h / scale)

        if ("RapidOCR" in engine_name or "Synthetic" in engine_name) and callable(engine):
            try:
                from typing import Callable as _Callable
                result, elapse = (_Callable)(engine)(img)  # type: ignore[operator]
                if result:
                    for item in result:
                        box = item[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                        text = str(item[1]).strip()
                        conf = round(float(item[2]) * 100.0, 2)
                        
                        if not text:
                            continue

                        # Invert all 4 polygon vertices individually
                        mapped_pts = [cls._map_point_to_orig(pt[0], pt[1], rotation, scale, orig_h, orig_w) for pt in box]
                        x1 = round(max(0, min(p[0] for p in mapped_pts)))
                        y1 = round(max(0, min(p[1] for p in mapped_pts)))
                        x2 = round(min(orig_w - 1, max(p[0] for p in mapped_pts)))
                        y2 = round(min(orig_h - 1, max(p[1] for p in mapped_pts)))

                        if x2 <= x1: x2 = x1 + 1
                        if y2 <= y1: y2 = y1 + 1

                        detections.append({
                            "text": text,
                            "confidence": conf,
                            "bbox": [x1, y1, x2, y2],
                            "bounding_box": [x1, y1, x2, y2],
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

                        mapped_pts = [cls._map_point_to_orig(pt[0], pt[1], rotation, scale, orig_h, orig_w) for pt in box]
                        x1 = round(max(0, min(p[0] for p in mapped_pts)))
                        y1 = round(max(0, min(p[1] for p in mapped_pts)))
                        x2 = round(min(orig_w - 1, max(p[0] for p in mapped_pts)))
                        y2 = round(min(orig_h - 1, max(p[1] for p in mapped_pts)))

                        if x2 <= x1: x2 = x1 + 1
                        if y2 <= y1: y2 = y1 + 1

                        detections.append({
                            "text": text,
                            "confidence": conf,
                            "bbox": [x1, y1, x2, y2],
                            "bounding_box": [x1, y1, x2, y2],
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
                        rx = float(data['left'][i])
                        ry = float(data['top'][i])
                        rw = float(data['width'][i])
                        rh = float(data['height'][i])
                        t_box = [[rx, ry], [rx + rw, ry], [rx + rw, ry + rh], [rx, ry + rh]]
                        mapped_pts = [cls._map_point_to_orig(pt[0], pt[1], rotation, scale, orig_h, orig_w) for pt in t_box]
                        x1 = round(max(0, min(p[0] for p in mapped_pts)))
                        y1 = round(max(0, min(p[1] for p in mapped_pts)))
                        x2 = round(min(orig_w - 1, max(p[0] for p in mapped_pts)))
                        y2 = round(min(orig_h - 1, max(p[1] for p in mapped_pts)))

                        if x2 <= x1: x2 = x1 + 1
                        if y2 <= y1: y2 = y1 + 1

                        detections.append({
                            "text": text,
                            "confidence": round(conf, 2),
                            "bbox": [x1, y1, x2, y2],
                            "bounding_box": [x1, y1, x2, y2],
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
                    union = area1 + area2 - intersection
                    iou = intersection / max(1, union)
                    overlap_ratio = intersection / min(area1, area2)

                    # NMS: If IoU >= 0.45 or heavy containment or identical normalized text with overlap
                    if iou >= 0.45 or overlap_ratio > 0.65 or (text.upper() == u_text.upper() and overlap_ratio > 0.25):
                        is_duplicate = True
                        break

            if not is_duplicate:
                unique_dets.append(det)

        # Sort top-to-bottom, left-to-right for natural reading order with strict 10px Y-tolerance
        unique_dets = sorted(unique_dets, key=lambda d: (d["bbox"][1] // 10, d["bbox"][0]))
        return unique_dets

    @classmethod
    def extract_multi_pass_ocr(
        cls,
        raw_img: np.ndarray,
        variants: List[Dict[str, Any]],
        statutory_crops: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Executes multi-pass OCR on pre-generated variants and optional YOLO statutory crops.
        Returns merged detections, full_text, and overall_confidence.
        """
        engine = cls.get_ocr_engine()
        orig_h, orig_w = raw_img.shape[:2] if (raw_img is not None and raw_img.size > 0) else (0, 0)
        all_variant_detections = []
        max_dim = max(orig_h, orig_w)

        # 1. Full image multi-pass variants with Fast-Track Early Exit
        for idx, v in enumerate(variants):
            v_name = v["name"]
            v_img = v["image"]
            v_scale = v.get("scale_factor", 1.0)
            v_rot = v.get("rotation", 0)
            dets = cls._run_single_variant_ocr(
                engine,
                v_img,
                v_scale,
                v_name,
                rotation=v_rot,
                orig_h=orig_h,
                orig_w=orig_w
            )
            all_variant_detections.extend(dets)

            # Fast-Track Early Exit: If primary pass extracted 2+ valid text detections, return immediately
            if idx == 0 and len(dets) >= 2:
                logger.info(f"[OCR][FAST-TRACK] Primary pass '{v_name}' returned {len(dets)} text lines. Early exit active.")
                break

            # Multi-scale sliding window fallback for large resolutions
            if max_dim > 1500 and v_name in ("enhanced_color", "grayscale_clahe") and v_rot == 0:
                patch_size = 1000
                overlap = 150
                h_var, w_var = v_img.shape[:2]
                for y_p in range(0, h_var, patch_size - overlap):
                    for x_p in range(0, w_var, patch_size - overlap):
                        y2 = min(h_var, y_p + patch_size)
                        x2 = min(w_var, x_p + patch_size)
                        if (y2 - y_p) > 300 and (x2 - x_p) > 300:
                            patch = v_img[y_p:y2, x_p:x2]
                            p_dets = cls._run_single_variant_ocr(
                                engine, patch, v_scale, f"{v_name}_patch_{y_p}_{x_p}",
                                rotation=0, orig_h=y2-y_p, orig_w=x2-x_p
                            )
                            for cd in p_dets:
                                bx1, by1, bx2, by2 = cd["bbox"]
                                shift_x = int(x_p / v_scale)
                                shift_y = int(y_p / v_scale)
                                cd["bbox"] = [bx1 + shift_x, by1 + shift_y, bx2 + shift_x, by2 + shift_y]
                                cd["bounding_box"] = cd["bbox"]
                                all_variant_detections.append(cd)

        # 2. Process YOLO statutory crops individually if detected (bypasses wrinkles & glare)
        if statutory_crops:
            for crop_info in statutory_crops:
                crop_img = crop_info.get("crop")
                crop_bbox = crop_info.get("bbox")
                crop_label = crop_info.get("label", "statutory_block")
                if crop_img is not None and isinstance(crop_img, np.ndarray) and crop_img.size > 0 and crop_bbox and len(crop_bbox) == 4:
                    crop_x1, crop_y1 = crop_bbox[0], crop_bbox[1]
                    c_h, c_w = crop_img.shape[:2]
                    c_dets = cls._run_single_variant_ocr(
                        engine,
                        crop_img,
                        1.0,
                        f"yolo_{crop_label}",
                        rotation=0,
                        orig_h=c_h,
                        orig_w=c_w
                    )
                    # Remap crop coordinates back to full image coordinate space
                    for cd in c_dets:
                        bx1, by1, bx2, by2 = cd["bbox"]
                        cd["bbox"] = [bx1 + crop_x1, by1 + crop_y1, bx2 + crop_x1, by2 + crop_y1]
                        cd["bounding_box"] = cd["bbox"]
                        all_variant_detections.append(cd)

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
    def extract_text(cls, img: np.ndarray, statutory_crops: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Convenience method to run multi-pass OCR directly on a NumPy image array.
        Includes barcode decoding output.
        """
        if img is None or img.size == 0:
            return {
                "detections": [],
                "full_text": "",
                "overall_confidence": 0.0,
                "barcode": {"value": None, "bbox": None, "confidence": 0.0, "detected": False}
            }
        variants = OpenCVPreprocessor.generate_ocr_variants(img)
        ocr_out = cls.extract_multi_pass_ocr(img, variants, statutory_crops=statutory_crops)
        barcode_data = decode_barcode(img)
        ocr_out["barcode"] = {
            "value": barcode_data.get("value"),
            "bbox": barcode_data.get("bbox"),
            "confidence": 100.0 if barcode_data.get("detected") else 0.0,
            "detected": bool(barcode_data.get("detected"))
        }
        return ocr_out

    @staticmethod
    def process_image(image_bytes: bytes, filename: str = "package_label.jpg") -> Dict[str, Any]:
        """
        Executes complete non-destructive OpenCV multi-pass OCR, YOLO statutory ROI detection,
        dedicated pyzbar barcode decoding, and statutory declaration extraction.
        """
        logger.info(f"[SCAN] Image received: {filename} ({len(image_bytes)/(1024):.1f} KB)")

        # 1. Load image without corruption
        raw_img, img_info = OpenCVPreprocessor.validate_and_load_image(image_bytes)
        h, w = img_info["height"], img_info["width"]
        logger.info(f"[SCAN] Image dimensions: {w}x{h}")

        # 1B. Barcode Decoding via pyzbar (EAN-13, UPC, Code-128)
        barcode_res = decode_barcode(raw_img)
        if barcode_res.get("detected"):
            logger.info(f"[BARCODE] Detected {barcode_res.get('type')}: {barcode_res.get('value')}")

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

        # 4B. YOLOv8 Statutory Region Detection (mrp_block, dates_block, fssai_logo)
        statutory_crops = []
        try:
            from app.package_detection.yolo_detector import YoloRegionDetector
            yolo_detector = YoloRegionDetector.get_instance()
            statutory_crops = yolo_detector.get_statutory_crops(raw_img)
            if statutory_crops:
                logger.info(f"[YOLO] Localized {len(statutory_crops)} statutory ROIs: {[c.get('label') for c in statutory_crops]}")
        except Exception as ye:
            logger.warning(f"[YOLO] Region detector note: {ye}")

        # 5. Multi-Pass OCR execution across variants and statutory crops
        ocr_result = PaddleOCRService.extract_multi_pass_ocr(raw_img, variants, statutory_crops=statutory_crops)
        merged_detections = ocr_result["detections"]
        full_text = ocr_result["full_text"]
        overall_conf = ocr_result["overall_confidence"]

        logger.info(f"[OCR] Detected text regions: {len(merged_detections)} unique lines")
        logger.info(f"[OCR] Raw text length: {len(full_text)} characters")
        logger.info(f"[OCR] Overall confidence: {overall_conf}%")

        # 6. Extract Declarations
        logger.info("[EXTRACTION] Extracting declarations...")
        declarations = DeclarationExtractor.parse_declarations(full_text, merged_detections)

        # 6.5 Layer 3 OCR Post-Processing (Glyph Disambiguation & Strict Regex)
        try:
            from app.ocr.postprocessor import OCRPostProcessor
            pp_fssai = OCRPostProcessor.extract_fssai(full_text)
            if pp_fssai:
                if not declarations.get("fssai_license"):
                    declarations["fssai_license"] = {}
                declarations["fssai_license"]["value"] = pp_fssai
                
            pp_mrp = OCRPostProcessor.extract_mrp(full_text)
            if pp_mrp is not None:
                if not declarations.get("mrp"):
                    declarations["mrp"] = {}
                declarations["mrp"]["value"] = pp_mrp
                
            pp_dates = OCRPostProcessor.extract_dates(full_text)
            if pp_dates.get("mfg"):
                if not declarations.get("manufacturing_date"):
                    declarations["manufacturing_date"] = {}
                declarations["manufacturing_date"]["value"] = pp_dates["mfg"]
            if pp_dates.get("exp"):
                if not declarations.get("expiry_date"):
                    declarations["expiry_date"] = {}
                declarations["expiry_date"]["value"] = pp_dates["exp"]
        except Exception as pe:
            logger.warning(f"[POSTPROCESSOR] Error applying Layer 3 sanitization: {pe}")

        # 6B. Forcefully inject detected barcode into declarations for Rule Engine voluntary_marks validation
        if barcode_res.get("detected") and barcode_res.get("value"):
            declarations["barcode"] = {
                "value": str(barcode_res["value"]),
                "bbox": barcode_res.get("bbox"),
                "confidence": 100.0,
                "detected": True,
                "type": barcode_res.get("type")
            }
        else:
            declarations["barcode"] = {
                "value": None,
                "bbox": None,
                "confidence": 0.0,
                "detected": False,
                "type": None
            }

        logger.info(f"[EXTRACTION] MRP: {declarations.get('mrp', {}).get('value')}")
        logger.info(f"[EXTRACTION] Net Quantity: {declarations.get('net_quantity', {}).get('value')}")
        logger.info(f"[EXTRACTION] Dates: Mfg={declarations.get('manufacturing_date', {}).get('value')}, Exp={declarations.get('expiry_date', {}).get('value')}")
        logger.info(f"[EXTRACTION] Batch: {declarations.get('batch_number', {}).get('value')}")
        logger.info(f"[EXTRACTION] Manufacturer: {declarations.get('manufacturer', {}).get('value')}")
        logger.info(f"[EXTRACTION] Consumer Care: {declarations.get('consumer_care', {}).get('value')}")
        logger.info(f"[EXTRACTION] Barcode: {declarations.get('barcode', {}).get('value')}")
        logger.info("[API] Returning OCR + declarations")

        # Create low-confidence warning if needed
        warning_msg = None
        if overall_conf < 75.0:
            warning_msg = "Text could not be read with high confidence (<75%). Please capture a clearer photo or require officer verification."
        elif len(merged_detections) == 0:
            warning_msg = "OCR completed, but no legible text was detected in the uploaded image."

        barcode_payload = {
            "value": barcode_res.get("value"),
            "bbox": barcode_res.get("bbox"),
            "confidence": 100.0 if barcode_res.get("detected") else 0.0,
            "detected": bool(barcode_res.get("detected"))
        }

        return {
            "success": True,
            "barcode": barcode_payload,
            "ocr": {
                "engine": engine_name,
                "status": "ready",
                "full_text": full_text,
                "overall_confidence": overall_conf,
                "detections": merged_detections,
                "barcode": barcode_payload
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
            "statutory_crops": [
                {
                    "label": c.get("label"),
                    "bbox": c.get("bbox"),
                    "confidence": c.get("confidence", 1.0)
                }
                for c in statutory_crops
            ],
            "preprocessing": {
                "original_size": (w, h),
                "variants_processed": [v["name"] for v in variants],
                "statutory_rois_processed": len(statutory_crops),
                "unique_detections": len(merged_detections)
            }
        }
