"""
preprocessor.py - Layer 2 Preprocessing Pipeline for PaddleOCR
"""

import cv2
import numpy as np

def optimize_statutory_crop(image: np.ndarray, max_dim: int = 1400) -> np.ndarray:
    """
    Optimizes a YOLO crop specifically for PaddleOCR by eliminating shadows, glare, and sensor noise,
    while maintaining sub-pixel font stroke boundaries necessary for Legal Metrology compliance parsing.

    Rules applied:
    1. Dimension Normalization (clamping to max 1400px via INTER_AREA).
    2. Luminance Equalization (LAB color space -> L-channel CLAHE).
    3. Edge-Preserving Smoothing (Bilateral Filter).
    """
    if image is None or image.size == 0:
        return image

    h, w = image.shape[:2]

    # 1. Dimension Normalization
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Convert to 3 channels if it isn't already (defensive programming)
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    # 2. Luminance Equalization (L-channel CLAHE)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_channel_eq = clahe.apply(l_channel)
    
    lab_eq = cv2.merge((l_channel_eq, a_channel, b_channel))
    image_eq = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)

    # 3. Edge-Preserving Smoothing (Bilateral Filtering)
    # d=5, sigmaColor=35, sigmaSpace=35
    optimized_image = cv2.bilateralFilter(image_eq, 5, 35, 35)

    return optimized_image
