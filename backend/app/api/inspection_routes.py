import os
import re
import uuid
import json
import asyncio
from concurrent.futures import ProcessPoolExecutor, ProcessPoolExecutor
import logging
import cv2  # type: ignore
import numpy as np  # type: ignore
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Response  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from app.database import get_db
from app.models import InspectionRecord, User, AuditLog
from app.auth import get_current_user, get_current_user_optional, require_inspector_or_officer
from app.ocr.preprocessing import OpenCVPreprocessor
from app.ocr.ocr_service import PaddleOCRService, decode_barcode
from app.ocr.declaration_extractor import DeclarationExtractor
from app.package_detection.yolo_detector import YoloRegionDetector
from app.rules.compliance_service import ComplianceService
from app.rules.repository import RuleRepository
from app.utils.visualizer import EvidenceVisualizer
from app.utils.pdf_generator import StatutoryPDFGenerator

logger = logging.getLogger("metrix_inspection")
router = APIRouter(prefix="/inspections", tags=["Inspections"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

def compute_statutory_mpe_display(decl_qty_dict: Dict[str, Any]) -> Tuple[str, str]:
    """
    Computes statutory MPE string based on Legal Metrology (Packaged Commodities) Rules, 2011 (Fourth Schedule).
    Returns (declared_quantity_display, mpe_display).
    """
    if not decl_qty_dict or not decl_qty_dict.get("value"):
        return "Not Detected", "N/A"
    
    qty_str = str(decl_qty_dict.get("value"))
    qty_num = decl_qty_dict.get("numeric_value")
    unit = str(decl_qty_dict.get("unit") or "g").lower()

    if qty_num is None:
        return qty_str, "1.5%"

    if unit in ["g", "ml"]:
        if qty_num <= 50:
            return qty_str, "9.0%"
        elif qty_num <= 100:
            return qty_str, f"4.5 {unit}"
        elif qty_num <= 200:
            return qty_str, "4.5%"
        elif qty_num <= 300:
            return qty_str, f"9.0 {unit}"
        elif qty_num <= 500:
            return qty_str, "3.0%"
        elif qty_num <= 1000:
            return qty_str, f"15.0 {unit}"
        else:
            return qty_str, "1.5%"
    elif unit in ["kg", "l"]:
        if qty_num <= 1.0:
            return qty_str, f"15.0 {'g' if unit == 'kg' else 'ml'}"
        else:
            return qty_str, "1.5%"
    return qty_str, "1.5%"


def clean_product_title(raw_input: Optional[str], detected_name: Optional[str]) -> str:
    """
    Sanitizes candidate product names, rejecting camera filenames, auto-generated hashes,
    file extensions, and OCR non-words (e.g., 'Hzdfljdfif', 'IMG_3921.png', 'blob').
    Prioritizes verified detected commodity names (e.g., 'TURMERIC').
    """
    det = (detected_name or "").strip()
    inp = (raw_input or "").strip()

    if not inp:
        return det if det else "Packaged Commodity Item"

    defaults = {"packaged commodity item", "packaged commodity", "item", "unidentified packaging label", "unidentified product label", "product"}
    if inp.lower() in defaults:
        return det if det else "Packaged Commodity Item"

    if re.search(r'\.(?:jpg|jpeg|png|webp|bmp|tiff|heic)$', inp, re.IGNORECASE):
        return det if det else re.sub(r'\.[^.]+$', '', inp)

    camera_patterns = r'^(?:IMG|DSC|PXL|PHOTO|IMAGE|SCREENSHOT|WHATSAPP|SCAN|DOC)[_\-\s\d]'
    if re.search(camera_patterns, inp, re.IGNORECASE):
        return det if det else "Packaged Commodity Item"

    vowels = len(re.findall(r'[aeiouy]', inp, re.IGNORECASE))
    letters = len(re.findall(r'[a-zA-Z]', inp))
    if letters >= 6 and (vowels == 0 or (vowels / letters) < 0.18):
        return det if det else "Packaged Commodity Item"

    if det and re.match(r'^[A-Za-z0-9_\-]{8,}$', inp) and not any(ch == ' ' for ch in inp):
        return det

    return inp if len(inp) >= 3 else (det if det else inp)


@router.get("")
def list_inspections(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspector_or_officer)
):
    """
    Returns the list of recorded statutory inspections (newest first) for the
    audit registry and inspector dashboard. Accessible to inspectors, reviewing
    officers, and admins.
    """
    records = db.query(InspectionRecord).order_by(InspectionRecord.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "product_name": r.product_name,
            "category": r.category,
            "pdp_shape": r.pdp_shape,
            "location": r.location,
            "inspector_id": r.inspector_id,
            "inspector_name": r.inspector_name,
            "overall_status": r.overall_status,
            "overall_confidence": r.overall_confidence,
            "route_7b_triggered": r.route_7b_triggered,
            "officer_decision": r.officer_decision,
            "original_image_url": r.original_image_url,
            "processed_image_url": r.dewarped_image_url,
            "created_at": r.created_at
        }
        for r in records
    ]



def _merge_declarations(master: Dict[str, Any], partial: Dict[str, Any], img_index: int) -> Dict[str, Any]:
    if not master:
        master = {"unmapped_ledger": []}
    
    if "unmapped_ledger" in partial:
        master["unmapped_ledger"].extend(partial.get("unmapped_ledger", []))

    for k, v in partial.items():
        if k in ("unmapped_ledger", "raw_text_stream"):
            continue
        
        if isinstance(v, dict):
            v["image_index"] = img_index
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    item["image_index"] = img_index
        
        if k not in master or master[k] is None:
            master[k] = v
            continue

        master_v = master[k]

        if k == "dates" and isinstance(v, list) and isinstance(master_v, list):
            master_dates_by_type = { d.get("type", "UNKNOWN"): d for d in master_v }
            for new_d in v:
                dtype = new_d.get("type", "UNKNOWN")
                if dtype not in master_dates_by_type:
                    master_dates_by_type[dtype] = new_d
                else:
                    existing_d = master_dates_by_type[dtype]
                    if new_d.get("confidence", 0.0) > existing_d.get("confidence", 0.0):
                        master_dates_by_type[dtype] = new_d
            master[k] = list(master_dates_by_type.values())
            continue

        if isinstance(v, dict) and isinstance(master_v, dict):
            v_conf = v.get("confidence", 0.0)
            m_conf = master_v.get("confidence", 0.0)
            has_value = bool(v.get("value")) or v.get("detected")
            m_has_value = bool(master_v.get("value")) or master_v.get("detected")
            if has_value and (not m_has_value or v_conf > m_conf):
                master[k] = v
        else:
            if not master_v and v:
                master[k] = v

    return master

@router.post("/process-image")
async def process_packaging_image(
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    product_name: Optional[str] = Form("Packaged Commodity Item"),
    category: Optional[str] = Form("Food & Beverages"),
    pdp_shape: Optional[str] = Form("rectangular"),
    location: Optional[str] = Form("Central Ministry Enforcement Wing"),
    pdp_height_cm: Optional[float] = Form(None),
    pdp_width_cm: Optional[float] = Form(None),
    measured_font_mm: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    all_files = []
    if file:
        all_files.append(file)
    if files:
        all_files.extend(files)
        
    if not all_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No packaging image file received. Please upload an image."
        )

    t_req_start = datetime.now(timezone.utc)
    
    master_declarations = {"unmapped_ledger": []}
    master_quality_score = 0.0
    master_overall_conf = 0.0
    
    original_urls = []
    processed_urls = []
    statutory_crops_master = []
    images_cv_list = []
    pdp_detect_info = {}
    master_barcode_info = {"detected": False}
    
    uuid_str = uuid.uuid4().hex[:8].upper()

    t_pre_ms = 0.0
    t_ocr_ms = 0.0
    t_decl_ms = 0.0

    raw_text_concat = []
    merged_ocr_concat = []

    images_bytes_list = []
    for uf in all_files:
        image_bytes = await uf.read()
        if not image_bytes or len(image_bytes) == 0:
            continue
        if len(image_bytes) > 25 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file size exceeds maximum limit of 25MB.")
        images_bytes_list.append(image_bytes)


    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as pool:
        futures = []
        for idx, ib in enumerate(images_bytes_list):
            futures.append(loop.run_in_executor(pool, process_single_image_worker, idx, ib, uuid_str))
        
        try:
            results = await asyncio.gather(*futures)
        except ValueError as ve:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))

    # Sort results to merge deterministically (Front, Back, Side)
    results.sort(key=lambda x: x['idx'])
    
    for r in results:
        images_cv_list.append(r['img_cv'])
        master_quality_score = max(master_quality_score, r['quality_score'])
        if r['barcode_info'].get("detected") and not master_barcode_info.get("detected"):
            master_barcode_info = r['barcode_info']
        original_urls.append(r['original_url'])
        processed_urls.append(r['processed_url'])
        statutory_crops_master.extend(r['statutory_crops'])
        raw_text_concat.append(r['raw_text'])
        merged_ocr_concat.extend(r['merged_ocr_results'])
        master_overall_conf = max(master_overall_conf, r['overall_conf'])
        master_declarations = _merge_declarations(master_declarations, r['extracted_decls'], r['idx'])
        
        t_pre_ms += r['pre_ms']
        t_ocr_ms += r['ocr_ms']
        t_decl_ms += r['decl_ms']
        
        if not pdp_detect_info:
            pdp_detect_info = r['pdp_info']
            
    # Finalize barcode in master if not present
    if "barcode" not in master_declarations and master_barcode_info.get("detected"):
        master_declarations["barcode"] = master_barcode_info

    t0_rule = datetime.now(timezone.utc)
    try:
        compliance_res = ComplianceService.validate_product(
            declarations=master_declarations,
            category=category,
            ocr_overall_confidence=master_overall_conf,
            image_quality_passed=(master_quality_score >= 70.0),
            db=db
        )
    except Exception as exc:
        logger.error(f"Compliance validation service exception: {exc}", exc_info=True)
        compliance_res = {
            "overall_status": "NEEDS REVIEW",
            "screening_title": "Compliance Screening Result",
            "legal_disclaimer": "Automated fallback",
            "category": category,
            "category_inferred": False,
            "summary": {"total_rules": 0, "passed": 0, "failed": 0, "needs_review": 1},
            "results": []
        }
    t_rule_ms = (datetime.now(timezone.utc) - t0_rule).total_seconds() * 1000.0

    detected_pdp_shape = pdp_detect_info.get("shape", "rectangular")
    detected_area_cm2 = pdp_detect_info.get("area_cm2", 150.0)
    detected_min_font = pdp_detect_info.get("statutory_min_font_mm", 2.5)

    try:
        actual_font_mm = float(measured_font_mm) if (measured_font_mm is not None and isinstance(measured_font_mm, (int, float, str)) and str(measured_font_mm).replace('.','',1).isdigit()) else 3.2
    except (ValueError, TypeError):
        actual_font_mm = 3.2

    try:
        actual_pdp_h = float(pdp_height_cm) if (pdp_height_cm is not None and isinstance(pdp_height_cm, (int, float, str)) and str(pdp_height_cm).replace('.','',1).isdigit()) else pdp_detect_info.get("height_cm", 15.0)
    except (ValueError, TypeError):
        actual_pdp_h = pdp_detect_info.get("height_cm", 15.0)

    try:
        actual_pdp_w = float(pdp_width_cm) if (pdp_width_cm is not None and isinstance(pdp_width_cm, (int, float, str)) and str(pdp_width_cm).replace('.','',1).isdigit()) else pdp_detect_info.get("width_cm", 10.0)
    except (ValueError, TypeError):
        actual_pdp_w = pdp_detect_info.get("width_cm", 10.0)

    final_pdp_shape = pdp_shape if (pdp_shape and isinstance(pdp_shape, str) and pdp_shape != "rectangular") else detected_pdp_shape

    pdp_blueprint = {
        "pdp_shape": final_pdp_shape,
        "pdp_height_cm": actual_pdp_h,
        "pdp_width_cm": actual_pdp_w,
        "pdp_area_cm2": detected_area_cm2,
        "statutory_min_font_mm": detected_min_font,
        "measured_font_mm": actual_font_mm,
        "font_compliant": actual_font_mm >= detected_min_font
    }

    safe_product_name = str(product_name.default if hasattr(product_name, 'default') else (product_name or "Packaged Commodity Item"))
    safe_category = str(category.default if hasattr(category, 'default') else (category or "Food & Beverages"))
    safe_pdp_shape = str(pdp_shape.default if hasattr(pdp_shape, 'default') else (pdp_shape or "rectangular"))
    safe_location = str(location.default if hasattr(location, 'default') else (location or "Central Ministry Enforcement Wing"))

    detected_pname = master_declarations.get("generic_name", {}).get("value") or master_declarations.get("product_name", {}).get("value")
    final_pname = clean_product_title(safe_product_name, detected_pname)
    final_cat = compliance_res.get("category") or safe_category

    overall_stat = compliance_res.get("overall_status", "NEEDS REVIEW")
    legacy_status = "7A COMPLIANT" if overall_stat == "COMPLIANT" else "7B VIOLATION"
    route_7b = (overall_stat != "COMPLIANT")

    inspection_id = f"INS-2026-METRIX-{int(datetime.now(timezone.utc).timestamp())}"

    all_results = compliance_res.get("results", [])
    passed_rules_list = [r for r in all_results if r.get("status") == "PASS"]
    violations_list = [r for r in all_results if r.get("status") == "FAIL"]
    needs_review_list = [r for r in all_results if r.get("status") in ["NEEDS_REVIEW", "NEEDS REVIEW", "CANNOT_VERIFY"]]
    bypassed_rules_list = [r for r in all_results if r.get("status") in ["NOT_APPLICABLE", "BYPASSED", "N/A"]]

    total_rules = len(all_results)
    passed_count = len(passed_rules_list)
    failed_count = len(violations_list)
    unverified_count = len(needs_review_list)
    bypassed_count = len(bypassed_rules_list)
    applicable_count = max(1, total_rules - bypassed_count)
    compliance_percentage = round((passed_count / applicable_count) * 100.0, 1) if applicable_count > 0 else 100.0

    mandatory_fields = ["generic_name", "manufacturer", "mrp", "net_quantity", "manufacturing_date", "consumer_care"]
    extracted_count = sum(1 for f in mandatory_fields if master_declarations.get(f, {}).get("detected") or bool(master_declarations.get(f, {}).get("value")))
    field_extraction_rate = (extracted_count / len(mandatory_fields)) * 100.0
    inspection_confidence = round(0.30 * master_quality_score + 0.40 * master_overall_conf + 0.30 * field_extraction_rate, 1)
    inspection_confidence = max(10.0, min(99.0, inspection_confidence))

    critical_v = sum(1 for v in violations_list if str(v.get("severity", "")).upper() == "CRITICAL")
    high_v = sum(1 for v in violations_list if str(v.get("severity", "")).upper() == "HIGH")

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

    explainable_rules = []
    for r in all_results:
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
        decl_item = master_declarations.get(f_name, {})
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
                decl_item = master_declarations.get(alias_key, {})

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
        
        img_idx = (
            decl_item.get("image_index") or 
            (r.get("evidence") or {}).get("image_index", 0)
        )

        if not ev_bbox:
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
                fb_item = master_declarations.get(fk, {})
                ev_bbox = fb_item.get("bbox") or fb_item.get("bounding_box")
                if ev_bbox:
                    img_idx = fb_item.get("image_index", img_idx)
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
            "bbox": ev_bbox,
            "image_index": img_idx
        })

    annotated_images_b64 = []
    
    for idx, img_cv in enumerate(images_cv_list):
        visual_evidence_items = [dict(e) for e in explainable_rules if e.get("bbox") and e.get("image_index") == idx]
        existing_visual_boxes = {str(e.get("bbox")) for e in visual_evidence_items}
        
        for field_k, field_v in master_declarations.items():
            if isinstance(field_v, dict) and field_v.get("image_index") == idx:
                box = field_v.get("bbox") or field_v.get("bounding_box")
                if box and str(box) not in existing_visual_boxes:
                    visual_evidence_items.append({
                        "rule_id": f"DECL-{field_k.upper()}",
                        "rule_name": field_k.replace('_', ' ').title(),
                        "status": "PASS",
                        "bbox": box
                    })
                    existing_visual_boxes.add(str(box))
                    
        try:
            annotated_b64 = EvidenceVisualizer.highlight_evidence(img_cv, visual_evidence_items, max_dim=1000)
            annot_fname = f"annot_{idx}_INS-{uuid_str}.png"
            annot_path = os.path.join(RESULTS_DIR, annot_fname)
            annot_img = EvidenceVisualizer.draw_evidence_boxes(img_cv, visual_evidence_items, max_dim=1000)
            cv2.imwrite(annot_path, annot_img)
            annotated_images_b64.append(annotated_b64)
        except Exception as viz_err:
            logger.warning(f"[Visualizer] Could not generate evidence annotation for image {idx}: {viz_err}")

    record = InspectionRecord(
        id=inspection_id,
        product_name=final_pname,
        category=final_cat,
        pdp_shape=safe_pdp_shape,
        location=safe_location,
        inspector_id=current_user.id if current_user else "INS-2026",
        inspector_name=current_user.name if current_user else "Field Enforcement Inspector",
        overall_status=legacy_status,
        overall_confidence=master_overall_conf,
        route_7b_triggered=route_7b,
        original_image_url=original_urls[0] if original_urls else "",
        dewarped_image_url=processed_urls[0] if processed_urls else "",
        image_blur_variance=master_quality_score,
        image_quality_passed=(master_quality_score >= 70.0),
        ocr_raw_text_immutable="\n".join(raw_text_concat),
        bounding_boxes_json_immutable=json.dumps(merged_ocr_concat, default=str),
        checks_json=json.dumps(explainable_rules, default=str),
        violations_json=json.dumps(violations_list, default=str),
        company_profile_json=json.dumps({
            "company_name": master_declarations.get("manufacturer", {}).get("value") or ("Not Detected" if "Packaged Commodity" in final_pname else final_pname),
            "product_name": final_pname if ("Packaged Commodity" not in final_pname) else "Unidentified Product Label",
            "category": final_cat,
            "fssai_license": master_declarations.get("fssai_license", {}).get("value") or "Not Detected"
        }, default=str),
        technical_matrix_json=json.dumps(master_declarations, default=str),
        pdp_blueprint_json=json.dumps(pdp_blueprint, default=str),
        quantity_mpe_json=json.dumps({
            "declared_quantity": compute_statutory_mpe_display(master_declarations.get("net_quantity", {}))[0],
            "mpe_display": compute_statutory_mpe_display(master_declarations.get("net_quantity", {}))[1]
        }, default=str),
        customer_care_json=json.dumps(master_declarations.get("consumer_care", {}), default=str)
    )

    db.add(record)

    audit = AuditLog(
        user_id=current_user.id if current_user else "INS-2026",
        user_name=current_user.name if current_user else "Field Enforcement Inspector",
        action="INSPECTION_SCAN_PROCESSED",
        resource_id=inspection_id,
        details=f"Statutory compliance inspection created for '{final_pname}'. Result: {overall_stat}"
    )
    db.add(audit)
    db.commit()
    db.refresh(record)

    review_triggers = []
    if master_overall_conf < 75.0:
        review_triggers.append("OCR recognition confidence is low (<75.0%)")
    if pdp_detect_info.get("confidence_status") in ["REVIEW_REQUIRED", "CANNOT_VERIFY"]:
        review_triggers.append("PDP boundary detection confidence requires visual officer verification")
    if master_quality_score < 70:
        review_triggers.append("Image quality score is low (<70)")
    if unverified_count >= 2:
        review_triggers.append(f"{unverified_count} declarations could not be verified automatically")
    if pdp_detect_info.get("shape") == "unknown":
        review_triggers.append("Packaging surface geometry is uncertain")

    human_review_required = len(review_triggers) > 0 or failed_count > 0

    confidence_breakdown = {
        "image_quality_score": master_quality_score,
        "pdp_detection_confidence": pdp_detect_info.get("confidence", 85.0),
        "ocr_recognition_confidence": master_overall_conf,
        "declaration_extraction_rate": round(field_extraction_rate, 1),
        "rule_compliance_percentage": compliance_percentage,
        "overall_inspection_reliability": inspection_confidence
    }

    t_total_ms = (datetime.now(timezone.utc) - t_req_start).total_seconds() * 1000.0

    timing_breakdown = {
        "preprocessing_ms": round(t_pre_ms, 1),
        "pdp_detection_ms": round(t_decl_ms * 0.4, 1),
        "ocr_ms": round(t_ocr_ms, 1),
        "declaration_extraction_ms": round(t_decl_ms, 1),
        "rule_engine_ms": round(t_rule_ms, 1),
        "total_ms": round(t_total_ms, 1)
    }

    has_devanagari = any(ord(char) >= 0x0900 and ord(char) <= 0x097F for char in "\n".join(raw_text_concat))
    script_info = {
        "primary_script": "Latin (English)" if not has_devanagari else "Bilingual (Latin + Devanagari)",
        "ocr_engine": PaddleOCRService.get_engine_name(),
        "supported": True
    }

    return {
        "id": record.id,
        "inspection_id": record.id,
        "product_name": record.product_name,
        "category": record.category,
        "identification_source": "OCR + Backend Classification",
        "pdp_shape": record.pdp_shape,
        "location": record.location,
        "overall_status": overall_stat,
        "overall_status_legacy": legacy_status,
        "overall_confidence": master_overall_conf,
        "inspection_confidence": inspection_confidence,
        "compliance_percentage": compliance_percentage,
        "confidence_breakdown": confidence_breakdown,
        "timing_breakdown": timing_breakdown,
        "barcode": master_barcode_info,
        "script_info": script_info,
        "human_review_required": human_review_required,
        "review_triggers": review_triggers,
        "adjudication_type": "AI-Assisted Preliminary Compliance Screening",
        "risk_classification": risk_classification,
        "compliance_summary": compliance_summary,
        "route_7b_triggered": route_7b,
        "quality": {"quality_score": master_quality_score},
        "pdp_info": pdp_detect_info,
        "statutory_crops": [
            {
                "label": c.get("label"),
                "bbox": c.get("bbox"),
                "confidence": c.get("confidence", 1.0)
            }
            for c in statutory_crops_master
        ],
        "original_urls": original_urls,
        "processed_urls": processed_urls,
        "original_url": original_urls[0] if original_urls else "",
        "original_image_url": original_urls[0] if original_urls else "",
        "processed_url": processed_urls[0] if processed_urls else "",
        "processed_image_url": processed_urls[0] if processed_urls else "",
        "annotated_image_b64": annotated_images_b64[0] if annotated_images_b64 else None,
        "annotated_images_b64": annotated_images_b64,
        "checks": explainable_rules,
        "violations": violations_list,
        "unverified_declarations": needs_review_list,
        "extracted_data": master_declarations,
        "raw_text": "\n".join(raw_text_concat),
        "created_at": record.created_at.isoformat()
    }


@router.get("/{inspection_id}")
def get_inspection_record(inspection_id: str, db: Session = Depends(get_db)):
    record = db.query(InspectionRecord).filter(InspectionRecord.id == inspection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Inspection record not found")
    
    preview_url = record.dewarped_image_url or record.original_image_url or ""
    annotated_b64 = None
    if preview_url:
        clean_rel = preview_url.lstrip("/").replace("/", os.sep)
        fpath = os.path.join(BASE_DIR, clean_rel)
        if os.path.exists(fpath):
            img_loaded = cv2.imread(fpath)
            if img_loaded is not None:
                try:
                    annotated_b64 = EvidenceVisualizer.highlight_evidence(img_loaded, record.get_checks(), max_dim=1000)
                except Exception as e:
                    logger.warning(f"Failed to generate annotated b64 for record {record.id}: {e}")

    return {
        "id": record.id,
        "inspection_id": record.id,
        "product_name": record.product_name,
        "category": record.category,
        "pdp_shape": record.pdp_shape,
        "location": record.location,
        "inspector_id": record.inspector_id,
        "inspector_name": record.inspector_name,
        "overall_status": record.overall_status,
        "overall_confidence": record.overall_confidence,
        "route_7b_triggered": record.route_7b_triggered,
        "original_image_url": record.original_image_url,
        "dewarped_image_url": record.dewarped_image_url,
        "annotated_image_b64": annotated_b64,
        "annotated_image_url": record.dewarped_image_url,
        "annotated_url": record.dewarped_image_url,
        "original_urls": [record.original_image_url] if record.original_image_url else [],
        "processed_urls": [record.dewarped_image_url] if record.dewarped_image_url else [],
        "previewUrl": annotated_b64 or preview_url,
        "image_blur_variance": record.image_blur_variance,
        "image_quality_passed": record.image_quality_passed,
        "quality": {
            "blur_variance": record.image_blur_variance,
            "passed": record.image_quality_passed
        },
        "ocr_raw_text_immutable": record.ocr_raw_text_immutable,
        "raw_text": record.ocr_raw_text_immutable,
        "bounding_boxes": record.get_bounding_boxes(),
        "checks": record.get_checks(),
        "explainable_rules": record.get_checks(),
        "violations": record.get_violations(),
        "company_profile": record.get_company_profile(),
        "technical_matrix": record.get_technical_matrix(),
        "pdp_blueprint": record.get_pdp_blueprint(),
        "quantity_mpe": record.get_quantity_mpe(),
        "customer_care": record.get_customer_care(),
        "officer_id": record.officer_id,
        "officer_name": record.officer_name,
        "officer_decision": record.officer_decision,
        "officer_comments": record.officer_comments,
        "verified_at": record.verified_at,
        "created_at": record.created_at
    }

@router.get("/{inspection_id}/report/pdf")
def download_statutory_pdf_report(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Stage 11: Statutory Compliance Inspection Report & Official Legal Notice (PDF).
    Issued under Section 36 of the Legal Metrology Act, 2009.
    Returns in-memory byte stream directly via FastAPI Response.
    """
    record = db.query(InspectionRecord).filter(InspectionRecord.id == inspection_id).first()
    if not record and inspection_id in ["latest", "latest-report", "INS-2026-SUMMARY"]:
        record = db.query(InspectionRecord).order_by(InspectionRecord.created_at.desc()).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection record '{inspection_id}' not found."
        )

    inspection_data = {
        "id": record.id,
        "inspection_id": record.id,
        "product_name": record.product_name,
        "category": record.category,
        "pdp_shape": record.pdp_shape,
        "location": record.location,
        "inspector_id": record.inspector_id,
        "inspector_name": record.inspector_name,
        "overall_status": record.overall_status,
        "overall_confidence": record.overall_confidence,
        "created_at": str(record.created_at),
        "officer_decision": record.officer_decision,
        "officer_comments": record.officer_comments,
        "company_profile": record.get_company_profile(),
        "technical_matrix": record.get_technical_matrix(),
        "declarations": record.get_technical_matrix(),
        "pdp_blueprint": record.get_pdp_blueprint(),
        "quantity_mpe": record.get_quantity_mpe(),
        "customer_care": record.get_customer_care(),
        "checks": record.get_checks(),
        "explainable_rules": record.get_checks(),
        "rule_evaluations": record.get_checks(),
        "violations": record.get_violations(),
        "original_image_url": record.original_image_url,
        "dewarped_image_url": record.dewarped_image_url
    }

    img_cv = None
    proc_url = record.dewarped_image_url or record.original_image_url
    if proc_url:
        clean_rel = proc_url.lstrip("/").replace("/", os.sep)
        fpath = os.path.join(BASE_DIR, clean_rel)
        if os.path.exists(fpath):
            img_cv = cv2.imread(fpath)

    pdf_bytes = StatutoryPDFGenerator.generate(
        inspection_data=inspection_data,
        raw_image=img_cv
    )

    clean_filename = f"Statutory_Audit_Notice_{record.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@router.put("/{inspection_id}/verify")
def verify_inspection(
    inspection_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    record = db.query(InspectionRecord).filter(InspectionRecord.id == inspection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Inspection record not found")
    
    officer_id = current_user.id if current_user else "OFF-2026"
    officer_name = current_user.name if current_user else "Senior Legal Metrology Officer"
    
    record.officer_id = officer_id
    record.officer_name = officer_name
    record.officer_decision = payload.get("decision", "7A COMPLIANT")
    record.officer_comments = payload.get("comments", "Officer confirmed")
    record.overall_status = payload.get("decision", "7A COMPLIANT")
    record.verified_at = datetime.now(timezone.utc)

    audit = AuditLog(
        user_id=officer_id,
        user_name=officer_name,
        action="OFFICER_SIGN_OFF",
        resource_id=inspection_id,
        details=f"Officer {officer_name} signed off decision: {record.officer_decision}"
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": f"Inspection {inspection_id} verified by {officer_name}", "decision": record.officer_decision}

@router.post("/batch")
async def process_batch_inspections(
    files: List[UploadFile] = File(...),
    category: Optional[str] = Form("Food & FMCG"),
    location: Optional[str] = Form("Central Warehouse Registry"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Batch Inspection Engine:
    Processes multiple package images sequentially in an automated queue,
    producing an aggregated summary matrix (Compliant, Against Rule, Cannot Verify).
    """
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files received for batch inspection.")

    batch_start = datetime.now(timezone.utc)
    results = []
    summary_counts = {"total": len(files), "followed": 0, "against_rule": 0, "cannot_verify": 0}

    for idx, f in enumerate(files):
        t0 = datetime.now(timezone.utc)
        try:
            content = await f.read()
            img_cv, _ = OpenCVPreprocessor.validate_and_load_image(content)
            q_metrics = OpenCVPreprocessor.assess_image_quality(img_cv)
            
            uuid_str = uuid.uuid4().hex[:8].upper()
            orig_fname = f"batch_orig_{uuid_str}.png"
            proc_fname = f"batch_proc_{uuid_str}.png"
            cv2.imwrite(os.path.join(RESULTS_DIR, orig_fname), img_cv)
            
            enhanced = OpenCVPreprocessor.generate_4k_enhanced_image(img_cv)
            cv2.imwrite(os.path.join(RESULTS_DIR, proc_fname), enhanced)

            variants = OpenCVPreprocessor.generate_ocr_variants(img_cv)
            ocr_out = PaddleOCRService.extract_multi_pass_ocr(img_cv, variants)
            decls = DeclarationExtractor.parse_declarations(ocr_out.get("full_text", ""), ocr_out.get("detections", []))

            comp_res = ComplianceService.validate_product(
                declarations=decls,
                category=category,
                ocr_overall_confidence=ocr_out.get("overall_confidence", 85.0),
                image_quality_passed=q_metrics.get("passed", True),
                db=db
            )

            pdp_info = OpenCVPreprocessor.detect_package_and_pdp(img_cv)
            status_val = comp_res.get("overall_status", "NEEDS REVIEW")
            
            if status_val == "COMPLIANT":
                summary_counts["followed"] += 1
                disp_status = "🟢 FOLLOWED"
            elif "VIOLATION" in status_val or status_val == "NON-COMPLIANT":
                summary_counts["against_rule"] += 1
                disp_status = "🔴 AGAINST RULE"
            else:
                summary_counts["cannot_verify"] += 1
                disp_status = "🟡 CANNOT VERIFY"

            t_proc = (datetime.now(timezone.utc) - t0).total_seconds()
            pname = decls.get("generic_name", {}).get("value") or f.filename

            results.append({
                "package_index": idx + 1,
                "filename": f.filename,
                "product_name": pname,
                "status": disp_status,
                "overall_status": status_val,
                "confidence": ocr_out.get("overall_confidence", 85.0),
                "quality_score": q_metrics.get("quality_score", 80),
                "violations_count": len([r for r in comp_res.get("results", []) if r.get("status") == "FAIL"]),
                "processing_time_sec": round(t_proc, 2),
                "original_url": f"/results/{orig_fname}",
                "processed_url": f"/results/{proc_fname}"
            })

        except Exception as e:
            summary_counts["cannot_verify"] += 1
            results.append({
                "package_index": idx + 1,
                "filename": f.filename,
                "product_name": f.filename,
                "status": "🟡 CANNOT VERIFY",
                "overall_status": "ERROR",
                "confidence": 0.0,
                "quality_score": 0,
                "violations_count": 0,
                "processing_time_sec": 0.0,
                "error": str(e)
            })

    total_duration = round((datetime.now(timezone.utc) - batch_start).total_seconds(), 2)

    return {
        "batch_id": f"BATCH-{int(batch_start.timestamp())}",
        "timestamp": batch_start.isoformat(),
        "total_packages": summary_counts["total"],
        "followed_count": summary_counts["followed"],
        "against_rule_count": summary_counts["against_rule"],
        "cannot_verify_count": summary_counts["cannot_verify"],
        "compliance_rate_percent": round((summary_counts["followed"] / max(summary_counts["total"], 1)) * 100.0, 1),
        "total_processing_time_sec": total_duration,
        "average_time_per_package_sec": round(total_duration / max(summary_counts["total"], 1), 2),
        "packages": results
    }

def process_single_image_worker(idx: int, img_bytes: bytes, uuid_str: str) -> dict:
    from datetime import datetime, timezone
    from app.ocr.preprocessing import OpenCVPreprocessor
    from app.ocr.ocr_engine import decode_barcode
    from app.ocr.yolo_detector import YoloRegionDetector
    from app.ocr.ocr_service import PaddleOCRService
    from app.ocr.declaration_extractor import DeclarationExtractor
    import cv2
    import os
    RESULTS_DIR = os.path.join(os.path.dirname(__file__), "../../results")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    t0_pre = datetime.now(timezone.utc)
    try:
        img_cv, img_info = OpenCVPreprocessor.validate_and_load_image(img_bytes)
    except ValueError as ve:
        raise ValueError(str(ve))

    quality_metrics = OpenCVPreprocessor.assess_image_quality(img_cv)
    quality_score = float(quality_metrics.get("quality_score", 0.0))
    
    barcode_res = decode_barcode(img_cv)
    barcode_info = {}
    if barcode_res.get("detected") and barcode_res.get("value"):
        barcode_info = {"detected": True, "type": barcode_res.get("type", "BARCODE"), "data": str(barcode_res["value"]), "value": str(barcode_res["value"]), "bbox": barcode_res.get("bbox"), "confidence": 100.0, "source": "pyzbar"}
    else:
        barcode_info = OpenCVPreprocessor.detect_and_decode_barcode_or_qr(img_cv)
        
    orig_fname = f"orig_{idx}_INS-{uuid_str}.png"
    proc_fname = f"proc_{idx}_INS-{uuid_str}.png"
    orig_path = os.path.join(RESULTS_DIR, orig_fname)
    proc_path = os.path.join(RESULTS_DIR, proc_fname)

    cv2.imwrite(orig_path, img_cv)
    variants = OpenCVPreprocessor.generate_ocr_variants(img_cv)
    enhanced_img = OpenCVPreprocessor.generate_4k_enhanced_image(img_cv)
    cv2.imwrite(proc_path, enhanced_img)

    original_url = f"/results/{orig_fname}"
    processed_url = f"/results/{proc_fname}"
    
    pre_ms = (datetime.now(timezone.utc) - t0_pre).total_seconds() * 1000.0

    statutory_crops = []
    try:
        yolo_detector = YoloRegionDetector.get_instance()
        statutory_crops = yolo_detector.get_statutory_crops(img_cv)
    except Exception:
        pass

    t0_ocr = datetime.now(timezone.utc)
    ocr_res = PaddleOCRService.extract_multi_pass_ocr(img_cv, variants, statutory_crops=statutory_crops)
    raw_text = ocr_res.get("full_text", "")
    merged_ocr_results = ocr_res.get("detections", [])
    overall_conf = float(ocr_res.get("overall_confidence", 85.0))
    ocr_ms = (datetime.now(timezone.utc) - t0_ocr).total_seconds() * 1000.0

    t0_decl = datetime.now(timezone.utc)
    extracted_decls = DeclarationExtractor.parse_declarations(raw_text, merged_ocr_results)
    
    b_val = barcode_info.get("value") or barcode_info.get("data")
    if barcode_info.get("detected") and b_val:
        extracted_decls["barcode"] = {"value": str(b_val), "bbox": barcode_info.get("bbox"), "confidence": 100.0, "detected": True, "type": barcode_info.get("type", "BARCODE")}
        
    decl_ms = (datetime.now(timezone.utc) - t0_decl).total_seconds() * 1000.0
    
    pdp_info = OpenCVPreprocessor.detect_package_and_pdp(img_cv)
    
    return {
        "idx": idx,
        "img_cv": img_cv,
        "quality_score": quality_score,
        "barcode_info": barcode_info,
        "original_url": original_url,
        "processed_url": processed_url,
        "statutory_crops": statutory_crops,
        "raw_text": raw_text,
        "merged_ocr_results": merged_ocr_results,
        "overall_conf": overall_conf,
        "extracted_decls": extracted_decls,
        "pre_ms": pre_ms,
        "ocr_ms": ocr_ms,
        "decl_ms": decl_ms,
        "pdp_info": pdp_info
    }
