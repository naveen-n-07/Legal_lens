"""
inspection_routes.py - Inspection Scan, Image Quality Gate & 5-Section Review API Endpoints
"""

import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from app.database import get_db
from app.models import InspectionRecord, User, AuditLog
from app.auth import get_current_user
from app.ocr_service import OpenCVOCRService
from app.rule_engine import RuleEngine

router = APIRouter(prefix="/inspections", tags=["Inspections"])

@router.post("/process-image")
async def process_packaging_image(
    file: UploadFile = File(...),
    product_name: str = Form(...),
    category: str = Form(...),
    pdp_shape: str = Form("rectangular"),
    location: str = Form("Delhi HQ"),
    pdp_height_cm: Optional[float] = Form(None),
    pdp_width_cm: Optional[float] = Form(None),
    measured_font_mm: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    image_bytes = await file.read()
    
    # 1. Image Blur & AI Dimension Auto-Detection
    ocr_result = OpenCVOCRService.extract_bounding_boxes_and_text(image_bytes, product_name=product_name, filename=file.filename)
    if not ocr_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ocr_result["message"]
        )

    auto_dims = ocr_result["auto_detected_dimensions"]
    final_pdp_h = pdp_height_cm if pdp_height_cm is not None else auto_dims["pdp_height_cm"]
    final_pdp_w = pdp_width_cm if pdp_width_cm is not None else auto_dims["pdp_width_cm"]
    final_font_mm = measured_font_mm if measured_font_mm is not None else auto_dims["measured_font_mm"]

    raw_text = ocr_result["raw_text"]
    bounding_boxes = ocr_result["bounding_boxes"]

    payload = {
        "product_name": product_name,
        "category": category,
        "pdp_shape": pdp_shape,
        "location": location,
        "pdp_height_cm": final_pdp_h,
        "pdp_width_cm": final_pdp_w,
        "measured_font_mm": final_font_mm,
        "bounding_boxes": bounding_boxes
    }

    # 2. 5-Section Evaluation against Statutory Rule Matrix
    eval_result = RuleEngine.evaluate_5_section_compliance(payload, raw_text, db=db)

    inspection_id = f"INS-2026-METRIX-{int(datetime.utcnow().timestamp())}"

    record = InspectionRecord(
        id=inspection_id,
        product_name=product_name,
        category=category,
        pdp_shape=pdp_shape,
        location=location,
        inspector_id=current_user.id,
        inspector_name=current_user.name,
        overall_status=eval_result["overall_status"],
        overall_confidence=eval_result["overall_confidence"],
        route_7b_triggered=eval_result["route_7b_triggered"],
        image_blur_variance=ocr_result["quality"]["blur_variance"],
        image_quality_passed=True,
        ocr_raw_text_immutable=raw_text,
        bounding_boxes_json_immutable=json.dumps(bounding_boxes),
        checks_json=json.dumps(eval_result["checks"]),
        violations_json=json.dumps(eval_result["violations"]),
        company_profile_json=json.dumps(eval_result["company_profile"]),
        technical_matrix_json=json.dumps(eval_result["technical_matrix"]),
        pdp_blueprint_json=json.dumps(eval_result["pdp_blueprint"]),
        quantity_mpe_json=json.dumps(eval_result["quantity_mpe"]),
        customer_care_json=json.dumps(eval_result["customer_care"])
    )

    db.add(record)
    
    audit = AuditLog(
        user_id=current_user.id,
        user_name=current_user.name,
        action="INSPECTION_SCAN_PROCESSED",
        resource_id=inspection_id,
        details=f"AI Computer Vision scanned {product_name}. Auto-detected PDP: {final_pdp_h}x{final_pdp_w}cm, Font: {final_font_mm}mm"
    )
    db.add(audit)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "product_name": record.product_name,
        "category": record.category,
        "overall_status": record.overall_status,
        "overall_confidence": record.overall_confidence,
        "route_7b_triggered": record.route_7b_triggered,
        "quality": ocr_result["quality"],
        "auto_detected_dimensions": auto_dims,
        "bounding_boxes": bounding_boxes,
        "checks": eval_result["checks"],
        "violations": eval_result["violations"],
        "company_profile": eval_result["company_profile"],
        "technical_matrix": eval_result["technical_matrix"],
        "pdp_blueprint": eval_result["pdp_blueprint"],
        "quantity_mpe": eval_result["quantity_mpe"],
        "customer_care": eval_result["customer_care"]
    }

@router.get("/{inspection_id}")
def get_inspection_record(inspection_id: str, db: Session = Depends(get_db)):
    record = db.query(InspectionRecord).filter(InspectionRecord.id == inspection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Inspection record not found")
    
    return {
        "id": record.id,
        "product_name": record.product_name,
        "category": record.category,
        "pdp_shape": record.pdp_shape,
        "location": record.location,
        "inspector_name": record.inspector_name,
        "overall_status": record.overall_status,
        "overall_confidence": record.overall_confidence,
        "route_7b_triggered": record.route_7b_triggered,
        "ocr_raw_text_immutable": record.ocr_raw_text_immutable,
        "bounding_boxes": record.get_json_field("bounding_boxes_json_immutable"),
        "checks": record.get_json_field("checks_json"),
        "violations": record.get_json_field("violations_json"),
        "company_profile": record.get_json_field("company_profile_json"),
        "technical_matrix": record.get_json_field("technical_matrix_json"),
        "pdp_blueprint": record.get_json_field("pdp_blueprint_json"),
        "quantity_mpe": record.get_json_field("quantity_mpe_json"),
        "customer_care": record.get_json_field("customer_care_json")
    }

@router.put("/{inspection_id}/verify")
def verify_inspection(
    inspection_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record = db.query(InspectionRecord).filter(InspectionRecord.id == inspection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Inspection record not found")
    
    record.officer_id = current_user.id
    record.officer_name = current_user.name
    record.officer_decision = payload.get("decision", "7A COMPLIANT")
    record.officer_comments = payload.get("comments", "Officer confirmed")
    record.overall_status = payload.get("decision", "7A COMPLIANT")
    record.verified_at = datetime.utcnow()

    audit = AuditLog(
        user_id=current_user.id,
        user_name=current_user.name,
        action="OFFICER_SIGN_OFF",
        resource_id=inspection_id,
        details=f"Officer {current_user.name} signed off decision: {record.officer_decision}"
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": f"Inspection {inspection_id} verified by {current_user.name}"}
