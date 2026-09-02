"""
models.py - SQLAlchemy Database ORM Schemas for Regulatory Legal Metrology System
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, ForeignKey, Integer  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore
from app.database import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    designation = Column(String, nullable=False)
    zone_office = Column(String, nullable=False)
    role = Column(String, nullable=False, default="inspector")  # inspector, officer, admin
    created_at = Column(DateTime, default=utc_now)

class InspectionRecord(Base):
    __tablename__ = "inspections"

    id = Column(String, primary_key=True, index=True)
    product_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    pdp_shape = Column(String, default="rectangular")
    location = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    inspector_id = Column(String, ForeignKey("users.id"), nullable=False)
    inspector_name = Column(String, nullable=False)
    
    # Image assets & Quality Metrics
    original_image_url = Column(String, nullable=True)
    dewarped_image_url = Column(String, nullable=True)
    image_blur_variance = Column(Float, default=150.0)
    image_quality_passed = Column(Boolean, default=True)

    # Compliance Evaluation
    overall_status = Column(String, nullable=False, default="PENDING")  # 7A COMPLIANT, 7B VIOLATION, PENDING
    overall_confidence = Column(Float, default=90.0)
    route_7b_triggered = Column(Boolean, default=False)
    
    # Immutable Raw OCR Data (Evidence Base)
    ocr_raw_text_immutable = Column(Text, nullable=True)
    bounding_boxes_json_immutable = Column(Text, nullable=True)
    
    # 5-Section Statutory Report Payloads
    company_profile_json = Column(Text, nullable=True)
    technical_matrix_json = Column(Text, nullable=True)
    pdp_blueprint_json = Column(Text, nullable=True)
    quantity_mpe_json = Column(Text, nullable=True)
    customer_care_json = Column(Text, nullable=True)

    # Provenance Tracking Metadata per Field
    provenance_json = Column(Text, nullable=True)

    # Rule Engine Checks & Violations
    checks_json = Column(Text, nullable=True)
    violations_json = Column(Text, nullable=True)

    # Certificates & Expiry
    lmpc_cert_number = Column(String, nullable=True)
    lmpc_cert_expiry = Column(DateTime, nullable=True)
    equipment_cert_number = Column(String, nullable=True)
    equipment_cert_expiry = Column(DateTime, nullable=True)

    # Senior Officer Verification Gate
    officer_id = Column(String, nullable=True)
    officer_name = Column(String, nullable=True)
    officer_decision = Column(String, nullable=True)
    officer_comments = Column(Text, nullable=True)
    verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utc_now)

    def set_json_field(self, field_name: str, data: Any):
        setattr(self, field_name, json.dumps(data, default=str))

    def get_json_field(self, field_name: str, default_val: Any = None) -> Any:
        val = getattr(self, field_name, None)
        if not val:
            return default_val if default_val is not None else {}
        try:
            return json.loads(val)
        except Exception:
            return default_val if default_val is not None else {}

    def get_checks(self) -> List[Dict[str, Any]]:
        val = self.get_json_field("checks_json", default_val=[])
        return val if isinstance(val, list) else []

    def get_violations(self) -> List[Dict[str, Any]]:
        val = self.get_json_field("violations_json", default_val=[])
        return val if isinstance(val, list) else []

    def get_bounding_boxes(self) -> List[Dict[str, Any]]:
        val = self.get_json_field("bounding_boxes_json_immutable", default_val=[])
        return val if isinstance(val, list) else []

    def get_company_profile(self) -> Dict[str, Any]:
        val = self.get_json_field("company_profile_json", default_val={})
        return val if isinstance(val, dict) else {}

    def get_technical_matrix(self) -> Dict[str, Any]:
        val = self.get_json_field("technical_matrix_json", default_val={})
        return val if isinstance(val, dict) else {}

    def get_pdp_blueprint(self) -> Dict[str, Any]:
        val = self.get_json_field("pdp_blueprint_json", default_val={})
        return val if isinstance(val, dict) else {}

    def get_quantity_mpe(self) -> Dict[str, Any]:
        val = self.get_json_field("quantity_mpe_json", default_val={})
        return val if isinstance(val, dict) else {}

    def get_customer_care(self) -> Dict[str, Any]:
        val = self.get_json_field("customer_care_json", default_val={})
        return val if isinstance(val, dict) else {}

class OCRResultDB(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(String, nullable=False, index=True)
    image_id = Column(String, nullable=True)
    full_text = Column(Text, nullable=False)
    detected_text = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    bounding_box = Column(Text, nullable=False)  # JSON serialized [x1, y1, x2, y2]
    created_at = Column(DateTime, default=utc_now)

class DeclarationDB(Base):
    __tablename__ = "declarations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(String, nullable=False, index=True)
    field_name = Column(String, nullable=False)
    field_value = Column(String, nullable=True)
    confidence = Column(Float, nullable=False, default=90.0)
    source_ocr_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class ComplianceRuleDB(Base):
    __tablename__ = "compliance_rules"

    rule_id = Column(String, primary_key=True, index=True)
    regulation = Column(String, nullable=True)
    regulation_section = Column(String, nullable=True)
    product_category = Column(String, nullable=True, default="ALL")
    field_name = Column(String, nullable=True)
    rule_type = Column(String, nullable=True, default="MANDATORY_FIELD")  # MANDATORY_FIELD, VALUE_CHECK, FORMAT_CHECK, RANGE_CHECK, DATE_CHECK, TEXT_CHECK, CONDITIONAL_RULE
    condition = Column(Text, nullable=True)  # Structured JSON string containing condition definition
    required = Column(Boolean, default=True)
    severity = Column(String, default="HIGH")  # HIGH, MEDIUM, LOW
    error_message = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    version = Column(String, default="1.0.0")
    source_reference = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Legacy / Backward Compatibility Fields
    rule_category = Column(String, nullable=True)
    statutory_reference = Column(String, nullable=True)
    target_parameter = Column(String, nullable=True)
    compliance_condition = Column(Text, nullable=True)
    violation_condition = Column(Text, nullable=True)

    def get_condition_dict(self) -> Dict[str, Any]:
        if not self.condition:
            return {}
        try:
            val = json.loads(self.condition)
            return val if isinstance(val, dict) else {"raw": val}
        except Exception:
            return {}

    def set_condition_dict(self, data: Dict[str, Any]):
        self.condition = json.dumps(data, default=str)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "regulation": self.regulation or self.statutory_reference or "Legal Metrology",
            "regulation_section": self.regulation_section or "",
            "product_category": self.product_category or "ALL",
            "field_name": self.field_name or "",
            "rule_type": self.rule_type or "MANDATORY_FIELD",
            "condition": self.get_condition_dict(),
            "required": bool(self.required),
            "severity": self.severity or "HIGH",
            "error_message": self.error_message or self.violation_condition or "",
            "explanation": self.explanation or self.compliance_condition or "",
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "version": self.version or "1.0.0",
            "source_reference": self.source_reference or self.statutory_reference or "",
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Backward compatibility
            "rule_category": self.rule_category or self.product_category or "",
            "statutory_reference": self.statutory_reference or self.regulation or "",
            "target_parameter": self.target_parameter or self.field_name or "",
            "compliance_condition": self.compliance_condition or self.explanation or "",
            "violation_condition": self.violation_condition or self.error_message or ""
        }

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utc_now)

class ScanSession(Base):
    __tablename__ = "scan_sessions"

    id = Column(String, primary_key=True, index=True)
    original_image_url = Column(String, nullable=True)
    processed_image_url = Column(String, nullable=True)
    quality_score = Column(Integer, nullable=False, default=100)
    quality_metrics_json = Column(Text, nullable=True)
    raw_ocr_json = Column(Text, nullable=True)
    normalized_declarations_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

