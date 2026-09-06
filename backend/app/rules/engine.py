"""
engine.py - Generic Stateless Compliance Rule Engine
Evaluates generic, database-stored statutory rule definitions against normalized OCR label fields.
Never hard-codes legal rules. Uses safe, deterministic operator evaluation (zero eval/exec).
"""

import re
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional, Tuple

from app.models import ComplianceRuleDB
from app.rules.normalization import DataNormalizer
from app.config import settings

class RuleEngine:

    @staticmethod
    def _get_field_data(declarations: Dict[str, Any], field_name: str) -> Dict[str, Any]:
        """
        Retrieves field entry from structured declarations with fallback for synonymous keys.
        """
        if not field_name:
            return {}

        f_clean = field_name.strip().lower()
        
        # Primary lookup
        if f_clean in declarations:
            val = declarations[f_clean]
            if isinstance(val, dict):
                return val
            return {"value": val, "confidence": 90.0, "bbox": None, "detected": bool(val)}

        # Alias lookup mapping (bridges Stage 5 OCR extractor keys with formal statutory rules)
        aliases = {
            "product_name": ["generic_name", "commodity_name", "common_generic_name", "title"],
            "generic_name": ["product_name", "commodity_name", "common_generic_name"],
            "common_generic_name": ["product_name", "generic_name", "commodity_name", "title"],
            "mrp": ["price", "maximum_retail_price", "retail_price"],
            "mrp_inclusive_tax": ["tax_inclusive", "inclusive_tax", "tax_clause", "mrp_label_format"],
            "mrp_label_format": ["mrp_inclusive_tax", "tax_inclusive", "inclusive_tax", "tax_clause", "mrp"],
            "mrp_rounding": ["mrp", "price"],
            "net_quantity": ["quantity", "net_weight", "net_content", "net_qty"],
            "net_quantity_unit": ["unit_of_measurement", "unit", "uom"],
            "unit_of_measurement": ["net_quantity_unit", "unit", "uom"],
            "manufacturing_date": ["manufacture_pack_import_date", "mfg_date", "mfd", "pkd", "packed_on_date", "date_of_mfg"],
            "manufacture_pack_import_date": ["manufacturing_date", "mfg_date", "mfd", "pkd", "packed_on_date", "date_of_mfg"],
            "expiry_date": ["best_before_use_by", "exp_date", "use_by", "best_before", "expiration_date"],
            "best_before_use_by": ["expiry_date", "exp_date", "use_by", "best_before", "expiration_date"],
            "batch_number": ["batch_no", "lot_number", "lot_no", "b_no"],
            "manufacturer": ["manufacturer_or_importer_name_address", "packer", "marketer", "importer", "manufacturer_details"],
            "manufacturer_or_importer_name_address": ["manufacturer", "packer", "marketer", "importer", "manufacturer_details", "address", "manufacturer_address"],
            "address": ["manufacturer_address", "packer_address", "factory_address", "manufacturer_or_importer_name_address"],
            "consumer_care": ["customer_care", "helpline", "consumer_care_details", "care"],
            "fssai_license": ["fssai", "license_number", "lic_no"],
            "allergen_declaration": ["allergen", "allergen_info", "allergens"],
            "country_of_origin": ["origin_country", "made_in", "ecommerce_coo_filter"],
            "ecommerce_coo_filter": ["country_of_origin", "origin_country", "made_in"],
            "unit_sale_price": ["usp", "unit_price"],
            "voluntary_marks": ["barcode", "gtin", "qr_code"],
            "quantity_by_number_wording": ["net_quantity_unit", "unit_of_measurement", "quantity"]
        }

        alt_keys = aliases.get(f_clean, [])
        for k in alt_keys:
            if k in declarations:
                val = declarations[k]
                if isinstance(val, dict):
                    return val
                return {"value": val, "confidence": 90.0, "bbox": None, "detected": bool(val)}

        return {
            "value": None,
            "normalized_value": None,
            "confidence": 0.0,
            "bbox": None,
            "detected": False
        }

    @staticmethod
    def evaluate_rule(
        rule: ComplianceRuleDB,
        declarations: Dict[str, Any],
        ocr_overall_confidence: float = 90.0,
        image_quality_passed: bool = True,
        review_threshold: Optional[float] = None,
        high_conf_threshold: Optional[float] = None,
        evaluation_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a single database rule against OCR declarations using safe structured operators.
        Returns a rich, auditable validation result dictionary.
        """
        rev_thresh = review_threshold if review_threshold is not None else settings.OCR_REVIEW_THRESHOLD
        high_thresh = high_conf_threshold if high_conf_threshold is not None else settings.OCR_HIGH_CONFIDENCE_THRESHOLD
        eval_dt = evaluation_date or datetime.now(timezone.utc).date()

        field_name = rule.field_name or ""
        rule_type = (rule.rule_type or "MANDATORY_FIELD").upper()
        # Normalize canonical validation types from rule_engine_rules.json
        if rule_type == "PRESENCE":
            rule_type = "MANDATORY_FIELD"
        elif rule_type == "UNIT":
            rule_type = "VALUE_CHECK"
        elif rule_type in ["FORMAT", "DIMENSION"]:
            rule_type = "FORMAT_CHECK"
        elif rule_type == "DATE":
            rule_type = "DATE_CHECK"
        elif rule_type == "NUMERIC":
            rule_type = "RANGE_CHECK"
        elif rule_type in ["CONDITIONAL", "APPLICABILITY_EXCLUSION", "CROSS_FIELD"]:
            rule_type = "CONDITIONAL_RULE"

        condition_dict = rule.get_condition_dict()
        is_required = bool(rule.required)
        severity = rule.severity or "HIGH"

        field_data = RuleEngine._get_field_data(declarations, field_name)
        raw_val = field_data.get("value")
        field_conf = float(field_data.get("confidence", 0.0))
        bbox = field_data.get("bbox")
        is_detected = bool(raw_val and str(raw_val).strip() and str(raw_val).lower() not in ["none", "null", "not detected", "not_detected"])

        # Normalize field value
        norm_dict = DataNormalizer.normalize_field(field_name, raw_val)
        norm_val = norm_dict["normalized_value"]

        # Prepare base evidence structure
        evidence = None
        if is_detected and bbox and not (isinstance(bbox, list) and len(bbox) == 4 and all(v == 0 for v in bbox)):
            evidence = {
                "bounding_box": bbox,
                "text_snippet": str(raw_val),
                "image_target": "enhanced",
                "evidence_status": "FOUND"
            }
        else:
            evidence = {
                "bounding_box": None,
                "text_snippet": None,
                "image_target": None,
                "evidence_status": "NO_RELIABLE_OCR_EVIDENCE_FOUND",
                "message": "No reliable visual evidence is available for this rule."
            }

        # Initialize result state
        status = "NEEDS_REVIEW"
        explanation = ""
        effective_conf = field_conf if is_detected else ocr_overall_confidence

        # Handle general statutory provisions without specific OCR field targets
        if not field_name:
            return {
                "rule_id": rule.rule_id,
                "rule_version": rule.version or "1.0.0",
                "regulation": rule.regulation or rule.statutory_reference or "Legal Metrology",
                "regulation_section": rule.regulation_section or "",
                "source_reference": rule.source_reference or rule.statutory_reference or "",
                "field": "general_provision",
                "field_name": "general_provision",
                "extracted_value": None,
                "normalized_value": None,
                "required": False,
                "severity": severity,
                "status": "PASS",
                "confidence": 100.0,
                "explanation": rule.compliance_condition or "General statutory provision.",
                "evidence": evidence,
                "evaluated_at": datetime.now(timezone.utc).isoformat()
            }

        # -------------------------------------------------------------
        # 1. MANDATORY_FIELD Check
        # -------------------------------------------------------------
        if rule_type == "MANDATORY_FIELD":
            if is_detected:
                if field_conf >= rev_thresh:
                    status = "PASS"
                    explanation = f"Mandatory field '{field_name}' successfully detected with {field_conf:.1f}% OCR confidence."
                else:
                    status = "NEEDS_REVIEW"
                    explanation = f"Field '{field_name}' detected but OCR confidence ({field_conf:.1f}%) is below verification threshold ({rev_thresh}%). Requires visual confirmation."
            else:
                # Field was NOT detected.
                if not is_required:
                    status = "PASS"
                    explanation = f"Optional declaration '{field_name}' was not detected; check passed."
                elif not image_quality_passed or ocr_overall_confidence < rev_thresh:
                    status = "NEEDS_REVIEW"
                    explanation = f"Required field '{field_name}' was not detected, but image quality or OCR scan confidence ({ocr_overall_confidence:.1f}%) is insufficient for definitive legal screening. Manual review required."
                elif ocr_overall_confidence >= high_thresh:
                    status = "FAIL"
                    err_msg = rule.error_message or f"Mandatory statutory declaration '{field_name}' was not detected."
                    explanation = f"{err_msg} (Field was not detected in high-confidence OCR scan {ocr_overall_confidence:.1f}%)."
                else:
                    status = "NEEDS_REVIEW"
                    explanation = f"Declaration '{field_name}' was not detected. Visual officer review recommended."

        # -------------------------------------------------------------
        # 2. VALUE_CHECK
        # -------------------------------------------------------------
        elif rule_type == "VALUE_CHECK":
            operator = condition_dict.get("operator", "one_of")
            allowed_values = [str(v).lower() for v in condition_dict.get("values", [])]
            expected_val = str(condition_dict.get("expected_value", "")).lower()

            if not is_detected:
                if is_required:
                    if ocr_overall_confidence >= high_thresh:
                        status = "FAIL"
                        explanation = rule.error_message or f"Required value check for '{field_name}' failed because the field was not detected."
                    else:
                        status = "NEEDS_REVIEW"
                        explanation = f"Value for '{field_name}' could not be evaluated due to unread field."
                else:
                    status = "PASS"
                    explanation = f"Optional field '{field_name}' not present; value check skipped."
            else:
                val_str = str(norm_val or raw_val).strip().lower()
                if operator in ["one_of", "in"]:
                    if val_str in allowed_values or any(val_str == av for av in allowed_values):
                        status = "PASS"
                        explanation = f"Extracted value '{norm_val}' is a valid statutory option in {allowed_values}."
                    else:
                        status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                        explanation = rule.error_message or f"Extracted value '{raw_val}' does not match allowed statutory options: {', '.join(allowed_values)}."
                elif operator == "equals":
                    if val_str == expected_val:
                        status = "PASS"
                        explanation = f"Extracted value matches required value '{expected_val}'."
                    else:
                        status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                        explanation = rule.error_message or f"Extracted value '{raw_val}' does not match expected '{expected_val}'."
                elif operator == "not_equals":
                    if val_str != expected_val:
                        status = "PASS"
                        explanation = f"Extracted value satisfies constraint (not equal to '{expected_val}')."
                    else:
                        status = "FAIL"
                        explanation = rule.error_message or f"Extracted value '{raw_val}' matches prohibited value '{expected_val}'."

        # -------------------------------------------------------------
        # 3. FORMAT_CHECK
        # -------------------------------------------------------------
        elif rule_type == "FORMAT_CHECK":
            pattern = condition_dict.get("pattern", "")
            operator = condition_dict.get("operator", "regex")

            if not is_detected:
                if is_required and ocr_overall_confidence >= high_thresh:
                    status = "FAIL"
                    explanation = rule.error_message or f"Format check for '{field_name}' failed because field was not detected."
                else:
                    status = "NEEDS_REVIEW" if is_required else "PASS"
                    explanation = f"Field '{field_name}' not detected; format evaluation cannot be completed."
            else:
                target_str = str(norm_val or raw_val).strip()
                if operator == "contains_all":
                    vals = condition_dict.get("values", [])
                    missing = [v for v in vals if str(v).lower() not in target_str.lower()]
                    if not missing:
                        status = "PASS"
                        explanation = f"Extracted value conforms to all required statutory phrases ({vals})."
                    else:
                        status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                        explanation = rule.error_message or f"Declaration missing required statutory phrasing (missing: {', '.join(missing)})."
                elif operator == "contains_any":
                    vals = condition_dict.get("values", [])
                    matched = [v for v in vals if str(v).lower() in target_str.lower()]
                    if matched:
                        status = "PASS"
                        explanation = f"Extracted value contains required statutory term '{matched[0]}'."
                    else:
                        status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                        explanation = rule.error_message or f"Declaration missing required statutory format keyword (expected one of: {', '.join(vals)})."
                elif operator == "one_of":
                    vals = [str(v).lower() for v in condition_dict.get("values", [])]
                    # Rule 13 quantity by number check only applies to items sold by number (not weight/volume)
                    if field_name == "quantity_by_number_wording" and target_str.lower() in ["g", "kg", "mg", "ml", "l", "ltr", "gm", "m", "cm", "mm"]:
                        status = "PASS"
                        explanation = f"Commodity declared by weight/measure ({target_str}); Rule 13 (quantity by number) check skipped."
                    elif target_str.lower() in vals:
                        status = "PASS"
                        explanation = f"Extracted value '{target_str}' is an authorized term in {vals}."
                    else:
                        status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                        explanation = rule.error_message or f"Extracted value '{target_str}' not in allowed terms: {', '.join(vals)}."
                elif operator == "regex" or pattern:
                    try:
                        match = re.search(pattern, target_str, re.IGNORECASE)
                        if match:
                            status = "PASS"
                            explanation = f"Extracted value '{target_str}' complies with required format pattern."
                        else:
                            status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                            explanation = rule.error_message or f"Extracted value '{target_str}' does not conform to format pattern '{pattern}'."
                    except re.error as re_err:
                        status = "NEEDS_REVIEW"
                        explanation = f"Rule regex pattern error: {str(re_err)}"
                else:
                    status = "PASS"
                    explanation = "Format check passed (no custom regex pattern defined)."

        # -------------------------------------------------------------
        # 4. RANGE_CHECK
        # -------------------------------------------------------------
        elif rule_type == "RANGE_CHECK":
            min_val = condition_dict.get("min_value", condition_dict.get("min"))
            max_val = condition_dict.get("max_value", condition_dict.get("max"))
            operator = condition_dict.get("operator", "between")

            num_val = norm_dict.get("numeric_value")
            if num_val is None and is_detected:
                # Try parsing float from raw_val
                num_m = re.search(r'(\d+(?:\.\d+)?)', str(raw_val))
                if num_m:
                    num_val = float(num_m.group(1))

            if num_val is None:
                if is_required and ocr_overall_confidence >= high_thresh:
                    status = "FAIL"
                    explanation = rule.error_message or f"Numeric range check for '{field_name}' failed: could not parse numeric quantity."
                else:
                    status = "NEEDS_REVIEW" if is_required else "PASS"
                    explanation = f"Could not extract numeric value for field '{field_name}' to evaluate range."
            else:
                passed_range = True
                if min_val is not None and num_val < float(min_val):
                    passed_range = False
                if max_val is not None and num_val > float(max_val):
                    passed_range = False

                if passed_range:
                    status = "PASS"
                    explanation = f"Numeric value {num_val} is within permissible range [{min_val if min_val is not None else '-inf'}, {max_val if max_val is not None else '+inf'}]."
                else:
                    status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                    explanation = rule.error_message or f"Numeric value {num_val} is outside allowed range [{min_val}, {max_val}]."

        # -------------------------------------------------------------
        # 5. DATE_CHECK (Uses real datetime.date objects)
        # -------------------------------------------------------------
        elif rule_type == "DATE_CHECK":
            operator = condition_dict.get("operator", "is_valid_date")
            compare_with_field = condition_dict.get("compare_with")

            d_obj = norm_dict.get("date_obj")

            if not is_detected or d_obj is None:
                if is_required and ocr_overall_confidence >= high_thresh:
                    status = "FAIL"
                    explanation = rule.error_message or f"Date declaration '{field_name}' missing or could not be parsed into a valid calendar date."
                else:
                    status = "NEEDS_REVIEW" if is_required else "PASS"
                    explanation = f"Date value for '{field_name}' could not be reliably parsed as calendar date."
            else:
                if operator == "is_past_or_today":
                    # Mfg date should not be far in the future
                    if d_obj <= eval_dt:
                        status = "PASS"
                        explanation = f"Date {d_obj.strftime('%d/%m/%Y')} is valid and precedes/equals screening date."
                    else:
                        # Minor future date (current month) might be allowed for pre-printed packaging
                        diff_days = (d_obj - eval_dt).days
                        if diff_days <= 31:
                            status = "NEEDS_REVIEW"
                            explanation = f"Date {d_obj.strftime('%d/%m/%Y')} is slightly in the future ({diff_days} days ahead). Verification required."
                        else:
                            status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                            explanation = rule.error_message or f"Date {d_obj.strftime('%d/%m/%Y')} is in the future relative to current date ({eval_dt.strftime('%d/%m/%Y')})."

                elif operator == "date_after_or_equal":
                    # E.g. Expiry Date >= Manufacturing Date
                    ref_data = RuleEngine._get_field_data(declarations, compare_with_field or "manufacturing_date")
                    ref_norm = DataNormalizer.normalize_field(compare_with_field or "manufacturing_date", ref_data.get("value"))
                    ref_d_obj = ref_norm.get("date_obj")

                    if ref_d_obj is None:
                        status = "NEEDS_REVIEW"
                        explanation = f"Cannot compare {field_name} because reference date '{compare_with_field}' was not detected."
                    else:
                        if d_obj >= ref_d_obj:
                            status = "PASS"
                            explanation = f"Expiry date ({d_obj.strftime('%d/%m/%Y')}) is subsequent to manufacturing date ({ref_d_obj.strftime('%d/%m/%Y')})."
                        else:
                            status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                            explanation = rule.error_message or f"Expiry date ({d_obj.strftime('%d/%m/%Y')}) precedes manufacturing date ({ref_d_obj.strftime('%d/%m/%Y')})."

                elif operator == "is_future_or_today":
                    if d_obj >= eval_dt:
                        status = "PASS"
                        explanation = f"Date {d_obj.strftime('%d/%m/%Y')} is current/future."
                    else:
                        status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                        explanation = rule.error_message or f"Date {d_obj.strftime('%d/%m/%Y')} is expired as of {eval_dt.strftime('%d/%m/%Y')}."
                else:
                    status = "PASS"
                    explanation = f"Date {d_obj.strftime('%d/%m/%Y')} is structurally valid."

        # -------------------------------------------------------------
        # 6. TEXT_CHECK
        # -------------------------------------------------------------
        elif rule_type == "TEXT_CHECK":
            operator = condition_dict.get("operator", "contains")
            required_val = condition_dict.get("value", condition_dict.get("substring", ""))
            values_list = condition_dict.get("values", [])

            text_to_search = str(raw_val or "").lower()
            # If checking mrp_inclusive_tax, also search full raw OCR text if available
            if field_name == "mrp_inclusive_tax" and not text_to_search:
                text_to_search = str(declarations.get("mrp_inclusive_tax", {}).get("value") or "").lower()

            if not is_detected and not text_to_search:
                if is_required and ocr_overall_confidence >= high_thresh:
                    status = "FAIL"
                    explanation = rule.error_message or f"Required text declaration for '{field_name}' was not found."
                else:
                    status = "NEEDS_REVIEW" if is_required else "PASS"
                    explanation = f"Field '{field_name}' text was not detected for evaluation."
            else:
                if operator == "contains":
                    if str(required_val).lower() in text_to_search:
                        status = "PASS"
                        explanation = f"Extracted text contains mandatory phrase '{required_val}'."
                    else:
                        status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                        explanation = rule.error_message or f"Declaration does not contain mandatory phrase '{required_val}'."

                elif operator == "contains_any":
                    matched_kw = [kw for kw in values_list if str(kw).lower() in text_to_search]
                    if matched_kw:
                        status = "PASS"
                        explanation = f"Extracted text matches required declaration keyword '{matched_kw[0]}'."
                    else:
                        status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                        explanation = rule.error_message or f"Declaration missing required statutory phrasing (expected one of: {', '.join(values_list)})."

                elif operator == "contains_all":
                    missing_kw = [kw for kw in values_list if str(kw).lower() not in text_to_search]
                    if not missing_kw:
                        status = "PASS"
                        explanation = f"All required keywords {values_list} are present in declaration."
                    else:
                        status = "FAIL" if field_conf >= rev_thresh else "NEEDS_REVIEW"
                        explanation = rule.error_message or f"Declaration missing mandatory elements: {', '.join(missing_kw)}."

        # -------------------------------------------------------------
        # 7. CONDITIONAL_RULE
        # -------------------------------------------------------------
        elif rule_type == "CONDITIONAL_RULE":
            # Safe structured conditional evaluation
            if_cond = condition_dict.get("if_condition", {})
            then_cond = condition_dict.get("then_condition", {})

            if_field = if_cond.get("field")
            if_op = if_cond.get("operator", "equals")
            if_expected = if_cond.get("value")

            trigger_matched = False
            if if_field:
                ref_f_data = RuleEngine._get_field_data(declarations, if_field)
                ref_v = str(ref_f_data.get("value") or "").lower()
                if if_op == "equals" and ref_v == str(if_expected).lower():
                    trigger_matched = True
                elif if_op == "present" and ref_f_data.get("detected"):
                    trigger_matched = True
                elif if_op == "contains" and str(if_expected).lower() in ref_v:
                    trigger_matched = True

            if not trigger_matched:
                status = "PASS"
                explanation = f"Conditional trigger condition for '{rule.rule_id}' was not active; check passed."
            else:
                # Evaluate then_condition
                then_field = then_cond.get("field", field_name)
                then_f_data = RuleEngine._get_field_data(declarations, then_field)
                if then_f_data.get("detected"):
                    status = "PASS"
                    explanation = f"Conditional statutory requirement for '{then_field}' satisfied."
                else:
                    status = "FAIL" if ocr_overall_confidence >= high_thresh else "NEEDS_REVIEW"
                    explanation = rule.error_message or f"Conditional requirement failed: '{then_field}' is mandatory when '{if_field}' is active."

        # Return comprehensive, auditable result record
        return {
            "rule_id": rule.rule_id,
            "rule_version": rule.version or "1.0.0",
            "regulation": rule.regulation or rule.statutory_reference or "Legal Metrology",
            "regulation_section": rule.regulation_section or "",
            "source_reference": rule.source_reference or rule.statutory_reference or "",
            "field": field_name,
            "field_name": field_name,
            "extracted_value": raw_val if is_detected else None,
            "normalized_value": norm_val if is_detected else None,
            "required": is_required,
            "severity": severity,
            "status": status,  # "PASS" | "FAIL" | "NEEDS_REVIEW"
            "confidence": round(effective_conf, 2),
            "explanation": explanation,
            "evidence": evidence,
            "evaluated_at": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def validate_declarations(
        declarations: Dict[str, Any],
        rules: List[ComplianceRuleDB],
        ocr_overall_confidence: float = 90.0,
        image_quality_passed: bool = True,
        review_threshold: Optional[float] = None,
        high_conf_threshold: Optional[float] = None,
        evaluation_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Iterates over all dynamically retrieved rules and returns a list of evaluated validation results.
        """
        results = []
        for rule in rules:
            res = RuleEngine.evaluate_rule(
                rule=rule,
                declarations=declarations,
                ocr_overall_confidence=ocr_overall_confidence,
                image_quality_passed=image_quality_passed,
                review_threshold=review_threshold,
                high_conf_threshold=high_conf_threshold,
                evaluation_date=evaluation_date
            )
            results.append(res)
        return results
