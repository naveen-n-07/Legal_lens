"""
schemas.py - Pydantic Request/Response Payload Models for PaddleOCR Pipeline
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel  # type: ignore

class OCRBoundingBox(BaseModel):
    text: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]
    statutory_tag: Optional[str] = None
    variant: Optional[str] = None

class DeclarationField(BaseModel):
    value: Optional[Any] = None
    confidence: Optional[float] = 0.0
    bbox: Optional[List[int]] = None
    status: Optional[str] = "not_detected"
    variant: Optional[str] = None

class OCRProcessResponse(BaseModel):
    success: bool
    full_text: str
    overall_confidence: float
    low_confidence_warning: Optional[str] = None
    results: List[Dict[str, Any]]
    extracted_declarations: Dict[str, Any]
    ocr: Optional[Dict[str, Any]] = None
