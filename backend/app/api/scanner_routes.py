"""
scanner_routes.py - Image Quality check, OpenCV Preprocessing, OCR, and Declaration Mapping Endpoints
"""

import os
import re
import uuid
import json
import cv2  # type: ignore
import numpy as np  # type: ignore
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models import ScanSession
from app.ocr.ocr_service import PaddleOCRService
from app.ocr.preprocessing import OpenCVPreprocessor
from app.ocr.declaration_extractor import DeclarationExtractor

router = APIRouter(prefix="", tags=["Statutory Image Scanner"])

RESULTS_DIR = r"c:\Sih\backend\results"
os.makedirs(RESULTS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

def get_file_extension(filename: str) -> str:
    return filename.split(".")[-1].lower() if "." in filename else ""

def calculate_quality_score(blur_var: float, contrast: float, brightness: float) -> int:
    score = 100
    # Blur penalty
    if blur_var < 50.0:
        score -= 40
    elif blur_var < 100.0:
        score -= 20
    # Contrast penalty
    if contrast < 25.0:
        score -= 30
    elif contrast < 45.0:
        score -= 15
    # Brightness penalty
    if brightness < 40.0 or brightness > 230.0:
        score -= 30
    elif brightness < 60.0 or brightness > 210.0:
        score -= 15
    return max(10, min(100, score))

def deskew_image(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return img
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) > 0.5 and abs(angle) < 45:
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    return img

def correct_perspective(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 200)
    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            pts = approx.reshape(4, 2)
            rect = np.zeros((4, 2), dtype="float32")
            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]
            rect[2] = pts[np.argmax(s)]
            diff = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(diff)]
            rect[3] = pts[np.argmax(diff)]
            (tl, tr, br, bl) = rect
            widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            maxWidth = max(int(widthA), int(widthB))
            heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            maxHeight = max(int(heightA), int(heightB))
            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")
            M = cv2.getPerspectiveTransform(rect, dst)
            return cv2.warpPerspective(img, M, (maxWidth, maxHeight))
    return img

def normalize_text(text: str) -> str:
    # 1. Clean spacing around symbols (e.g. MRP Rs . 120 -> MRP Rs. 120)
    text = re.sub(r'\s*\.\s*', '.', text)
    text = re.sub(r'\s*\:\s*', ': ', text)
    text = re.sub(r'\s*\,\s*', ', ', text)
    # 2. Fix multiple spacing
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

@router.post("/api/process-image")
async def process_image_endpoint(file: UploadFile = File(...)):
    ext = get_file_extension(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid format .{ext}. Allowed: JPG, JPEG, PNG, WEBP")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 25MB).")

    # Load image
    img, info = OpenCVPreprocessor.validate_and_load_image(contents)
    
    # 1. Quality evaluation
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    
    quality_score = calculate_quality_score(blur_var, contrast, brightness)
    quality_payload = {
        "quality_score": quality_score,
        "resolution": f"{img.shape[1]}x{img.shape[0]}",
        "blur": blur_var < 100.0,
        "brightness": "dark" if brightness < 60 else "bright" if brightness > 210 else "good",
        "readability": "poor" if quality_score < 70 else "good"
    }

    # 2. Apply OpenCV Enhancements
    enhanced, proc_info = OpenCVPreprocessor.preprocess_for_ocr(img)
    deskewed = deskew_image(enhanced)
    processed = correct_perspective(deskewed)

    # Save processed preview image
    file_uuid = uuid.uuid4().hex
    processed_filename = f"processed_{file_uuid}.png"
    processed_path = os.path.join(RESULTS_DIR, processed_filename)
    cv2.imwrite(processed_path, processed)

    # Save original preview image
    original_filename = f"original_{file_uuid}.png"
    original_path = os.path.join(RESULTS_DIR, original_filename)
    cv2.imwrite(original_path, img)

    return {
        "quality": quality_payload,
        "original_url": f"/results/{original_filename}",
        "processed_url": f"/results/{processed_filename}"
    }

@router.post("/api/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    ocr_out = PaddleOCRService.process_image(contents)
    return {
        "text": ocr_out["full_text"],
        "confidence": ocr_out["overall_confidence"],
        "results": ocr_out["results"]
    }

@router.post("/api/scan")
async def scan_endpoint(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    scan_uuid = f"SCN-{uuid.uuid4().hex[:8].upper()}"
    merged_ocr_results = []
    merged_text_list = []
    conf_scores = []
    quality_scores = []
    
    original_urls = []
    processed_urls = []
    quality_payloads = []

    for i, file in enumerate(files):
        ext = get_file_extension(file.filename)
        if ext not in ALLOWED_EXTENSIONS:
            continue

        contents = await file.read()
        # 1. Quality & Preprocessing
        img, info = OpenCVPreprocessor.validate_and_load_image(contents)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(np.mean(gray))
        contrast = float(np.std(gray))
        
        quality_score = calculate_quality_score(blur_var, contrast, brightness)
        quality_scores.append(quality_score)
        
        quality_payload = {
            "quality_score": quality_score,
            "resolution": f"{img.shape[1]}x{img.shape[0]}",
            "blur": blur_var < 100.0,
            "brightness": "dark" if brightness < 60 else "bright" if brightness > 210 else "good",
            "readability": "poor" if quality_score < 70 else "good"
        }
        quality_payloads.append(quality_payload)

        # OpenCV Preprocessing Pipeline
        enhanced, proc_info = OpenCVPreprocessor.preprocess_for_ocr(img)
        deskewed = deskew_image(enhanced)
        processed = correct_perspective(deskewed)

        file_uuid = uuid.uuid4().hex
        orig_filename = f"orig_{scan_uuid}_{i}.png"
        proc_filename = f"proc_{scan_uuid}_{i}.png"
        
        cv2.imwrite(os.path.join(RESULTS_DIR, orig_filename), img)
        cv2.imwrite(os.path.join(RESULTS_DIR, proc_filename), processed)
        
        original_urls.append(f"/results/{orig_filename}")
        processed_urls.append(f"/results/{proc_filename}")

        # OCR
        ocr_out = PaddleOCRService.process_image(contents, filename=file.filename)
        for res in ocr_out["results"]:
            # Normalization
            normalized_val = normalize_text(res["text"])
            merged_ocr_results.append({
                "text": res["text"],
                "normalized_text": normalized_val,
                "confidence": res["confidence"],
                "bbox": res["bbox"],
                "image_id": orig_filename
            })
            merged_text_list.append(normalized_val)
            conf_scores.append(res["confidence"])

    if not merged_ocr_results:
        raise HTTPException(status_code=400, detail="No valid images were processed.")

    full_text = "\n".join(merged_text_list)
    overall_conf = round(sum(conf_scores) / max(len(conf_scores), 1), 2)
    overall_quality = int(sum(quality_scores) / len(quality_scores))

    # Declaration Extraction via regex/NLP
    declarations = DeclarationExtractor.parse_declarations(full_text)
    
    # Evidence / Bounding Box mapping
    evidence_mapping = {}
    for field, val in declarations.items():
        if not val:
            evidence_mapping[field] = None
            continue
        
        # Look for best matches in OCR results
        best_match = None
        for res in merged_ocr_results:
            if val.upper() in res["text"].upper() or res["text"].upper() in val.upper():
                best_match = res
                break
        
        if best_match:
            evidence_mapping[field] = {
                "value": val,
                "confidence": best_match["confidence"],
                "bbox": best_match["bbox"],
                "image_id": best_match["image_id"]
            }
        else:
            evidence_mapping[field] = {
                "value": val,
                "confidence": overall_conf,
                "bbox": [0, 0, 0, 0],
                "image_id": ""
            }

    # Store ScanSession
    db_session = ScanSession(
        id=scan_uuid,
        original_image_url=",".join(original_urls),
        processed_image_url=",".join(processed_urls),
        quality_score=overall_quality,
        quality_metrics_json=json.dumps(quality_payloads),
        raw_ocr_json=json.dumps(merged_ocr_results),
        normalized_declarations_json=json.dumps(evidence_mapping)
    )
    db.add(db_session)
    db.commit()

    return {
        "scan_id": scan_uuid,
        "original_urls": original_urls,
        "processed_urls": processed_urls,
        "quality": {
            "quality_score": overall_quality,
            "metrics": quality_payloads,
            "warning": "Image quality is low. Please upload a clearer image for better text extraction." if overall_quality < 70 else None
        },
        "raw_text": full_text,
        "ocr_results": merged_ocr_results,
        "extracted_declarations": evidence_mapping
    }

@router.get("/api/scan/{scan_id}")
def get_scan_session(scan_id: str, db: Session = Depends(get_db)):
    sess = db.query(ScanSession).filter(ScanSession.id == scan_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail=f"Scan session '{scan_id}' not found.")
    
    return {
        "scan_id": sess.id,
        "original_urls": sess.original_image_url.split(","),
        "processed_urls": sess.processed_image_url.split(","),
        "quality": {
            "quality_score": sess.quality_score,
            "metrics": json.loads(sess.quality_metrics_json)
        },
        "ocr_results": json.loads(sess.raw_ocr_json),
        "extracted_declarations": json.loads(sess.normalized_declarations_json),
        "created_at": sess.created_at
    }
