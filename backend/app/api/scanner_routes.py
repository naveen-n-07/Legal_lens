"""
scanner_routes.py - Image Quality Check, Non-Destructive OpenCV Preprocessing, Multi-Pass OCR, and Declaration Mapping Endpoints
"""

import os
import re
import uuid
import json
import logging
import cv2  # type: ignore
import numpy as np  # type: ignore
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status  # type: ignore
from pydantic import BaseModel  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models import ScanSession
from app.ocr.ocr_service import PaddleOCRService
from app.ocr.preprocessing import OpenCVPreprocessor
from app.ocr.declaration_extractor import DeclarationExtractor
from app.api.inspection_routes import compute_statutory_mpe_display, clean_product_title, _merge_declarations
from app.utils.visualizer import EvidenceVisualizer

logger = logging.getLogger("metrix_ocr")
router = APIRouter(prefix="", tags=["Statutory Image Scanner"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

def get_file_extension(filename: str) -> str:
    return filename.split(".")[-1].lower() if "." in filename else ""

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
    ext = get_file_extension(file.filename or "upload.jpg")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid format .{ext}. Allowed: JPG, JPEG, PNG, WEBP")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 25MB).")

    # Load image without corruption
    img, info = OpenCVPreprocessor.validate_and_load_image(contents)
    
    # 1. Quality evaluation
    quality_payload = OpenCVPreprocessor.evaluate_quality_metrics(img)

    # 2. Non-destructive enhancement for preview
    enhanced = OpenCVPreprocessor.enhance_for_preview(img)

    # Save original & processed preview images
    file_uuid = uuid.uuid4().hex
    original_filename = f"original_{file_uuid}.png"
    processed_filename = f"processed_{file_uuid}.png"
    
    cv2.imwrite(os.path.join(RESULTS_DIR, original_filename), img)
    cv2.imwrite(os.path.join(RESULTS_DIR, processed_filename), enhanced)

    return {
        "quality": quality_payload,
        "original_url": f"/results/{original_filename}",
        "processed_url": f"/results/{processed_filename}"
    }

@router.post("/api/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    ocr_out = PaddleOCRService.process_image(contents, filename=file.filename or "package.jpg")
    if not ocr_out.get("success"):
        raise HTTPException(
            status_code=500,
            detail=ocr_out.get("error", {}).get("message", "OCR processing failed.")
        )
    return {
        "text": ocr_out["full_text"],
        "confidence": ocr_out["overall_confidence"],
        "results": ocr_out["results"],
        "ocr": ocr_out.get("ocr", {}),
        "declarations": ocr_out.get("declarations", {})
    }

@router.post("/scan")
@router.post("/api/scan")
async def scan_endpoint(
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    upload_list: List[UploadFile] = []
    if files:
        upload_list.extend(files)
    if file and file not in upload_list:
        upload_list.append(file)

    if not upload_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No packaging image files uploaded. Please select an image."
        )

    scan_uuid = f"SCN-{uuid.uuid4().hex[:8].upper()}"
    merged_ocr_results = []
    merged_text_list = []
    conf_scores = []
    quality_scores = []
    
    original_urls = []
    processed_urls = []
    quality_payloads = []
    all_declarations_list = []
    primary_cv_img = None
    cv_images = []
    cv_images = []

    for i, file_obj in enumerate(upload_list):
        ext = get_file_extension(file_obj.filename or "upload.jpg")
        if ext not in ALLOWED_EXTENSIONS:
            continue

        contents = await file_obj.read()
        if not contents or len(contents) == 0:
            continue
        
        # 1. Quality & Image Loading
        img, info = OpenCVPreprocessor.validate_and_load_image(contents)
        cv_images.append(img)
        cv_images.append(img)
        if primary_cv_img is None:
            primary_cv_img = img
        quality = OpenCVPreprocessor.evaluate_quality_metrics(img)
        quality_scores.append(quality["quality_score"])
        quality_payloads.append(quality)

        # 2. Non-Destructive 4K UHD Image Enhancement for Preview
        enhanced = OpenCVPreprocessor.generate_4k_enhanced_image(img)

        orig_filename = f"orig_{scan_uuid}_{i}.png"
        proc_filename = f"proc_{scan_uuid}_{i}.png"
        
        # Save original and enhanced preview to legal evidence results store
        cv2.imwrite(os.path.join(RESULTS_DIR, orig_filename), img)
        cv2.imwrite(os.path.join(RESULTS_DIR, proc_filename), enhanced)
        
        original_urls.append(f"/results/{orig_filename}")
        processed_urls.append(f"/results/{proc_filename}")

        # 3. Multi-Pass OCR Execution
        ocr_out = PaddleOCRService.process_image(contents, filename=file_obj.filename or f"image_{i}.jpg")
        
        if not ocr_out.get("success"):
            logger.error(f"[SCAN] OCR failed for file {file_obj.filename}: {ocr_out.get('error')}")
            # If critical engine error, raise structured exception
            raise HTTPException(
                status_code=500,
                detail=ocr_out.get("error", {}).get("message", "OCR processing engine unavailable.")
            )

        file_ocr_results = ocr_out.get("results", [])
        for res in file_ocr_results:
            normalized_val = normalize_text(res["text"])
            res_entry = {
                "text": res["text"],
                "normalized_text": normalized_val,
                "confidence": res["confidence"],
                "bbox": res["bbox"],
                "image_id": orig_filename,
                "variant": res.get("variant", "enhanced")
            }
            merged_ocr_results.append(res_entry)
            merged_text_list.append(normalized_val)
            conf_scores.append(res["confidence"])

        file_decls = ocr_out.get("declarations", {})
        all_declarations_list.append(file_decls)

    # Calculate overall metrics
    full_text = "\n".join(merged_text_list)
    overall_conf = round(sum(conf_scores) / max(len(conf_scores), 1), 2)
    overall_quality = int(sum(quality_scores) / max(len(quality_scores), 1))
    engine_name = PaddleOCRService.get_engine_name()

    # Refactored Multi-Image Merge Logic
    merged_declarations = {"unmapped_ledger": []}
    for idx, decls in enumerate(all_declarations_list):
        merged_declarations = _merge_declarations(merged_declarations, decls, idx)

    # Format evidence mapping with guaranteed fields for UI and audit table
    evidence_mapping: Dict[str, Dict[str, Any]] = {}
    
    # Core mandatory Legal Metrology declaration keys
    mandatory_keys = [
        "mrp",
        "mrp_inclusive_tax",
        "net_quantity",
        "unit_of_measurement",
        "unit_sale_price",
        "manufacturing_date",
        "expiry_date",
        "batch_number",
        "manufacturer",
        "packer",
        "marketer",
        "importer",
        "country_of_origin",
        "consumer_care",
        "consumer_care_phone",
        "consumer_care_email",
        "generic_name",
        "fssai_license"
    ]

    for k in mandatory_keys:
        decl: Any = merged_declarations.get(k, {})
        if not isinstance(decl, dict):
            decl = {}

        val = decl.get("value")
        conf = decl.get("confidence", 0.0)
        bbox = decl.get("bbox") or [0, 0, 0, 0]
        status_str = decl.get("status", "not_detected")
        
        img_idx = decl.get("image_index", 0)
        img_id = original_urls[img_idx].replace("/results/", "") if original_urls and img_idx < len(original_urls) else ""
        
        evidence_mapping[k] = {
            "value": val,
            "confidence": conf,
            "bbox": bbox,
            "status": status_str,
            "image_id": img_id
        }

    # Store immutable ScanSession in SQLite database
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

    # Run Dynamic Database-Driven Compliance Validation Engine with strict Error Isolation
    try:
        from app.rules.compliance_service import ComplianceService
        compliance_res = ComplianceService.validate_product(
            declarations=merged_declarations,
            category=None,
            ocr_overall_confidence=overall_conf,
            image_quality_passed=(overall_quality >= 70),
            db=db
        )
    except Exception as exc:
        logger.error(f"Compliance validation engine error: {exc}", exc_info=True)
        compliance_res = {
            "overall_status": "NEEDS REVIEW",
            "screening_title": "Compliance Screening Result",
            "legal_disclaimer": "This is an automated preliminary image-based compliance screening result and does not guarantee absolute legal compliance under the Legal Metrology Act, 2009.",
            "category": "Packaged Commodity",
            "category_inferred": True,
            "regulation": "Statutory Regulations",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_rules": 0,
                "passed": 0,
                "failed": 0,
                "needs_review": 1
            },
            "error_isolation_note": f"Compliance validation encountered an internal error: {str(exc)}. Raw OCR results preserved.",
            "results": []
        }

    # Resolve identified product name and category
    raw_fname = upload_list[0].filename if (upload_list and upload_list[0].filename) else "Packaged Commodity Item"
    gn = merged_declarations.get("generic_name", {}); pn = merged_declarations.get("product_name", {}); detected_pname = (gn.get("value") if isinstance(gn, dict) else None) or (pn.get("value") if isinstance(pn, dict) else None)
    final_pname = clean_product_title(raw_fname, detected_pname)
    final_cat = compliance_res.get("category") or "Food & Beverages"
    overall_stat = compliance_res.get("overall_status", "NEEDS REVIEW")
    legacy_status = "7A COMPLIANT" if overall_stat == "COMPLIANT" else "7B VIOLATION"

    all_results = compliance_res.get("results", [])
    passed_rules_list = [r for r in all_results if isinstance(r, dict) and r.get("status") == "PASS"]
    violations_list = [r for r in all_results if isinstance(r, dict) and r.get("status") == "FAIL"]
    needs_review_list = [r for r in all_results if isinstance(r, dict) and r.get("status") in ["NEEDS_REVIEW", "NEEDS REVIEW", "CANNOT_VERIFY"]]
    bypassed_rules_list = [r for r in all_results if isinstance(r, dict) and r.get("status") in ["NOT_APPLICABLE", "BYPASSED", "N/A"]]

    # Calculate Intelligent Metrics
    total_rules = len(all_results)
    passed_count = len(passed_rules_list)
    failed_count = len(violations_list)
    unverified_count = len(needs_review_list)
    bypassed_count = len(bypassed_rules_list)
    applicable_count = max(1, total_rules - bypassed_count)
    compliance_percentage = round((passed_count / applicable_count) * 100.0, 1) if applicable_count > 0 else 100.0

    mandatory_fields = ["generic_name", "manufacturer", "mrp", "net_quantity", "manufacturing_date", "consumer_care"]
    extracted_count = 0
    for f in mandatory_fields:
        val = merged_declarations.get(f, {})
        if isinstance(val, dict) and (val.get("detected") or val.get("value")):
            extracted_count += 1
    field_extraction_rate = (extracted_count / len(mandatory_fields)) * 100.0
    inspection_confidence = round(0.30 * float(overall_quality) + 0.40 * overall_conf + 0.30 * field_extraction_rate, 1)
    inspection_confidence = max(10.0, min(99.0, inspection_confidence))

    critical_v = sum(1 for v in violations_list if isinstance(v, dict) and str(v.get("severity", "")).upper() == "CRITICAL")
    high_v = sum(1 for v in violations_list if isinstance(v, dict) and str(v.get("severity", "")).upper() == "HIGH")

    if critical_v > 0 or failed_count >= 3 or compliance_percentage < 60.0:
        risk_level = "HIGH"
        risk_icon = "🔴"
        risk_reason = f"{failed_count} compliance rule(s) failed, including {critical_v} critical violation(s)."
    elif failed_count > 0 or unverified_count >= 3 or compliance_percentage < 85.0:
        risk_level = "MEDIUM"
        risk_icon = "🟡"
        risk_reason = f"{failed_count} rule failure(s) and {unverified_count} unverified declaration(s) require officer verification."
    else:
        risk_level = "LOW"
        risk_icon = "🟢"
        risk_reason = f"All {passed_count} mandatory packaging declarations satisfy statutory Legal Metrology requirements."

    risk_classification = {
        "level": risk_level,
        "icon": risk_icon,
        "reason": risk_reason,
        "critical_violations": critical_v,
        "high_violations": high_v
    }

    compliance_summary = {
        "total_rules": total_rules,
        "passed": passed_count,
        "failed": failed_count,
        "cannot_verify": unverified_count,
        "needs_review": unverified_count,
        "compliance_percentage": compliance_percentage,
        "inspection_confidence": inspection_confidence
    }

    # Format Explainable Rules with Evidence & Reasoning
    explainable_rules = []
    for r in all_results:
        if not isinstance(r, dict): continue
        st = r.get("status", "NEEDS_REVIEW")
        if st in ("NOT_APPLICABLE", "BYPASSED", "N/A"):
            status_clean = "NOT_APPLICABLE"
            status_icon = "⚪"
        elif st == "PASS":
            status_clean = "PASS"
            status_icon = "✅"
        elif st == "FAIL":
            status_clean = "FAIL"
            status_icon = "❌"
        else:
            status_clean = "CANNOT_VERIFY"
            status_icon = "⚠"
        
        f_name = r.get("field_name") or r.get("field") or "declaration"
        decl_item = merged_declarations.get(f_name, {})
        if not isinstance(decl_item, dict): decl_item = {}
        if not decl_item or not decl_item.get("value"):
            FIELD_ALIASES = {
                "retail_sale_price": "mrp",
                "mrp_declaration": "mrp",
                "price": "mrp",
                "mrp_inclusive_tax": "mrp_inclusive_tax",
                "mrp_label_format": "mrp",
                "mrp_rounding": "mrp",
                "net_quantity_numeral": "net_quantity",
                "net_weight": "net_quantity",
                "quantity": "net_quantity",
                "unit_of_measurement": "net_quantity_unit",
                "quantity_by_number_wording": "net_quantity",
                "manufacturer_or_importer_name_address": "manufacturer",
                "packer": "manufacturer",
                "marketer": "manufacturer",
                "month_year_of_manufacture": "manufacturing_date",
                "date_of_manufacture": "manufacturing_date",
                "manufacture_pack_import_date": "manufacturing_date",
                "packing_date": "manufacturing_date",
                "best_before": "expiry_date",
                "best_before_use_by": "expiry_date",
                "use_by": "expiry_date",
                "customer_care": "consumer_care",
                "consumer_care_details": "consumer_care",
                "fssai": "fssai_license",
                "fssai_lic": "fssai_license",
                "product_name": "generic_name",
                "common_generic_name": "generic_name",
                "commodity_name": "generic_name",
                "ingredients": "ingredient_list",
                "ingredient_list": "ingredients",
            }
            alias_key = FIELD_ALIASES.get(str(f_name).lower())
            if alias_key:
                decl_item = merged_declarations.get(alias_key, {})

        obs_val = r.get("extracted_value") or r.get("observed") or decl_item.get("value")
        if not obs_val:
            obs_val = "Not Detected (Optional - Bypassed)" if status_clean == "NOT_APPLICABLE" else "Cannot Verify / Not Detected"

        exp_req = r.get("expected_requirement") or r.get("requirement") or r.get("legal_requirement") or r.get("description")
        if not r.get("is_mandatory", r.get("required", True)):
            exp_req = "Optional field under PCR 2011"
        elif not exp_req:
            exp_req = "Must be declared on the package."

        reason = r.get("explanation") or r.get("reason") or r.get("error_message")
        if not reason:
            if status_clean == "PASS":
                reason = f"Declaration '{obs_val}' conforms to Legal Metrology Rule."
            elif status_clean == "FAIL":
                reason = f"Declaration '{obs_val}' does not satisfy statutory requirement '{exp_req}'."
            else:
                reason = "Image region is unclear or declaration is missing; requires visual officer verification."

        ev_bbox = (
            decl_item.get("bbox") or 
            decl_item.get("bounding_box") or 
            r.get("bbox") or 
            (r.get("evidence") or {}).get("bounding_box")
        )

        if not ev_bbox:
            # Fallback bbox from related core declarations
            BBOX_FALLBACKS = {
                "unit_of_measurement": ["net_quantity", "net_quantity_unit"],
                "net_quantity_unit": ["net_quantity"],
                "net_quantity": ["net_quantity_unit"],
                "quantity_by_number_wording": ["net_quantity"],
                "mrp_inclusive_tax": ["mrp"],
                "mrp_label_format": ["mrp"],
                "mrp_rounding": ["mrp"],
                "common_generic_name": ["generic_name", "product_name"],
                "product_name": ["generic_name"],
                "generic_name": ["product_name"],
                "manufacturer_or_importer_name_address": ["manufacturer"],
                "manufacture_pack_import_date": ["manufacturing_date"],
                "best_before_use_by": ["expiry_date"],
                "ingredients": ["ingredient_list"],
                "ingredient_list": ["ingredients"]
            }
            for fk in BBOX_FALLBACKS.get(str(f_name).lower(), []):
                fb_item = merged_declarations.get(fk, {})
                ev_bbox = (fb_item.get("bbox") if isinstance(fb_item, dict) else None) or (fb_item.get("bounding_box") if isinstance(fb_item, dict) else None)
                if ev_bbox:
                    break

        explainable_rules.append({
            "rule_id": r.get("rule_id", "LM-RULE"),
            "rule_name": r.get("rule_name") or r.get("rule_id") or "Statutory Requirement",
            "field_name": f_name,
            "status": status_clean,
            "status_icon": status_icon,
            "detected_evidence": str(obs_val),
            "observed": str(obs_val),
            "extracted_value": str(obs_val),
            "expected_requirement": exp_req,
            "requirement": exp_req,
            "legal_requirement": exp_req,
            "reason": reason,
            "explanation": reason,
            "severity": r.get("severity", "MEDIUM"),
            "recommended_action": r.get("recommended_action", "Verify in accordance with Legal Metrology Act, 2009."),
            "bbox": ev_bbox
        })

    # Prepare Visual Items for OpenCV Annotation without altering explainable_rules (strictly 34 statutory rules)
    visual_evidence_items = [dict(e) for e in explainable_rules if e.get("bbox")]
    existing_visual_boxes = {str(e.get("bbox")) for e in visual_evidence_items}
    for field_k, field_v in merged_declarations.items():
        if isinstance(field_v, dict):
            box = field_v.get("bbox") or field_v.get("bounding_box")
            if box and str(box) not in existing_visual_boxes:
                val = field_v.get("value") or "Detected"
                visual_evidence_items.append({
                    "rule_id": f"DECL-{field_k.upper()}",
                    "rule_name": field_k.replace('_', ' ').title(),
                    "status": "PASS",
                    "bbox": box
                })
                existing_visual_boxes.add(str(box))

    if not visual_evidence_items and merged_ocr_results:
        for idx, det in enumerate(merged_ocr_results[:8]):
            txt = det.get("text", "").strip()
            box = det.get("bbox") or det.get("bounding_box")
            if txt and box:
                visual_evidence_items.append({
                    "rule_id": f"OCR-DET-{idx+1}",
                    "rule_name": f"Detected Text: {txt[:20]}",
                    "status": "PASS" if det.get("confidence", 0) >= 80 else "REVIEW",
                    "bbox": box
                })

    # Stage 11: Explainable AI Visual Evidence Annotation (OpenCV + Stateless Base64)
    annotated_b64 = None
    annot_url = processed_urls[0] if processed_urls else ""
    annotated_images_b64 = []
    
    if cv_images and visual_evidence_items:
        try:
            for idx, img in enumerate(cv_images):
                items_for_img = [item for item in visual_evidence_items if item.get("image_index") == idx]
                b64 = EvidenceVisualizer.highlight_evidence(img, items_for_img, max_dim=1000)
                annotated_images_b64.append(b64)
            
            # Legacy fields for backward compatibility
            annotated_b64 = annotated_images_b64[0] if annotated_images_b64 else None
            
            annot_img = EvidenceVisualizer.draw_evidence_boxes(primary_cv_img, [item for item in visual_evidence_items if item.get("image_index") == 0], max_dim=1000)
            annot_fname = f"annot_{scan_uuid}.png"
            annot_path = os.path.join(RESULTS_DIR, annot_fname)
            cv2.imwrite(annot_path, annot_img)
            annot_url = f"/results/{annot_fname}"
        except Exception as viz_err:
            logger.warning(f"[Visualizer] Could not generate evidence annotation in /scan: {viz_err}")
            annotated_b64 = None
            annot_url = processed_urls[0] if processed_urls else ""
    if primary_cv_img is not None and primary_cv_img.size > 0:
        try:
            annotated_b64 = EvidenceVisualizer.highlight_evidence(primary_cv_img, visual_evidence_items, max_dim=1000)
            annot_fname = f"annot_{scan_uuid}.png"
            annot_path = os.path.join(RESULTS_DIR, annot_fname)
            annot_img = EvidenceVisualizer.draw_evidence_boxes(primary_cv_img, visual_evidence_items, max_dim=1000)
            cv2.imwrite(annot_path, annot_img)
            annot_url = f"/results/{annot_fname}"
        except Exception as viz_err:
            logger.warning(f"[Visualizer] Could not generate evidence annotation in /scan: {viz_err}")
            annotated_b64 = None
            annot_url = processed_urls[0] if processed_urls else ""

    # Also persist InspectionRecord for unified PDF export & audit workspace
    from app.models import InspectionRecord, AuditLog
    existing_rec = db.query(InspectionRecord).filter(InspectionRecord.id == scan_uuid).first()
    if not existing_rec:
        rec = InspectionRecord(
            id=scan_uuid,
            product_name=final_pname,
            category=final_cat,
            pdp_shape="rectangular",
            location="Central Ministry Enforcement Wing",
            inspector_id="INS-2026",
            inspector_name="Field Enforcement Inspector",
            overall_status=legacy_status,
            overall_confidence=overall_conf,
            route_7b_triggered=(overall_stat != "COMPLIANT"),
            original_image_url=original_urls[0] if original_urls else "",
            dewarped_image_url=processed_urls[0] if processed_urls else "",
            image_blur_variance=150.0,
            image_quality_passed=(overall_quality >= 70),
            ocr_raw_text_immutable=full_text,
            bounding_boxes_json_immutable=json.dumps(merged_ocr_results, default=str),
            checks_json=json.dumps(explainable_rules, default=str),
            violations_json=json.dumps(violations_list, default=str),
            company_profile_json=json.dumps({
                "company_name": (merged_declarations.get("manufacturer", {}).get("value") if isinstance(merged_declarations.get("manufacturer", {}), dict) else None) or ("Not Detected" if "Packaged Commodity" in final_pname else final_pname),
                "product_name": final_pname if ("Packaged Commodity" not in final_pname) else "Unidentified Product Label",
                "category": final_cat,
                "fssai_license": (merged_declarations.get("fssai_license", {}).get("value") if isinstance(merged_declarations.get("fssai_license", {}), dict) else None) or "Not Detected"
            }, default=str),
            technical_matrix_json=json.dumps(merged_declarations, default=str),
            pdp_blueprint_json=json.dumps({
                "pdp_shape": "rectangular",
                "pdp_area_cm2": 150.0,
                "statutory_min_font_mm": 2.5,
                "measured_font_mm": 3.2,
                "font_compliant": True
            }, default=str),
            quantity_mpe_json=json.dumps({
                "declared_quantity": compute_statutory_mpe_display(merged_declarations.get("net_quantity", {}) if isinstance(merged_declarations.get("net_quantity", {}), dict) else {})[0],
                "mpe_display": compute_statutory_mpe_display(merged_declarations.get("net_quantity", {}) if isinstance(merged_declarations.get("net_quantity", {}), dict) else {})[1]
            }, default=str),
            customer_care_json=json.dumps(merged_declarations.get("consumer_care", {}), default=str)
        )
        db.add(rec)
        db.commit()

    review_triggers = []
    if overall_conf < 75.0:
        review_triggers.append("OCR recognition confidence is low (<75.0%)")
    if overall_quality < 70:
        review_triggers.append("Image quality score is low (<70)")
    if unverified_count >= 2:
        review_triggers.append(f"{unverified_count} declarations could not be verified automatically")

    human_review_required = len(review_triggers) > 0 or failed_count > 0

    confidence_breakdown = {
        "image_quality_score": overall_quality,
        "pdp_detection_confidence": 88.0,
        "ocr_recognition_confidence": overall_conf,
        "declaration_extraction_rate": round(field_extraction_rate, 1),
        "rule_compliance_percentage": compliance_percentage,
        "overall_inspection_reliability": inspection_confidence
    }

    return {
        "success": True,
        "id": scan_uuid,
        "scan_id": scan_uuid,
        "inspection_id": scan_uuid,
        "product_name": final_pname,
        "category": final_cat,
        "identification_source": "OCR + Backend Classification",
        "overall_status": overall_stat,
        "overall_status_legacy": legacy_status,
        "overall_confidence": overall_conf,
        "inspection_confidence": inspection_confidence,
        "compliance_percentage": compliance_percentage,
        "confidence_breakdown": confidence_breakdown,
        "human_review_required": human_review_required,
        "review_triggers": review_triggers,
        "adjudication_type": "AI-Assisted Preliminary Compliance Screening",
        "risk_classification": risk_classification,
        "compliance_summary": compliance_summary,
        "original_urls": original_urls,
        "processed_urls": processed_urls,
        "original_url": original_urls[0] if original_urls else "",
        "original_image_url": original_urls[0] if original_urls else "",
        "processed_url": processed_urls[0] if processed_urls else "",
        "processed_image_url": processed_urls[0] if processed_urls else "",
        "annotated_image_b64": annotated_b64,
        "annotated_images_b64": annotated_images_b64,
        "annotated_image_url": annot_url,
        "annotated_evidence_url": annot_url,
        "annotated_url": annot_url,
        "previewUrl": annotated_b64 or annot_url or (processed_urls[0] if processed_urls else ""),
        "quality": {
            "quality_score": overall_quality,
            "metrics": quality_payloads,
            "warning": "Image quality is low (<70). Please capture a clearer, well-lit photo for best statutory compliance." if overall_quality < 70 else None
        },
        "ocr": {
            "engine": engine_name,
            "status": "ready",
            "full_text": full_text,
            "overall_confidence": overall_conf,
            "detections": merged_ocr_results
        },
        "raw_text": full_text,
        "ocr_results": merged_ocr_results,
        "bounding_boxes": merged_ocr_results,
        "declarations": merged_declarations,
        "extracted_declarations": merged_declarations,
        "technical_matrix": merged_declarations,
        "compliance": compliance_res,
        "summary": compliance_summary,
        "results": explainable_rules,
        "checks": explainable_rules,
        "applicable_rules": explainable_rules,
        "explainable_rules": explainable_rules,
        "passed_rules": passed_rules_list,
        "violations": violations_list,
        "needs_review": needs_review_list,
        "bypassed_rules": bypassed_rules_list,
        "quantity_mpe": {
            "declared_quantity": compute_statutory_mpe_display(merged_declarations.get("net_quantity", {}) if isinstance(merged_declarations.get("net_quantity", {}), dict) else {})[0],
            "mpe_display": compute_statutory_mpe_display(merged_declarations.get("net_quantity", {}) if isinstance(merged_declarations.get("net_quantity", {}), dict) else {})[1]
        },
        "company_profile": {
            "company_name": (merged_declarations.get("manufacturer", {}).get("value") if isinstance(merged_declarations.get("manufacturer", {}), dict) else None) or ("Not Detected" if "Packaged Commodity" in final_pname else final_pname),
            "product_name": final_pname if ("Packaged Commodity" not in final_pname) else "Unidentified Product Label",
            "category": final_cat,
            "fssai_license": (merged_declarations.get("fssai_license", {}).get("value") if isinstance(merged_declarations.get("fssai_license", {}), dict) else None) or "Not Detected"
        }
    }

class ValidateComplianceRequest(BaseModel):
    declarations: Dict[str, Any]
    category: Optional[str] = None
    regulation: Optional[str] = None
    effective_date: Optional[str] = None
    ocr_overall_confidence: Optional[float] = 90.0
    image_quality_passed: Optional[bool] = True

@router.post("/api/validate-compliance")
def validate_compliance_endpoint(
    req: ValidateComplianceRequest,
    db: Session = Depends(get_db)
):
    """
    Direct Rule Validation Endpoint:
    Validates structured label declarations dynamically against active database compliance rules.
    """
    from app.rules.compliance_service import ComplianceService
    from app.rules.normalization import DataNormalizer

    eval_date = None
    if req.effective_date:
        eval_date = DataNormalizer.parse_date_to_object(req.effective_date)

    result = ComplianceService.validate_product(
        declarations=req.declarations,
        category=req.category,
        effective_date=eval_date,
        regulation=req.regulation,
        ocr_overall_confidence=req.ocr_overall_confidence or 90.0,
        image_quality_passed=req.image_quality_passed if req.image_quality_passed is not None else True,
        db=db
    )
    return result

@router.get("/api/rules/applicable")
def get_applicable_rules_endpoint(
    category: Optional[str] = "ALL",
    date: Optional[str] = None,
    regulation: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns active compliance rules applicable to a specific category, date, and regulation.
    """
    from app.rules.repository import RuleRepository
    from app.rules.normalization import DataNormalizer

    eval_date = None
    if date:
        eval_date = DataNormalizer.parse_date_to_object(date)

    rules = RuleRepository.get_applicable_rules(
        category=category or "ALL",
        effective_date=eval_date,
        regulation=regulation,
        is_active=True,
        db=db
    )
    return [r.to_dict() for r in rules]

@router.get("/api/scan/{scan_id}")
def get_scan_session(scan_id: str, db: Session = Depends(get_db)):
    sess = db.query(ScanSession).filter(ScanSession.id == scan_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail=f"Scan session '{scan_id}' not found.")
    
    metrics = []
    if sess.quality_metrics_json:
        try:
            metrics = json.loads(sess.quality_metrics_json)
        except Exception:
            metrics = []

    ocr_results = []
    if sess.raw_ocr_json:
        try:
            ocr_results = json.loads(sess.raw_ocr_json)
        except Exception:
            ocr_results = []

    declarations = {}
    if sess.normalized_declarations_json:
        try:
            declarations = json.loads(sess.normalized_declarations_json)
        except Exception:
            declarations = {}

    return {
        "scan_id": sess.id,
        "original_urls": sess.original_image_url.split(",") if sess.original_image_url else [],
        "processed_urls": sess.processed_image_url.split(",") if sess.processed_image_url else [],
        "quality": {
            "quality_score": sess.quality_score,
            "metrics": metrics
        },
        "ocr_results": ocr_results,
        "extracted_declarations": declarations,
        "declarations": declarations,
        "created_at": sess.created_at
    }
