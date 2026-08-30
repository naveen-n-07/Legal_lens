"""
schemas.py - Pydantic Request/Response Payload Schemas for Stage 1 Package Detection
"""

from typing import List, Optional
from pydantic import BaseModel  # type: ignore

class BoundingBoxCoordinates(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class DetectionItem(BaseModel):
    class_name: str = "package"
    confidence: float
    bounding_box: BoundingBoxCoordinates
    crop_url: str

class PackageDetectionResponse(BaseModel):
    success: bool
    detections: List[DetectionItem]
    message: str
    original_image_url: Optional[str] = None
    annotated_image_url: Optional[str] = None
