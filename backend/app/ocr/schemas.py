"""
schemas.py - Pydantic Request/Response Payload Models for PaddleOCR Pipeline
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel  # type: ignore

class OCRBoundingBox(BaseModel):
    text: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]
    statutory_tag: Optional[str] = None

class ExtractedDeclarations(BaseModel):
    product_name: Optional[str] = None
    mrp: Optional[str] = None
    net_quantity: Optional[str] = None
    manufacturer: Optional[str] = None
    packer: Optional[str] = None
    importer: Optional[str] = None
    date: Optional[str] = None
    consumer_care: Optional[str] = None
    address: Optional[str] = None

class OCRProcessResponse(BaseModel):
    success: bool
    full_text: str
    overall_confidence: float
    low_confidence_warning: Optional[str] = None
    results: List[OCRBoundingBox]
    extracted_declarations: ExtractedDeclarations
