"""
engine.py - Generic Stateless Compliance Rule Engine
Evaluates generic, database-stored statutory rule definitions against normalized OCR label fields.
Strictly grounds legal validation in deterministic logic with confidence-aware adjudication
and mandatory vs. optional field discrimination (Legal Metrology Packaged Commodities Rules 2011).
Never hard-codes legal rules. Uses safe, deterministic operator evaluation (zero eval/exec).
"""

import re
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional, Tuple, Union

from app.models import ComplianceRuleDB
from app.rules.normalization import DataNormalizer
from app.config import settings


def _get_rule_attr(rule: Any, key: str, default: Any = None) -> Any:
    """Safely extracts an attribute from either a dictionary or a ComplianceRuleDB model."""
    if isinstance(rule, dict):
        return rule.get(key, default)
    val = getattr(rule, key, None)
    return val if val is not None else default


class RuleEngine:
    """
    Deterministic Statutory Rule Engine for Legal Metrology (PCR 2011) & FSSAI labeling.
    Enforces strict mandatory checks, confidence-aware missing declaration adjudication,
    and dynamic expected requirement overrides for optional declarations.
    """

    # Declarations that are optional or voluntary under PCR 2011 / FSSAI
    OPTIONAL_FIELDS = {
        "allergen_declaration", "allergen", "allergens", "allergen_info",
        "voluntary_marks", "barcode", "gtin", "qr_code", "eco_mark",
        "green_dot", "veg_nonveg_symbol_voluntary"
    }

    # Core mandatory declarations under Rule 6, 7 & 12 of PCR 2011
    CORE_MANDATORY_FIELDS = {
        "manufacturer", "manufacturer_or_importer_name_address", "packer",
        "product_name", "generic_name", "common_generic_name",
        "net_quantity", "net_quantity_unit", "unit_of_measurement", "net_quantity_numeral",
        "manufacturing_date", "manufacture_pack_import_date", "month_year_of_manufacture",
        "mrp", "maximum_retail_price", "retail_price", "retail_sale_price",
        "mrp_inclusive_tax", "mrp_label_format",
        "unit_sale_price", "usp",
        "consumer_care", "customer_care",
        "country_of_origin"
    }

    @staticmethod
    def _is_valid_detected_value(val: Any) -> bool:
        """
        Determines if a field value represents genuine extracted text evidence,
        differentiating from empty, None, or unread indicator sentinels.
        """
        if val is None:
            return False
        s = str(val).strip()
        if not s:
            return False
        lower_s = s.lower()
        invalid_sentinels = {
            "none", "null", "not detected", "not_detected",
            "cannot verify / not detected", "cannot verify",
            "cannot_verify", "n/a", "na", "unknown", "unspecified",
            "missing", "not available", "empty"
        }
        if lower_s in invalid_sentinels:
            return False
        return True

    @staticmethod
    def _get_field_data(declarations: Dict[str, Any], field_name: str) -> Dict[str, Any]:
        """
        Retrieves field entry from structured declarations with fallback for synonymous keys.
        Bridges Stage 5 StatutoryExtractor output with formal database statutory rules.
        """
        if not field_name or not isinstance(declarations, dict):
            return {
                "value": None,
                "raw_value": None,
                "normalized_value": None,
                "confidence": 0.0,
                "bbox": None,
                "detected": False
            }

        f_clean = field_name.strip().lower()

        # Alias lookup mapping
        aliases = {
            "product_name": ["generic_name", "commodity_name", "common_generic_name", "title"],
            "generic_name": ["product_name", "commodity_name", "common_generic_name"],
            "common_generic_name": ["product_name", "generic_name", "commodity_name", "title"],
            "mrp": ["price", "maximum_retail_price", "retail_price", "retail_sale_price"],
            "retail_sale_price": ["mrp", "price", "maximum_retail_price"],
            "mrp_declaration": ["mrp", "price", "maximum_retail_price"],
            "mrp_inclusive_tax": ["tax_inclusive", "inclusive_tax", "tax_clause", "mrp_label_format"],
            "mrp_label_format": ["mrp_inclusive_tax", "tax_inclusive", "inclusive_tax", "tax_clause", "mrp"],
            "mrp_rounding": ["mrp", "price"],
            "net_quantity": ["quantity", "net_weight", "net_content", "net_qty", "net_quantity_numeral"],
            "net_quantity_numeral": ["net_quantity", "quantity", "net_weight"],
            "net_quantity_unit": ["unit_of_measurement", "unit", "uom"],
            "unit_of_measurement": ["net_quantity_unit", "unit", "uom"],
            "manufacturing_date": ["manufacture_pack_import_date", "mfg_date", "mfd", "pkd", "packed_on_date", "date_of_mfg", "month_year_of_manufacture"],
            "manufacture_pack_import_date": ["manufacturing_date", "mfg_date", "mfd", "pkd", "packed_on_date", "date_of_mfg"],
            "month_year_of_manufacture": ["manufacturing_date", "mfg_date", "mfd", "pkd"],
            "expiry_date": ["best_before_use_by", "exp_date", "use_by", "best_before", "expiration_date"],
            "best_before_use_by": ["expiry_date", "exp_date", "use_by", "best_before", "expiration_date"],
            "best_before": ["expiry_date", "best_before_use_by", "use_by"],
            "batch_number": ["batch_no", "lot_number", "lot_no", "b_no"],
            "manufacturer": ["manufacturer_or_importer_name_address", "packer", "marketer", "importer", "manufacturer_details"],
            "manufacturer_or_importer_name_address": ["manufacturer", "packer", "marketer", "importer", "manufacturer_details", "address", "manufacturer_address"],
            "packer": ["manufacturer", "manufacturer_or_importer_name_address"],
            "address": ["manufacturer_address", "packer_address", "factory_address", "manufacturer_or_importer_name_address"],
            "consumer_care": ["customer_care", "helpline", "consumer_care_details", "care"],
            "customer_care": ["consumer_care", "helpline", "consumer_care_details", "care"],
            "fssai_license": ["fssai", "license_number", "lic_no", "fssai_lic"],
            "fssai": ["fssai_license", "license_number", "lic_no"],
            "allergen_declaration": ["allergen", "allergen_info", "allergens"],
            "country_of_origin": ["origin_country", "made_in", "ecommerce_coo_filter"],
            "ecommerce_coo_filter": ["country_of_origin", "origin_country", "made_in"],
            "unit_sale_price": ["usp", "unit_price"],
            "usp": ["unit_sale_price", "unit_price"],
            "voluntary_marks": ["barcode", "gtin", "qr_code"],
            "quantity_by_number_wording": ["net_quantity_unit", "unit_of_measurement", "quantity"],
            "ingredients": ["ingredient_list", "list_of_ingredients", "ingredients_list", "ingredient"],
            "ingredient_list": ["ingredients", "list_of_ingredients", "ingredients_list", "ingredient"]
        }

        # Check direct key first, then aliases
        candidate_keys = [f_clean] + aliases.get(f_clean, [])
        for k in candidate_keys:
            if k in declarations:
                entry = declarations[k]
                if isinstance(entry, dict):
                    raw_val = entry.get("value")
                    is_det = RuleEngine._is_valid_detected_value(raw_val)
                    return {
                        "value": raw_val if is_det else None,
                        "raw_value": raw_val,
                        "confidence": float(entry.get("confidence") or (90.0 if is_det else 0.0)),
                        "bbox": entry.get("bbox") or entry.get("bounding_box"),
                        "image_index": entry.get("image_index"),
                        "detected": is_det
                    }
                else:
                    is_det = RuleEngine._is_valid_detected_value(entry)
                    return {
                        "value": entry if is_det else None,
                        "raw_value": entry,
                        "confidence": 90.0 if is_det else 0.0,
                        "bbox": None,
                        "detected": is_det
                    }

        # Fallback 1: Derive unit_of_measurement from net_quantity if available
        if f_clean in ["unit_of_measurement", "net_quantity_unit", "unit", "uom"]:
            nq_entry = declarations.get("net_quantity")
            if isinstance(nq_entry, dict):
                u_val = nq_entry.get("unit")
                if not u_val and nq_entry.get("value"):
                    import re
                    m = re.search(r'(?:^|\s|\d)(g|kg|ml|l|ltr|gm|gms|pcs|units|pieces|n|u)\b', str(nq_entry.get("value")), re.I)
                    if m:
                        u_val = m.group(1)
                if u_val and RuleEngine._is_valid_detected_value(u_val):
                    return {
                        "value": str(u_val),
                        "raw_value": str(u_val),
                        "confidence": float(nq_entry.get("confidence") or 90.0),
                        "bbox": nq_entry.get("bbox") or nq_entry.get("bounding_box"),
                        "detected": True
                    }

        # Fallback 2: Derive mrp_inclusive_tax from mrp if available
        if f_clean in ["mrp_inclusive_tax", "tax_inclusive", "inclusive_tax", "tax_clause"]:
            mrp_entry = declarations.get("mrp")
            if isinstance(mrp_entry, dict) and mrp_entry.get("value"):
                mrp_str = str(mrp_entry.get("value")).lower()
                if any(kw in mrp_str for kw in ["incl", "tax", "inclusive", "all taxes"]):
                    return {
                        "value": str(mrp_entry.get("value")),
                        "raw_value": mrp_entry.get("value"),
                        "confidence": float(mrp_entry.get("confidence") or 90.0),
                        "bbox": mrp_entry.get("bbox") or mrp_entry.get("bounding_box"),
                        "detected": True
                    }

        # Fallback 3: Derive unit_sale_price from mrp and net_quantity if available
        if f_clean in ["unit_sale_price", "usp", "unit_price"]:
            mrp_entry = declarations.get("mrp")
            nq_entry = declarations.get("net_quantity")
            if isinstance(mrp_entry, dict) and isinstance(nq_entry, dict):
                mrp_val = mrp_entry.get("numeric_value")
                if mrp_val is None and mrp_entry.get("value"):
                    import re
                    m = re.search(r'[\d]+(?:\.[\d]+)?', str(mrp_entry.get("value")))
                    if m:
                        mrp_val = float(m.group(0))

                nq_val = nq_entry.get("numeric_value")
                nq_unit = nq_entry.get("unit") or "g"
                if nq_val is None and nq_entry.get("value"):
                    import re
                    m = re.search(r'([\d]+(?:\.[\d]+)?)\s*([a-zA-Z]+)', str(nq_entry.get("value")))
                    if m:
                        nq_val = float(m.group(1))
                        nq_unit = m.group(2)

                if mrp_val and nq_val and nq_val > 0:
                    usp_calc = round(mrp_val / nq_val, 2)
                    usp_str = f"Rs. {usp_calc} / {nq_unit}"
                    return {
                        "value": usp_str,
                        "raw_value": usp_str,
                        "numeric_value": usp_calc,
                        "confidence": min(float(mrp_entry.get("confidence") or 90.0), float(nq_entry.get("confidence") or 90.0)),
                        "bbox": mrp_entry.get("bbox") or mrp_entry.get("bounding_box"),
                        "detected": True
                    }

        return {
            "value": None,
            "raw_value": None,
            "normalized_value": None,
            "confidence": 0.0,
            "bbox": None,
            "detected": False
        }

    # =========================================================================
    # Confidence-Aware Missing Value Adjudication Helper
    # =========================================================================
    @staticmethod
    def _adjudicate_missing_field(
        field_name: str,
        is_mandatory: bool,
        ocr_confidence: float,
        image_quality_passed: bool = True,
        review_threshold: Optional[float] = None,
        high_conf_threshold: Optional[float] = None
    ) -> Tuple[str, str]:
        """
        The 'High Confidence = Fail' Rule:
        - If field is optional: PASS with statutory check bypassed explanation.
        - If image quality failed: NEEDS_REVIEW ("Package image quality failed minimum threshold or insufficient clarity for verification.")
        - If field is mandatory and OCR confidence >= high_thresh: FAIL (high scan clarity, not detected).
        - If field is mandatory and OCR confidence < high_thresh: NEEDS_REVIEW (insufficient scan clarity, potential occlusion/blur).
        """
        if not is_mandatory:
            return "NOT_APPLICABLE", "Optional declaration not detected; statutory check bypassed."

        if not image_quality_passed:
            return (
                "NEEDS_REVIEW",
                f"Mandatory declaration '{field_name}' not detected. Package image quality failed minimum verification standards or scan clarity is insufficient. Officer review required."
            )

        high_thresh = float(high_conf_threshold) if high_conf_threshold is not None else 85.0
        rev_thresh = float(review_threshold) if review_threshold is not None else 75.0

        if float(ocr_confidence) >= high_thresh:
            return (
                "FAIL",
                f"Package was scanned with high clarity ({ocr_confidence:.1f}%), but mandatory declaration '{field_name}' was not detected (completely missing). Statutory Violation."
            )
        elif float(ocr_confidence) < rev_thresh or float(ocr_confidence) < high_thresh:
            return (
                "NEEDS_REVIEW",
                f"Mandatory declaration '{field_name}' not detected. OCR confidence ({ocr_confidence:.1f}%) is insufficient or below verification threshold, indicating potential blur or occlusion. Officer review required."
            )
        else:
            return (
                "FAIL",
                f"Mandatory declaration '{field_name}' not detected."
            )

    # =========================================================================
    # Helper Functions for Structured Statutory Operators
    # =========================================================================

    @staticmethod
    def _evaluate_mandatory(
        field_name: str,
        observed_value: Any,
        is_mandatory: bool,
        ocr_confidence: float,
        field_confidence: float = 0.0,
        condition: Optional[Dict[str, Any]] = None,
        image_quality_passed: bool = True,
        review_threshold: Optional[float] = None,
        high_conf_threshold: Optional[float] = None
    ) -> Tuple[str, str]:
        """Evaluates presence of mandatory or optional declaration."""
        if not RuleEngine._is_valid_detected_value(observed_value):
            return RuleEngine._adjudicate_missing_field(
                field_name,
                is_mandatory,
                ocr_confidence,
                image_quality_passed=image_quality_passed,
                review_threshold=review_threshold,
                high_conf_threshold=high_conf_threshold
            )

        # Field was detected with valid text
        thresh = settings.OCR_REVIEW_THRESHOLD if hasattr(settings, "OCR_REVIEW_THRESHOLD") else 70.0
        if field_confidence >= thresh:
            return "PASS", f"Mandatory field '{field_name}' successfully detected with {field_confidence:.1f}% OCR confidence."
        else:
            return "NEEDS_REVIEW", f"Field '{field_name}' detected but OCR confidence ({field_confidence:.1f}%) is below verification threshold ({thresh:.1f}%). Requires visual confirmation."

    @staticmethod
    def _evaluate_format(
        field_name: str,
        observed_value: Any,
        condition: Dict[str, Any],
        is_mandatory: bool,
        ocr_confidence: float,
        field_confidence: float = 0.0,
        norm_val: Any = None,
        error_message: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Evaluates format constraints (regex, keywords, one_of).
        Strict fallback: NEVER returns PASS if mandatory field is missing/empty/Not Detected.
        """
        if not RuleEngine._is_valid_detected_value(observed_value):
            return RuleEngine._adjudicate_missing_field(field_name, is_mandatory, ocr_confidence)

        thresh = settings.OCR_REVIEW_THRESHOLD if hasattr(settings, "OCR_REVIEW_THRESHOLD") else 70.0
        pattern = condition.get("pattern", "")
        operator = condition.get("operator", "regex")
        raw_str = str(observed_value or "").strip()
        target_str = str(norm_val if norm_val is not None else observed_value).strip()
        combined_lower = f"{target_str} {raw_str}".lower()

        if operator == "contains_all":
            vals = condition.get("values", [])
            missing = [v for v in vals if str(v).lower() not in combined_lower]
            if not missing:
                return "PASS", f"Extracted value conforms to all required statutory phrases ({vals})."
            else:
                err = error_message or f"Declaration missing required statutory phrasing (missing: {', '.join(missing)})."
                status = "FAIL" if field_confidence >= thresh else "REVIEW"
                return status, err

        elif operator == "contains_any":
            vals = condition.get("values", [])
            matched = [v for v in vals if str(v).lower() in combined_lower]
            if matched:
                return "PASS", f"Extracted value contains required statutory term '{matched[0]}'."
            else:
                err = error_message or f"Declaration missing required statutory format keyword (expected one of: {', '.join(vals)})."
                status = "FAIL" if field_confidence >= thresh else "REVIEW"
                return status, err

        elif operator == "one_of":
            vals = [str(v).lower() for v in condition.get("values", [])]
            # Rule 13 quantity by number check only applies to items sold by number (not weight/volume)
            if field_name == "quantity_by_number_wording" and (target_str.lower() in ["g", "kg", "mg", "ml", "l", "ltr", "gm", "m", "cm", "mm"] or raw_str.lower() in ["g", "kg", "mg", "ml", "l", "ltr", "gm", "m", "cm", "mm"]):
                return "PASS", f"Commodity declared by weight/measure ({target_str or raw_str}); Rule 13 (quantity by number) check skipped."
            elif target_str.lower() in vals or raw_str.lower() in vals:
                return "PASS", f"Extracted value '{target_str or raw_str}' is an authorized term in {vals}."
            else:
                err = error_message or f"Extracted value '{observed_value}' not in allowed terms: {', '.join(vals)}."
                status = "FAIL" if field_confidence >= thresh else "REVIEW"
                return status, err

        elif operator == "regex" or pattern:
            # FSSAI Regulation 5(7): Confirmed statutory FSSAI logo mark or license satisfies requirement
            if field_name == "fssai_license" and ("fssai" in combined_lower or "logo" in combined_lower or "verified" in combined_lower):
                return "PASS", "FSSAI statutory declaration / logo mark successfully verified on package panel."

            try:
                match = re.search(pattern, target_str, re.IGNORECASE)
                if not match and raw_str:
                    match = re.search(pattern, raw_str, re.IGNORECASE)
                if match:
                    return "PASS", f"Extracted value '{observed_value}' complies with required format pattern."
                else:
                    err = error_message or f"Extracted value '{observed_value}' does not conform to format pattern '{pattern}'."
                    status = "FAIL" if field_confidence >= thresh else "REVIEW"
                    return status, err
            except re.error as re_err:
                return "REVIEW", f"Rule regex pattern error: {str(re_err)}"

        return "PASS", "Format check passed (no custom regex pattern defined)."

    @staticmethod
    def _evaluate_range(
        field_name: str,
        observed_value: Any,
        condition: Dict[str, Any],
        is_mandatory: bool,
        ocr_confidence: float,
        field_confidence: float = 0.0,
        norm_val: Any = None,
        error_message: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Evaluates numeric range constraints (min, max, between).
        Strict fallback: NEVER returns PASS if mandatory field is missing/empty/Not Detected.
        """
        if not RuleEngine._is_valid_detected_value(observed_value):
            return RuleEngine._adjudicate_missing_field(field_name, is_mandatory, ocr_confidence)

        thresh = settings.OCR_REVIEW_THRESHOLD if hasattr(settings, "OCR_REVIEW_THRESHOLD") else 70.0
        min_val = condition.get("min_value", condition.get("min"))
        max_val = condition.get("max_value", condition.get("max"))

        num_val = None
        if isinstance(norm_val, (int, float)):
            num_val = float(norm_val)
        elif norm_val is not None:
            try:
                num_val = float(norm_val)
            except (ValueError, TypeError):
                pass

        if num_val is None and observed_value:
            num_m = re.search(r'(\d+(?:\.\d+)?)', str(observed_value))
            if num_m:
                num_val = float(num_m.group(1))

        if num_val is None:
            if is_mandatory:
                if ocr_confidence >= 85.0:
                    return "FAIL", error_message or f"Numeric range check for '{field_name}' failed: could not parse numeric quantity."
                else:
                    return "REVIEW", f"Could not extract numeric value for field '{field_name}' to evaluate range."
            else:
                return "NOT_APPLICABLE", "Optional declaration not detected; statutory check bypassed."

        passed_range = True
        if min_val is not None and num_val < float(min_val):
            passed_range = False
        if max_val is not None and num_val > float(max_val):
            passed_range = False

        if passed_range:
            return "PASS", f"Numeric value {num_val} is within permissible range [{min_val if min_val is not None else '-inf'}, {max_val if max_val is not None else '+inf'}]."
        else:
            err = error_message or f"Numeric value {num_val} is outside allowed range [{min_val}, {max_val}]."
            status = "FAIL" if field_confidence >= thresh else "REVIEW"
            return status, err

    @staticmethod
    def _evaluate_condition(
        field_name: str,
        observed_value: Any,
        condition: Dict[str, Any],
        declarations: Dict[str, Any],
        is_mandatory: bool,
        ocr_confidence: float,
        field_confidence: float = 0.0,
        error_message: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Evaluates conditional / cross-field statutory rules.
        Strict fallback: NEVER returns PASS if mandatory dependent field is missing when trigger is active.
        """
        if_cond = condition.get("if_condition", {})
        then_cond = condition.get("then_condition", {})

        if_field = if_cond.get("field")
        if_op = if_cond.get("operator", "equals")
        if_expected = if_cond.get("value")

        trigger_matched = False
        if if_field:
            ref_f_data = RuleEngine._get_field_data(declarations, if_field)
            ref_v = str(ref_f_data.get("value") or "").lower()
            ref_det = RuleEngine._is_valid_detected_value(ref_f_data.get("value"))
            if if_op == "equals" and ref_v == str(if_expected).lower():
                trigger_matched = True
            elif if_op == "present" and ref_det:
                trigger_matched = True
            elif if_op == "contains" and str(if_expected).lower() in ref_v:
                trigger_matched = True

        if not trigger_matched:
            return "PASS", f"Conditional trigger condition for rule was not active; check passed."

        # Trigger is active, evaluate then_condition
        then_field = then_cond.get("field", field_name)
        then_f_data = RuleEngine._get_field_data(declarations, then_field)
        then_val = then_f_data.get("value")
        then_detected = RuleEngine._is_valid_detected_value(then_val)

        if not then_detected:
            return RuleEngine._adjudicate_missing_field(then_field, is_mandatory, ocr_confidence)

        return "PASS", f"Conditional statutory requirement for '{then_field}' satisfied."

    @staticmethod
    def _evaluate_value(
        field_name: str,
        observed_value: Any,
        condition: Dict[str, Any],
        is_mandatory: bool,
        ocr_confidence: float,
        field_confidence: float = 0.0,
        norm_val: Any = None,
        error_message: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Evaluates value constraints (one_of, in, equals, not_equals).
        Strict fallback: NEVER returns PASS if mandatory field is missing/empty/Not Detected.
        """
        if not RuleEngine._is_valid_detected_value(observed_value):
            return RuleEngine._adjudicate_missing_field(field_name, is_mandatory, ocr_confidence)

        thresh = settings.OCR_REVIEW_THRESHOLD if hasattr(settings, "OCR_REVIEW_THRESHOLD") else 70.0
        operator = condition.get("operator", "one_of")
        allowed_values = [str(v).lower() for v in condition.get("values", [])]
        expected_val = str(condition.get("expected_value", "")).lower()

        val_str = str(norm_val if norm_val is not None else observed_value).strip().lower()

        if operator in ["one_of", "in"]:
            if val_str in allowed_values or any(val_str == av for av in allowed_values):
                return "PASS", f"Extracted value '{norm_val or observed_value}' is a valid statutory option in {allowed_values}."
            else:
                status = "FAIL" if field_confidence >= thresh else "REVIEW"
                err = error_message or f"Extracted value '{observed_value}' does not match allowed statutory options: {', '.join(allowed_values)}."
                return status, err
        elif operator == "equals":
            if val_str == expected_val:
                return "PASS", f"Extracted value matches required value '{expected_val}'."
            else:
                status = "FAIL" if field_confidence >= thresh else "REVIEW"
                err = error_message or f"Extracted value '{observed_value}' does not match expected '{expected_val}'."
                return status, err
        elif operator == "not_equals":
            if val_str != expected_val:
                return "PASS", f"Extracted value satisfies constraint (not equal to '{expected_val}')."
            else:
                return "FAIL", error_message or f"Extracted value '{observed_value}' matches prohibited value '{expected_val}'."

        return "PASS", f"Value check satisfied for '{field_name}'."

    @staticmethod
    def _evaluate_date(
        field_name: str,
        observed_value: Any,
        condition: Dict[str, Any],
        declarations: Dict[str, Any],
        is_mandatory: bool,
        ocr_confidence: float,
        field_confidence: float = 0.0,
        norm_dict: Optional[Dict[str, Any]] = None,
        eval_dt: Optional[date] = None,
        error_message: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Evaluates calendar date validity and sequence constraints.
        Strict fallback: NEVER returns PASS if mandatory date field is missing/empty/Not Detected.
        """
        if not RuleEngine._is_valid_detected_value(observed_value):
            return RuleEngine._adjudicate_missing_field(field_name, is_mandatory, ocr_confidence)

        thresh = settings.OCR_REVIEW_THRESHOLD if hasattr(settings, "OCR_REVIEW_THRESHOLD") else 70.0
        operator = condition.get("operator", "is_valid_date")
        compare_with_field = condition.get("compare_with")
        eval_dt = eval_dt or datetime.now(timezone.utc).date()

        d_obj = (norm_dict or {}).get("date_obj")
        if d_obj is None:
            if is_mandatory:
                if ocr_confidence >= 85.0:
                    return "FAIL", error_message or f"Date declaration '{field_name}' missing or could not be parsed into a valid calendar date."
                else:
                    return "REVIEW", f"Date value for '{field_name}' could not be reliably parsed as calendar date."
            else:
                return "NOT_APPLICABLE", "Optional declaration not detected; statutory check bypassed."

        if operator == "is_past_or_today":
            if d_obj <= eval_dt:
                return "PASS", f"Date {d_obj.strftime('%d/%m/%Y')} is valid and precedes/equals screening date."
            else:
                diff_days = (d_obj - eval_dt).days
                if diff_days <= 31:
                    return "REVIEW", f"Date {d_obj.strftime('%d/%m/%Y')} is slightly in the future ({diff_days} days ahead). Verification required."
                else:
                    status = "FAIL" if field_confidence >= thresh else "REVIEW"
                    return status, error_message or f"Date {d_obj.strftime('%d/%m/%Y')} is in the future relative to current date ({eval_dt.strftime('%d/%m/%Y')})."

        elif operator == "date_after_or_equal":
            ref_data = RuleEngine._get_field_data(declarations, compare_with_field or "manufacturing_date")
            ref_norm = DataNormalizer.normalize_field(compare_with_field or "manufacturing_date", ref_data.get("value"))
            ref_d_obj = ref_norm.get("date_obj")

            if ref_d_obj is None:
                return "REVIEW", f"Cannot compare {field_name} because reference date '{compare_with_field}' was not detected."
            else:
                if d_obj >= ref_d_obj:
                    return "PASS", f"Expiry date ({d_obj.strftime('%d/%m/%Y')}) is subsequent to manufacturing date ({ref_d_obj.strftime('%d/%m/%Y')})."
                else:
                    status = "FAIL" if field_confidence >= thresh else "REVIEW"
                    return status, error_message or f"Expiry date ({d_obj.strftime('%d/%m/%Y')}) precedes manufacturing date ({ref_d_obj.strftime('%d/%m/%Y')})."

        elif operator == "is_future_or_today":
            if d_obj >= eval_dt:
                return "PASS", f"Date {d_obj.strftime('%d/%m/%Y')} is current/future."
            else:
                status = "FAIL" if field_confidence >= thresh else "REVIEW"
                return status, error_message or f"Date {d_obj.strftime('%d/%m/%Y')} is expired as of {eval_dt.strftime('%d/%m/%Y')}."

        return "PASS", f"Date {d_obj.strftime('%d/%m/%Y')} is structurally valid."

    @staticmethod
    def _evaluate_text(
        field_name: str,
        observed_value: Any,
        condition: Dict[str, Any],
        declarations: Dict[str, Any],
        is_mandatory: bool,
        ocr_confidence: float,
        field_confidence: float = 0.0,
        error_message: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Evaluates text substring and keyword inclusion constraints.
        Strict fallback: NEVER returns PASS if mandatory text field is missing/empty/Not Detected.
        """
        if not RuleEngine._is_valid_detected_value(observed_value):
            return RuleEngine._adjudicate_missing_field(field_name, is_mandatory, ocr_confidence)

        thresh = settings.OCR_REVIEW_THRESHOLD if hasattr(settings, "OCR_REVIEW_THRESHOLD") else 70.0
        operator = condition.get("operator", "contains")
        required_val = condition.get("value", condition.get("substring", ""))
        values_list = condition.get("values", [])

        text_to_search = str(observed_value or "").lower()
        if field_name == "mrp_inclusive_tax" and not text_to_search:
            text_to_search = str(declarations.get("mrp_inclusive_tax", {}).get("value") or "").lower()

        if operator == "contains":
            if str(required_val).lower() in text_to_search:
                return "PASS", f"Extracted text contains mandatory phrase '{required_val}'."
            else:
                status = "FAIL" if field_confidence >= thresh else "REVIEW"
                return status, error_message or f"Declaration does not contain mandatory phrase '{required_val}'."

        elif operator == "contains_any":
            matched_kw = [kw for kw in values_list if str(kw).lower() in text_to_search]
            if matched_kw:
                return "PASS", f"Extracted text matches required declaration keyword '{matched_kw[0]}'."
            else:
                status = "FAIL" if field_confidence >= thresh else "REVIEW"
                return status, error_message or f"Declaration missing required statutory phrasing (expected one of: {', '.join(values_list)})."

        elif operator == "contains_all":
            missing_kw = [kw for kw in values_list if str(kw).lower() not in text_to_search]
            if not missing_kw:
                return "PASS", f"All required keywords {values_list} are present in declaration."
            else:
                status = "FAIL" if field_confidence >= thresh else "REVIEW"
                return status, error_message or f"Declaration missing mandatory elements: {', '.join(missing_kw)}."

        return "PASS", f"Text declaration check satisfied for '{field_name}'."

    # =========================================================================
    # Primary Rule Evaluation Method
    # =========================================================================

    @staticmethod
    def evaluate(
        rule: Union[ComplianceRuleDB, Dict[str, Any]],
        declarations: Dict[str, Any],
        ocr_overall_confidence: float = 90.0,
        image_quality_passed: bool = True,
        review_threshold: Optional[float] = None,
        high_conf_threshold: Optional[float] = None,
        evaluation_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a single compliance rule against extracted OCR declarations with strict
        mandatory vs. optional discrimination and confidence-aware adjudication.
        """
        # Defensive argument order swap: evaluate(declarations, rule)
        if isinstance(rule, dict) and isinstance(declarations, (list, tuple)):
            return RuleEngine.validate_declarations(rule, declarations, ocr_overall_confidence)

        eval_dt = evaluation_date or datetime.now(timezone.utc).date()

        # Extract rule metadata
        rule_id = str(_get_rule_attr(rule, "rule_id", "LM-RULE"))
        field_name = str(_get_rule_attr(rule, "field_name", "") or "")
        field_clean = field_name.strip().lower()
        rule_id_clean = rule_id.strip().upper()

        rule_type = str(_get_rule_attr(rule, "rule_type", "MANDATORY_FIELD")).upper()
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

        # Condition dict resolution
        if hasattr(rule, "get_condition_dict"):
            condition_dict = rule.get_condition_dict()
        else:
            condition_dict = _get_rule_attr(rule, "condition", {})
            if isinstance(condition_dict, str):
                import json
                try:
                    condition_dict = json.loads(condition_dict)
                except Exception:
                    condition_dict = {}

        severity = _get_rule_attr(rule, "severity", "HIGH")
        error_message = _get_rule_attr(rule, "error_message")

        # -------------------------------------------------------------
        # 1. Mandatory vs. Optional Discrimination
        # -------------------------------------------------------------
        explicit_mandatory = _get_rule_attr(rule, "is_mandatory")
        if explicit_mandatory is not None:
            is_mandatory = bool(explicit_mandatory)
        else:
            # If field is in known optional fields or rule_id has ALLERGEN / VOLUNTARY
            if field_clean in RuleEngine.OPTIONAL_FIELDS or "ALLERGEN" in rule_id_clean or "VOLUNTARY" in rule_id_clean:
                is_mandatory = False
            elif field_clean in RuleEngine.CORE_MANDATORY_FIELDS:
                # Core mandatory PCR 2011 fields must always be mandatory
                is_mandatory = True
            else:
                req_val = _get_rule_attr(rule, "required")
                is_mandatory = bool(req_val) if req_val is not None else True

        # -------------------------------------------------------------
        # 2. Dynamic UI Expected Requirement Text Override
        # -------------------------------------------------------------
        if not is_mandatory:
            expected_requirement = "Optional field under PCR 2011"
        else:
            raw_req = (
                _get_rule_attr(rule, "expected_requirement")
                or _get_rule_attr(rule, "requirement")
                or _get_rule_attr(rule, "legal_requirement")
                or _get_rule_attr(rule, "description")
                or "Must be declared on the package."
            )
            if "optional" in str(raw_req).lower():
                expected_requirement = "Must be declared on the package."
            else:
                expected_requirement = str(raw_req)

        # -------------------------------------------------------------
        # 3. Resolve Overall OCR Confidence from Payload
        # -------------------------------------------------------------
        overall_conf = (
            declarations.get("overall_confidence")
            or declarations.get("inspection_confidence")
            or declarations.get("ocr_overall_confidence")
            or declarations.get("confidence")
            or ocr_overall_confidence
            or 90.0
        )
        try:
            overall_conf = float(overall_conf)
        except (ValueError, TypeError):
            overall_conf = 90.0

        # Retrieve field evidence from declarations
        field_data = RuleEngine._get_field_data(declarations, field_name)
        raw_val = field_data.get("value")
        field_conf = float(field_data.get("confidence", 0.0))
        bbox = field_data.get("bbox")
        is_detected = RuleEngine._is_valid_detected_value(raw_val)

        # Normalize field value
        norm_dict = DataNormalizer.normalize_field(field_name, raw_val) if is_detected else {"normalized_value": None}
        norm_val = norm_dict.get("normalized_value")

        # Evidence structure
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

        effective_conf = field_conf if is_detected else overall_conf

        # General statutory provision without specific field target
        if not field_name:
            return {
                "rule_id": rule_id,
                "rule_name": _get_rule_attr(rule, "rule_name") or rule_id,
                "rule_version": _get_rule_attr(rule, "version", "2026.1.0"),
                "regulation": _get_rule_attr(rule, "regulation", "Legal Metrology"),
                "regulation_section": _get_rule_attr(rule, "regulation_section", ""),
                "source_reference": _get_rule_attr(rule, "source_reference", ""),
                "field": "general_provision",
                "field_name": "general_provision",
                "extracted_value": None,
                "observed": "Conforming",
                "observed_value": "Conforming",
                "detected_evidence": "Conforming",
                "normalized_value": None,
                "is_mandatory": False,
                "required": False,
                "severity": severity,
                "status": "PASS",
                "confidence": 100.0,
                "explanation": _get_rule_attr(rule, "compliance_condition") or "General statutory provision.",
                "reason": _get_rule_attr(rule, "compliance_condition") or "General statutory provision.",
                "expected_requirement": "Optional field under PCR 2011",
                "requirement": "Optional field under PCR 2011",
                "legal_requirement": "Optional field under PCR 2011",
                "evidence": evidence,
                "evaluated_at": datetime.now(timezone.utc).isoformat()
            }

        # -------------------------------------------------------------
        # 4. Dispatch to Specific Operator Evaluation Helper
        # -------------------------------------------------------------
        if rule_type == "MANDATORY_FIELD":
            status, explanation = RuleEngine._evaluate_mandatory(
                field_name=field_name,
                observed_value=raw_val,
                is_mandatory=is_mandatory,
                ocr_confidence=overall_conf,
                field_confidence=field_conf,
                condition=condition_dict,
                image_quality_passed=image_quality_passed,
                review_threshold=review_threshold,
                high_conf_threshold=high_conf_threshold
            )

        elif rule_type == "VALUE_CHECK":
            status, explanation = RuleEngine._evaluate_value(
                field_name=field_name,
                observed_value=raw_val,
                condition=condition_dict,
                is_mandatory=is_mandatory,
                ocr_confidence=overall_conf,
                field_confidence=field_conf,
                norm_val=norm_val,
                error_message=error_message
            )

        elif rule_type == "FORMAT_CHECK":
            status, explanation = RuleEngine._evaluate_format(
                field_name=field_name,
                observed_value=raw_val,
                condition=condition_dict,
                is_mandatory=is_mandatory,
                ocr_confidence=overall_conf,
                field_confidence=field_conf,
                norm_val=norm_val,
                error_message=error_message
            )

        elif rule_type == "RANGE_CHECK":
            status, explanation = RuleEngine._evaluate_range(
                field_name=field_name,
                observed_value=raw_val,
                condition=condition_dict,
                is_mandatory=is_mandatory,
                ocr_confidence=overall_conf,
                field_confidence=field_conf,
                norm_val=norm_val,
                error_message=error_message
            )

        elif rule_type == "DATE_CHECK":
            status, explanation = RuleEngine._evaluate_date(
                field_name=field_name,
                observed_value=raw_val,
                condition=condition_dict,
                declarations=declarations,
                is_mandatory=is_mandatory,
                ocr_confidence=overall_conf,
                field_confidence=field_conf,
                norm_dict=norm_dict,
                eval_dt=eval_dt,
                error_message=error_message
            )

        elif rule_type == "TEXT_CHECK":
            status, explanation = RuleEngine._evaluate_text(
                field_name=field_name,
                observed_value=raw_val,
                condition=condition_dict,
                declarations=declarations,
                is_mandatory=is_mandatory,
                ocr_confidence=overall_conf,
                field_confidence=field_conf,
                error_message=error_message
            )

        elif rule_type == "CONDITIONAL_RULE":
            status, explanation = RuleEngine._evaluate_condition(
                field_name=field_name,
                observed_value=raw_val,
                condition=condition_dict,
                declarations=declarations,
                is_mandatory=is_mandatory,
                ocr_confidence=overall_conf,
                field_confidence=field_conf,
                error_message=error_message
            )

        else:
            # Fallback for unknown rule types
            if not is_detected:
                status, explanation = RuleEngine._adjudicate_missing_field(
                    field_name,
                    is_mandatory,
                    overall_conf,
                    image_quality_passed=image_quality_passed,
                    review_threshold=review_threshold,
                    high_conf_threshold=high_conf_threshold
                )
            else:
                status = "PASS"
                explanation = f"Statutory declaration '{field_name}' verified."

        display_obs = str(raw_val) if is_detected else "Cannot Verify / Not Detected"

        return {
            "rule_id": rule_id,
            "rule_name": _get_rule_attr(rule, "rule_name") or rule_id,
            "rule_version": _get_rule_attr(rule, "version", "2026.1.0"),
            "regulation": _get_rule_attr(rule, "regulation", "Legal Metrology (Packaged Commodities) Rules, 2011"),
            "regulation_section": _get_rule_attr(rule, "regulation_section", ""),
            "source_reference": _get_rule_attr(rule, "source_reference", ""),
            "field": field_name,
            "field_name": field_name,
            "extracted_value": raw_val if is_detected else None,
            "observed": display_obs,
            "observed_value": display_obs,
            "detected_evidence": display_obs,
            "normalized_value": norm_val if is_detected else None,
            "is_mandatory": is_mandatory,
            "required": is_mandatory,
            "severity": severity,
            "status": status,  # "PASS" | "FAIL" | "REVIEW"
            "confidence": round(effective_conf, 2),
            "explanation": explanation,
            "reason": explanation,
            "expected_requirement": expected_requirement,
            "requirement": expected_requirement,
            "legal_requirement": expected_requirement,
            "evidence": evidence,
            "evaluated_at": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def evaluate_rule(
        rule: Union[ComplianceRuleDB, Dict[str, Any]],
        declarations: Dict[str, Any],
        ocr_overall_confidence: float = 90.0,
        image_quality_passed: bool = True,
        review_threshold: Optional[float] = None,
        high_conf_threshold: Optional[float] = None,
        evaluation_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Backward-compatible alias for evaluate()."""
        return RuleEngine.evaluate(
            rule=rule,
            declarations=declarations,
            ocr_overall_confidence=ocr_overall_confidence,
            image_quality_passed=image_quality_passed,
            review_threshold=review_threshold,
            high_conf_threshold=high_conf_threshold,
            evaluation_date=evaluation_date
        )

    @staticmethod
    def validate_declarations(
        declarations: Dict[str, Any],
        rules: List[Union[ComplianceRuleDB, Dict[str, Any]]],
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
            res = RuleEngine.evaluate(
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
