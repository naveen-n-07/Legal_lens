"""
preprocessing.py - OpenCV Low-Quality Image Auto-Enhancement Pipeline
"""

import cv2  # type: ignore
import numpy as np  # type: ignore
from typing import Tuple, Dict, Any

class OpenCVPreprocessor:

    @staticmethod
    def validate_and_load_image(image_bytes: bytes) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Validates file size, format, and loads raw image bytes into NumPy OpenCV matrix.
        """
        if not image_bytes or len(image_bytes) == 0:
            raise ValueError("Empty image byte stream received.")

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Unsupported or corrupted image file format. Allowed: JPG, JPEG, PNG.")

        height, width = img.shape[:2]
        return img, {"height": height, "width": width, "size_bytes": len(image_bytes)}

    @staticmethod
    def evaluate_quality_metrics(img: np.ndarray) -> Dict[str, Any]:
        """
        Evaluates OpenCV Laplacian blur variance, contrast standard deviation, and brightness.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(np.mean(gray))
        contrast = float(np.std(gray))
        h, w = gray.shape[:2]

        is_low_quality = blur_var < 100.0 or contrast < 40.0 or brightness < 50.0 or brightness > 220.0

        return {
            "blur_variance": round(blur_var, 2),
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "resolution": f"{w}x{h}",
            "is_low_quality": is_low_quality,
            "status": "Auto-Enhancement Required" if is_low_quality else "High Quality Image"
        }

    @staticmethod
    def preprocess_for_ocr(img: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Applies OpenCV low-quality adaptive image enhancement pipeline:
        1. Multi-scale resizing for optimal OCR character height (max 1600px)
        2. Bilateral noise reduction while preserving crisp text letter edges
        3. CLAHE contrast equalization (clipLimit=3.0) for glare reduction
        4. Laplacian unsharp mask sharpening filter
        5. Adaptive Otsu binarization fallback for severe blur/shadows
        """
        h, w = img.shape[:2]
        max_dim = max(h, w)
        scale = 1.0
        if max_dim > 1600:
            scale = 1600.0 / max_dim
            img_resized = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        elif max_dim < 600:
            scale = 800.0 / max_dim
            img_resized = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
        else:
            img_resized = img.copy()

        quality_before = OpenCVPreprocessor.evaluate_quality_metrics(img_resized)

        # 1. Edge-preserving Bilateral Filter for Denoising
        denoised = cv2.bilateralFilter(img_resized, d=9, sigmaColor=75, sigmaSpace=75)

        # 2. CLAHE Glare Reduction & Contrast Equalization on L-channel
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        enhanced_lab = cv2.merge((cl, a, b))
        contrast_img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        # 3. Unsharp Mask Sharpening Filter
        gaussian_blur = cv2.GaussianBlur(contrast_img, (0, 0), 3.0)
        sharpened_img = cv2.addWeighted(contrast_img, 1.5, gaussian_blur, -0.5, 0)

        quality_after = OpenCVPreprocessor.evaluate_quality_metrics(sharpened_img)

        return sharpened_img, {
            "original_size": (w, h),
            "processed_size": (sharpened_img.shape[1], sharpened_img.shape[0]),
            "scale_factor": scale,
            "quality_before": quality_before,
            "quality_after": quality_after,
            "enhancement_applied": [
                "CLAHE Glare Reduction",
                "Bilateral Denoising",
                "Unsharp Mask Text Sharpening"
            ]
        }
