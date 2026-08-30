"""
models.py - SQLAlchemy Database ORM Schemas for Regulatory Legal Metrology System
"""

import json
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, ForeignKey, Integer  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    designation = Column(String, nullable=False)
    zone_office = Column(String, nullable=False)
    role = Column(String, nullable=False, default="inspector")  # inspector, officer, admin
    created_at = Column(DateTime, default=datetime.utcnow)

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

    created_at = Column(DateTime, default=datetime.utcnow)

    def set_json_field(self, field_name: str, data: dict):
        setattr(self, field_name, json.dumps(data, default=str))

    def get_json_field(self, field_name: str) -> dict:
        val = getattr(self, field_name, None)
        return json.loads(val) if val else {}

class OCRResultDB(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(String, nullable=False, index=True)
    image_id = Column(String, nullable=True)
    full_text = Column(Text, nullable=False)
    detected_text = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    bounding_box = Column(Text, nullable=False)  # JSON serialized [x1, y1, x2, y2]
    created_at = Column(DateTime, default=datetime.utcnow)

class DeclarationDB(Base):
    __tablename__ = "declarations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(String, nullable=False, index=True)
    field_name = Column(String, nullable=False)
    field_value = Column(String, nullable=True)
    confidence = Column(Float, nullable=False, default=90.0)
    source_ocr_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ComplianceRuleDB(Base):
    __tablename__ = "compliance_rules"

    rule_id = Column(String, primary_key=True, index=True)
    rule_category = Column(String, nullable=False)
    statutory_reference = Column(String, nullable=False)
    target_parameter = Column(String, nullable=False)
    compliance_condition = Column(Text, nullable=False)
    violation_condition = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ScanSession(Base):
    __tablename__ = "scan_sessions"

    id = Column(String, primary_key=True, index=True)
    original_image_url = Column(String, nullable=True)
    processed_image_url = Column(String, nullable=True)
    quality_score = Column(Integer, nullable=False, default=100)
    quality_metrics_json = Column(Text, nullable=True)
    raw_ocr_json = Column(Text, nullable=True)
    normalized_declarations_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

