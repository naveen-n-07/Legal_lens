"""
visualizer.py - Explainable AI Computer Vision Annotation Engine (Stage 11)
Draws color-coded bounding boxes and statutory status badges on package images:
- PASS: Green (0, 255, 0)
- FAIL: Red (0, 0, 255)
- REVIEW / CANNOT_VERIFY: Yellow (0, 255, 255)

Stateless architecture: Converts OpenCV annotations into compact Base64 data URLs
in-memory with adaptive downscaling (max 1000px) to prevent payload bloat.
Supports both 4-point polygon contours (for tilted text) and 4-tuple rectangles.
"""

import base64
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import cv2  # type: ignore
import numpy as np  # type: ignore

logger = logging.getLogger("metrix_visualizer")

# Standardized BGR Color Palette for Legal Metrology Enforcement
COLOR_PASS = (0, 220, 0)       # Vivid Emerald Green (BGR)
COLOR_FAIL = (0, 0, 235)       # High-Alert Ruby Red (BGR)
COLOR_REVIEW = (0, 215, 255)   # Statutory Amber / Yellow (BGR)
COLOR_WHITE = (255, 255, 255)
COLOR_DARK = (20, 24, 33)


class EvidenceVisualizer:
    """
    OpenCV Evidence Highlighting Engine for SIH 26034 (METRIX-LM).
    Statelessly renders explainability overlays directly onto image arrays.
    """

    @classmethod
    def get_status_color(cls, status_str: Optional[str]) -> Tuple[int, int, int]:
        """Maps compliance status string to BGR color tuple."""
        st = (status_str or "").strip().upper()
        if st in ["PASS", "COMPLIANT", "FOLLOWED", "7A COMPLIANT", "VALID"]:
            return COLOR_PASS
        elif st in ["FAIL", "NON_COMPLIANT", "NON-COMPLIANT", "AGAINST", "7B VIOLATION", "INVALID", "CRITICAL"]:
            return COLOR_FAIL
        else:
            return COLOR_REVIEW

    @classmethod
    def normalize_box_coordinates(
        cls,
        box_data: Any,
        scale_x: float = 1.0,
        scale_y: float = 1.0
    ) -> Optional[np.ndarray]:
        """
        Normalizes varying bounding box formats into an integer numpy polygon array:
        Format A: 4-point polygon [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] (PaddleOCR / RapidOCR)
        Format B: 4-element rectangle [x1, y1, x2, y2]
        Format C: Dict with keys x1, y1, x2, y2 or left, top, width, height
        """
        if box_data is None:
            return None

        try:
            # Format A: 4-point polygon list of points
            if isinstance(box_data, (list, tuple)) and len(box_data) == 4 and isinstance(box_data[0], (list, tuple)):
                pts = []
                for pt in box_data:
                    px = round(float(pt[0]) * scale_x)
                    py = round(float(pt[1]) * scale_y)
                    pts.append([px, py])
                return np.array(pts, dtype=np.int32).reshape((-1, 1, 2))

            # Format B: 4-number rectangle [x1, y1, x2, y2]
            elif isinstance(box_data, (list, tuple)) and len(box_data) == 4 and all(isinstance(v, (int, float)) for v in box_data):
                x1 = round(float(box_data[0]) * scale_x)
                y1 = round(float(box_data[1]) * scale_y)
                x2 = round(float(box_data[2]) * scale_x)
                y2 = round(float(box_data[3]) * scale_y)
                pts = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                return np.array(pts, dtype=np.int32).reshape((-1, 1, 2))

            # Format C: Dict
            elif isinstance(box_data, dict):
                if "x1" in box_data and "y1" in box_data and "x2" in box_data and "y2" in box_data:
                    x1 = round(float(box_data["x1"]) * scale_x)
                    y1 = round(float(box_data["y1"]) * scale_y)
                    x2 = round(float(box_data["x2"]) * scale_x)
                    y2 = round(float(box_data["y2"]) * scale_y)
                    pts = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                    return np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
                elif "left" in box_data and "top" in box_data:
                    x1 = round(float(box_data["left"]) * scale_x)
                    y1 = round(float(box_data["top"]) * scale_y)
                    w = float(box_data.get("width", 0))
                    h = float(box_data.get("height", 0))
                    x2 = round((float(box_data["left"]) + w) * scale_x)
                    y2 = round((float(box_data["top"]) + h) * scale_y)
                    pts = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                    return np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
        except Exception as e:
            logger.debug(f"Box coordinate normalization note: {e}")
            return None

        return None

    @classmethod
    def downscale_for_stateless_transport(
        cls,
        image: np.ndarray,
        max_dim: int = 1000
    ) -> Tuple[np.ndarray, float, float]:
        """
        Scales down large packaging images to a max dimension (default 1000px).
        Avoids browser freezing from oversized Base64 JSON payloads.
        Returns: (scaled_image, scale_x, scale_y)
        """
        if image is None or image.size == 0:
            return image, 1.0, 1.0

        h, w = image.shape[:2]
        if max(h, w) <= max_dim:
            return image.copy(), 1.0, 1.0

        scale = max_dim / float(max(h, w))
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))

        scaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        scale_x = new_w / float(w)
        scale_y = new_h / float(h)
        return scaled, scale_x, scale_y

    @classmethod
    def draw_evidence_boxes(
        cls,
        image: np.ndarray,
        rule_evaluations: List[Dict[str, Any]],
        max_dim: int = 1000,
        draw_labels: bool = True
    ) -> np.ndarray:
        """
        Renders Explainable AI bounding boxes on image array:
        - Uses cv2.polylines with isClosed=True for angled 4-point OCR polygons.
        - Uses translucent alpha-blended fills for statutory highlight regions.
        - Adds crisp label badges with declaration field name and status tag.
        """
        if image is None or image.size == 0:
            return np.zeros((300, 400, 3), dtype=np.uint8)

        # 1. Downscale to keep browser payload lightweight
        annotated, scale_x, scale_y = cls.downscale_for_stateless_transport(image, max_dim=max_dim)
        h, w = annotated.shape[:2]

        # Calculate adaptive line thickness and font scale
        base_thickness = max(2, int(round(min(w, h) / 350.0)))
        font_scale = max(0.38, min(0.65, min(w, h) / 1400.0))

        # Create overlay for translucent region fill
        overlay = annotated.copy()

        # Deduplicate and sort items so FAIL boxes render on top of PASS boxes
        def get_priority(item: Dict[str, Any]) -> int:
            st = str(item.get("status", "")).upper()
            if st in ["FAIL", "NON_COMPLIANT", "NON-COMPLIANT"]:
                return 3
            if st in ["PASS", "COMPLIANT"]:
                return 1
            return 2

        sorted_evals = sorted(rule_evaluations or [], key=get_priority)

        # Keep track of drawn label positions to minimize overlapping
        drawn_labels = []

        for item in sorted_evals:
            # Extract bounding box from multiple possible keys
            raw_box = (
                item.get("evidence_box") or
                item.get("bbox") or
                item.get("bounding_box") or
                item.get("coordinates")
            )

            poly = cls.normalize_box_coordinates(raw_box, scale_x, scale_y)
            if poly is None:
                continue

            status = item.get("status", "REVIEW")
            color = cls.get_status_color(status)
            field_name = (
                item.get("field_name") or
                item.get("declaration_type") or
                item.get("rule_name") or
                "Declaration"
            )
            clean_field = str(field_name).replace("_", " ").title()

            # 1. Draw translucent background fill
            cv2.fillPoly(overlay, [poly], color)

            # 2. Draw sharp contour outline (cv2.polylines supports angled boxes)
            cv2.polylines(annotated, [poly], isClosed=True, color=color, thickness=base_thickness, lineType=cv2.LINE_AA)

            # 3. Draw label badge if requested
            if draw_labels:
                # Find top-left reference point for the label
                xs = poly[:, 0, 0]
                ys = poly[:, 0, 1]
                min_x = int(np.min(xs))
                min_y = int(np.min(ys))

                status_tag = "PASS" if color == COLOR_PASS else ("FAIL" if color == COLOR_FAIL else "REVIEW")
                label_text = f"[{status_tag}] {clean_field}"

                font = cv2.FONT_HERSHEY_SIMPLEX
                text_thickness = max(1, round(base_thickness * 0.7))
                (tw, th), baseline = cv2.getTextSize(label_text, font, font_scale, text_thickness)

                # Ensure label stays inside image boundaries
                pad = 4
                lx = max(4, min(min_x, w - tw - pad * 2 - 4))
                ly = max(th + pad * 2 + 2, min_y - 4)

                # Position label badge
                pt1 = (lx, ly - th - pad * 2)
                pt2 = (lx + tw + pad * 2, ly)

                # Draw solid label background pill
                cv2.rectangle(annotated, pt1, pt2, color, thickness=-1)
                cv2.rectangle(annotated, pt1, pt2, COLOR_DARK, thickness=1, lineType=cv2.LINE_AA)

                # Text color: Dark text for Green/Yellow, White text for Red
                text_color = COLOR_WHITE if color == COLOR_FAIL else COLOR_DARK
                cv2.putText(
                    annotated,
                    label_text,
                    (lx + pad, ly - pad - baseline // 2),
                    font,
                    font_scale,
                    text_color,
                    text_thickness,
                    lineType=cv2.LINE_AA
                )

        # Blend translucent overlay (alpha=0.18) with main annotated image
        cv2.addWeighted(overlay, 0.18, annotated, 0.82, 0, annotated)

        # Draw a sleek Explainable AI Legend Banner on the top-left corner
        cls._draw_legend_badge(annotated, base_thickness)

        return annotated

    @classmethod
    def _draw_legend_badge(cls, img: np.ndarray, base_thickness: int):
        """Draws a compact statutory color-code legend in the top corner."""
        h, w = img.shape[:2]
        pad = 6
        lh = 20
        lw = 240
        x0, y0 = 10, 10

        if w < 320:
            return  # Skip legend on tiny preview thumbnails

        # Semi-transparent dark container
        sub_img = img[y0:y0+lh, x0:x0+lw]
        black_rect = np.zeros(sub_img.shape, dtype=np.uint8)
        cv2.addWeighted(sub_img, 0.35, black_rect, 0.65, 1.0, sub_img)
        cv2.rectangle(img, (x0, y0), (x0 + lw, y0 + lh), (70, 80, 95), 1, lineType=cv2.LINE_AA)

        # Draw 3 color indicator dots with labels
        items = [
            (COLOR_PASS, "PASS"),
            (COLOR_FAIL, "FAIL"),
            (COLOR_REVIEW, "REVIEW")
        ]
        curr_x = x0 + 10
        dot_r = 4
        font = cv2.FONT_HERSHEY_SIMPLEX
        f_scale = 0.35

        for col, txt in items:
            cy = y0 + lh // 2
            cv2.circle(img, (curr_x + dot_r, cy), dot_r, col, -1, lineType=cv2.LINE_AA)
            cv2.circle(img, (curr_x + dot_r, cy), dot_r, COLOR_WHITE, 1, lineType=cv2.LINE_AA)
            cv2.putText(img, txt, (curr_x + dot_r * 2 + 4, cy + 4), font, f_scale, COLOR_WHITE, 1, lineType=cv2.LINE_AA)
            curr_x += 75

    @classmethod
    def to_base64(
        cls,
        image: np.ndarray,
        format_type: str = "jpeg",
        quality: int = 85
    ) -> str:
        """Encodes numpy image array directly to Base64 data URL string."""
        if image is None or image.size == 0:
            return ""

        ext = ".jpg" if format_type.lower() in ["jpg", "jpeg"] else ".png"
        mime = "image/jpeg" if ext == ".jpg" else "image/png"

        if ext == ".jpg":
            params = [int(cv2.IMWRITE_JPEG_QUALITY), max(10, min(100, quality))]
        else:
            params = [int(cv2.IMWRITE_PNG_COMPRESSION), 4]

        success, buffer = cv2.imencode(ext, image, params)
        if not success:
            raise ValueError("Failed to encode image buffer to Base64")

        b64_data = base64.b64encode(buffer).decode("utf-8")
        return f"data:{mime};base64,{b64_data}"

    @classmethod
    def from_base64(cls, b64_str: str) -> Optional[np.ndarray]:
        """Decodes a Base64 data URL or raw Base64 string into an OpenCV image array."""
        if not b64_str:
            return None

        try:
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]

            img_bytes = base64.b64decode(b64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.error(f"Error decoding Base64 image: {e}")
            return None

    @classmethod
    def highlight_evidence(
        cls,
        image: np.ndarray,
        rule_evaluations: List[Dict[str, Any]],
        max_dim: int = 1000
    ) -> str:
        """
        One-stop Explainable AI Pipeline:
        Accepts raw image array & rule evaluations list -> returns Base64 data URL.
        """
        annotated_img = cls.draw_evidence_boxes(image, rule_evaluations, max_dim=max_dim)
        return cls.to_base64(annotated_img, format_type="jpeg", quality=86)
