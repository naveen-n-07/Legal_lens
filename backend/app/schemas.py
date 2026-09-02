"""
schemas.py - Pydantic Request/Response Payload Validation Schemas
"""

from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict  # type: ignore

class Token(BaseModel):
    access_token: str
    token_type: str
    user_name: str
    role: str
    email: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "inspector"

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    designation: str
    zone_office: str
    role: str

    model_config = ConfigDict(from_attributes=True)

class InspectionCreatePayload(BaseModel):
    product_name: str
    category: str
    pdp_shape: Optional[str] = "rectangular"
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pdp_height_cm: Optional[float] = 10.0
    pdp_width_cm: Optional[float] = 10.0
    is_imported: Optional[bool] = False

class BoundingBoxSchema(BaseModel):
    id: str
    text: str
    confidence: float
    x: float
    y: float
    w: float
    h: float
    is_violation: bool = False
    statutory_tag: str

class RuleCheckSchema(BaseModel):
    field_name: str
    extracted_value: str
    expected_rule: str
    is_compliant: bool
    warning_message: Optional[str] = None
    confidence: float

class RuleViolationSchema(BaseModel):
    rule_id: str
    statutory_reference: str
    target_parameter: str
    detected_issue: str

class InspectionResponse(BaseModel):
    id: str
    product_name: str
    category: str
    pdp_shape: str
    location: str
    inspector_id: str
    inspector_name: str
    overall_status: str
    overall_confidence: float
    route_7b_triggered: bool
    original_image_url: Optional[str] = None
    dewarped_image_url: Optional[str] = None
    bounding_boxes: List[BoundingBoxSchema] = []
    checks: List[RuleCheckSchema] = []
    violations: List[RuleViolationSchema] = []
    officer_id: Optional[str] = None
    officer_name: Optional[str] = None
    officer_decision: Optional[str] = None
    officer_comments: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OfficerVerifyRequest(BaseModel):
    inspection_id: str
    decision: str  # 7A COMPLIANT, 7B VIOLATION, REJECTED
    comments: Optional[str] = ""

class AnalyticsResponse(BaseModel):
    total_inspections: int
    compliant_count: int
    violation_count: int
    pending_review_count: int
    compliance_rate_percent: float
    route_7b_trigger_count: int
    category_breakdown: Dict[str, int]
    top_violations: List[Dict[str, Any]]
