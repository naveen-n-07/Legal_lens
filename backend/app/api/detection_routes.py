"""
detection_routes.py - Stage 1 Packaged Commodity Detection API Endpoint Gateway
"""

import os
from fastapi import APIRouter, HTTPException, UploadFile, File, status  # type: ignore
from app.package_detection.detector import PackageDetector
from app.package_detection.schemas import PackageDetectionResponse

router = APIRouter(prefix="", tags=["Stage 1: Package Detection"])

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

@router.post("/api/detect-package", response_model=PackageDetectionResponse)
@router.post("/api/v1/detect-package", response_model=PackageDetectionResponse)
async def detect_package(image: UploadFile = File(...)):
    """
    Stage 1: Packaged Commodity / Product Packet Detection Endpoint.
    
    Locates and isolates the packaged commodity from the input photograph.
    Returns detection bounding boxes, confidence score, and cropped package URL.
    """
    filename = image.filename or "uploaded_package.jpg"
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Allowed formats: JPG, JPEG, PNG."
        )

    image_bytes = await image.read()
    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds 25MB limit (received {len(image_bytes)/(1024*1024):.2f}MB)."
        )

    try:
        result = PackageDetector.detect_packages(image_bytes)
        return PackageDetectionResponse(
            success=result["success"],
            detections=result["detections"],
            message=result["message"],
            original_image_url=result.get("original_image_url"),
            annotated_image_url=result.get("annotated_image_url")
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Package detection engine error: {str(e)}"
        )
