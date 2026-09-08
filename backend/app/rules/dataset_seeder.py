"""
dataset_seeder.py - External Rules Dataset Database Import / Seeding Utility
Populates database from canonical verified JSON dataset (rule engine dataset/rule_engine_rules.json).
"""

import json
import os
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session  # type: ignore
from sqlalchemy import or_  # type: ignore

from app.models import ComplianceRuleDB
from app.database import SessionLocal


def get_dataset_path() -> str:
    """
    Resolves the absolute path to the canonical rules dataset.
    Prioritizes 'rule engine dataset/rule_engine_rules.json'.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        # 1. Workspace root: 'rule engine dataset/rule_engine_rules.json'
        os.path.abspath(os.path.join(current_dir, "..", "..", "..", "rule engine dataset", "rule_engine_rules.json")),
        os.path.abspath(os.path.join(os.getcwd(), "rule engine dataset", "rule_engine_rules.json")),
        os.path.abspath(os.path.join(current_dir, "..", "..", "rule engine dataset", "rule_engine_rules.json")),
        # 2. Fallbacks inside rule engine dataset folder
        os.path.abspath(os.path.join(current_dir, "..", "..", "..", "rule engine dataset", "compliance_rules.json")),
        os.path.abspath(os.path.join(os.getcwd(), "rule engine dataset", "compliance_rules.json")),
        # 3. Local fallback
        os.path.join(current_dir, "data", "statutory_rules.json"),
    ]

    for p in candidates:
        if os.path.exists(p):
            return p

    return candidates[0]


def _map_canonical_rule_entry(r_entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms a rule from rule_engine_rules.json schema into ComplianceRuleDB schema attributes.
    """
    rule_id = r_entry.get("rule_id", "")
    provision = r_entry.get("provision") or {}
    r_num = provision.get("rule_number", "")
    sub_r = provision.get("sub_rule", "")
    clause = provision.get("clause", "")
    title = provision.get("title", "")

    sec_parts = []
    if r_num:
        s = f"Rule {r_num}"
        if sub_r:
            s += f"({sub_r})"
        if clause:
            s += f"({clause})"
        sec_parts.append(s)
    if title:
        sec_parts.append(title)
    reg_section = " - ".join(sec_parts) if sec_parts else r_entry.get("regulation_section", "")

    # Applicability to Product Category
    applicability = r_entry.get("applicability", [])
    if isinstance(applicability, str):
        applicability = [applicability]

    if "pre_packaged_general" in applicability or "ALL" in applicability:
        category = "ALL"
    elif "pre_packaged_food" in applicability:
        category = "Food & Beverages"
    elif "e_commerce_listing" in applicability:
        category = "E-Commerce"
    elif "cosmetics" in applicability:
        category = "Cosmetics"
    elif "medical_devices" in applicability:
        category = "Medical Devices"
    elif "pharma_price_controlled" in applicability:
        category = "Pharmaceuticals"
    elif "garments_hosiery" in applicability:
        category = "Garments & Hosiery"
    elif "pan_masala" in applicability:
        category = "Pan Masala"
    elif "bulk_over_25kg" in applicability:
        category = "Bulk Packages"
    elif "farm_produce" in applicability:
        category = "Farm Produce"
    elif "industrial_institutional" in applicability:
        category = "Institutional Consumer"
    elif "combination_group_package" in applicability:
        category = "Group Packages"
    elif "imported_products" in applicability:
        category = "Imported Products"
    elif applicability:
        category = ", ".join(applicability)
    else:
        category = "ALL"

    field_name = r_entry.get("field") or r_entry.get("field_name") or ""
    val_type = (r_entry.get("validation_type") or r_entry.get("rule_type") or "PRESENCE").upper()
    params = r_entry.get("parameters") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}

    # Map validation type & condition
    if val_type == "PRESENCE":
        rule_type = "MANDATORY_FIELD"
        cond_dict = {"operator": "present"}
    elif val_type == "UNIT":
        rule_type = "VALUE_CHECK"
        allowed_units = params.get("allowed_units", ["g", "kg", "ml", "l", "m", "cm", "mm", "number"])
        cond_dict = {"operator": "one_of", "values": allowed_units}
    elif val_type == "FORMAT":
        rule_type = "FORMAT_CHECK"
        if "required_phrases_any_of" in params or "required_phrase_all" in params:
            # Legal Metrology MRP tax phrases include recognized statutory abbreviations
            tax_variants = [
                "inclusive of all taxes", "incl. of all taxes", "incl of all taxes",
                "incl. all taxes", "incl taxes", "all taxes incl", "all taxes included",
                "inclusive of taxes", "incl. taxes", "maximum retail price", "mrp", "₹", "rs"
            ]
            cond_dict = {
                "operator": "contains_any",
                "values": tax_variants
            }
        elif "allowed_terms" in params:
            cond_dict = {"operator": "one_of", "values": params.get("allowed_terms", [])}
        else:
            cond_dict = params
    elif val_type == "DATE":
        rule_type = "DATE_CHECK"
        cond_dict = {"operator": "is_valid_date", "format": params.get("format", "DD/MM/YYYY or MM/YYYY")}
    elif val_type == "NUMERIC":
        rule_type = "RANGE_CHECK"
        cond_dict = params
    elif val_type in ["CONDITIONAL", "APPLICABILITY_EXCLUSION", "CROSS_FIELD"]:
        rule_type = "CONDITIONAL_RULE"
        cond_dict = params
    elif val_type == "DIMENSION":
        rule_type = "FORMAT_CHECK"
        cond_dict = params
    else:
        rule_type = r_entry.get("rule_type") or "MANDATORY_FIELD"
        cond_dict = r_entry.get("condition") or params

    chapter = provision.get("chapter", "")
    is_chapter_2 = "II" in chapter or "Retail sale" in chapter
    is_mandatory_param = params.get("mandatory", True) if isinstance(params, dict) else True

    # Distinguish mandatory on-pack declarations from voluntary marks, licensing, dimension, and exemptions
    non_mandatory_ids = {
        "LM-CR-008", "LM-CR-011", "LM-CR-012", "LM-CR-013", "LM-CR-014", "LM-CR-015",
        "LM-CR-016", "LM-CR-017", "LM-CR-018", "LM-CR-019", "LM-CR-020", "LM-CR-021",
        "LM-CR-022", "LM-CR-023", "LM-CR-024", "LM-CR-025", "LM-CR-001B", "LM-CR-005B",
        "LM-CR-007D", "LM-CR-007E", "LM-CR-009B", "LM-CR-012B", "LM-CR-013B"
    }

    if rule_id in non_mandatory_ids:
        required = False
    elif is_mandatory_param is False or not is_chapter_2 or val_type in ["APPLICABILITY_EXCLUSION", "DIMENSION"]:
        required = False
    else:
        required = True

    if r_entry.get("required") is not None:
        required = bool(r_entry.get("required"))

    severity = r_entry.get("severity", "HIGH")
    error_message = r_entry.get("error_message") or r_entry.get("description") or f"Statutory declaration '{field_name}' violation."
    explanation = r_entry.get("explanation") or provision.get("legal_text") or r_entry.get("description") or ""
    last_amended = r_entry.get("last_amended_by") or {}
    version = r_entry.get("version") or last_amended.get("gsr_number") or "2026.1.0"
    src = r_entry.get("source") or {}
    source_ref = r_entry.get("source_reference") or f"{src.get('gsr_number', '')} / {provision.get('provision_id', '')}".strip(" /")
    is_active = r_entry.get("verification_status") != "DEPRECATED"

    return {
        "rule_id": rule_id,
        "regulation": r_entry.get("regulation") or "Legal Metrology (Packaged Commodities) Rules, 2011",
        "regulation_section": reg_section,
        "product_category": category,
        "field_name": field_name,
        "rule_type": rule_type,
        "condition": json.dumps(cond_dict),
        "required": required,
        "severity": severity,
        "error_message": error_message,
        "explanation": explanation,
        "version": version,
        "source_reference": source_ref,
        "is_active": is_active,
        "rule_category": category,
        "statutory_reference": reg_section or "Legal Metrology",
        "target_parameter": field_name or rule_id,
        "compliance_condition": explanation,
        "violation_condition": error_message
    }


# Canonical statutory complementary rules: duplicates removed to maintain clean non-overlapping rule evaluation
DUPLICATE_RULE_IDS = {
    "LM-PCR-2011-R06-S1-F-CARE",
    "FSSAI-LDR-2020-R05-S2-ING",
    "FSSAI-LDR-2020-R05-S3-ALG",
    # Redundant legacy LM-CR- rules superseded by LM-PCR-2011-R06 and FSSAI- series
    "LM-CR-001",
    "LM-CR-001B",
    "LM-CR-003",
    "LM-CR-004",
    "LM-CR-004B",
    "LM-CR-005",
    "LM-CR-006",
    "LM-CR-007",
    "LM-CR-007B",
    "LM-CR-007C",
    "LM-CR-007D",
    "LM-CR-007E",
    "LM-CR-011",
}
COMPLEMENTARY_STATUTORY_RULES: List[Dict[str, Any]] = []


def seed_rules_from_dataset(db: Optional[Session] = None, force_reload: bool = False) -> int:
    """
    Imports statutory rules from 'rule engine dataset' and 'data/statutory_rules.json' into the database.
    Eliminates duplicates and ensures exactly the canonical 34 statutory rules exist.
    """
    local_db = db or SessionLocal()
    close_on_finish = db is None
    seeded_count = 0
    try:
        # Purge any known duplicate rule IDs, obsolete placeholders, or pseudo-rules
        local_db.query(ComplianceRuleDB).filter(
            or_(
                ComplianceRuleDB.rule_id.in_(DUPLICATE_RULE_IDS),
                ComplianceRuleDB.rule_id.like("rule_%"),
                ComplianceRuleDB.rule_id.like("DECL-%"),
                ComplianceRuleDB.rule_id.like("VIS-%"),
                ComplianceRuleDB.rule_id.like("OCR-DET-%")
            )
        ).delete(synchronize_session=False)
        local_db.commit()

        # 1. Load primary statutory rules (LM-PCR & FSSAI mandatory declarations)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        statutory_json = os.path.join(current_dir, "data", "statutory_rules.json")
        statutory_entries: List[Dict[str, Any]] = []
        if os.path.exists(statutory_json):
            with open(statutory_json, "r", encoding="utf-8") as f:
                stat_data = json.load(f)
                if isinstance(stat_data, list):
                    for r in stat_data:
                        rid = r.get("rule_id", "")
                        if rid and rid not in DUPLICATE_RULE_IDS:
                            statutory_entries.append({
                                "rule_id": rid,
                                "regulation": r.get("regulation", "Legal Metrology (Packaged Commodities) Rules, 2011"),
                                "regulation_section": r.get("regulation_section", ""),
                                "product_category": r.get("product_category", "ALL"),
                                "field_name": r.get("field_name", ""),
                                "rule_type": r.get("rule_type", "MANDATORY_FIELD"),
                                "condition": json.dumps(r.get("condition", {})),
                                "required": r.get("required", True),
                                "severity": r.get("severity", "HIGH"),
                                "error_message": r.get("error_message", ""),
                                "explanation": r.get("explanation", ""),
                                "version": r.get("version", "2026.1.0"),
                                "source_reference": r.get("source_reference", ""),
                                "is_active": r.get("is_active", True),
                                "rule_category": r.get("product_category", "ALL"),
                                "statutory_reference": r.get("regulation_section", "Legal Metrology"),
                                "target_parameter": r.get("field_name", rid),
                                "compliance_condition": r.get("explanation", ""),
                                "violation_condition": r.get("error_message", "")
                            })

        # 2. Load complementary rules from rule engine dataset
        dataset_file = get_dataset_path()
        canonical_entries: List[Dict[str, Any]] = []
        if os.path.exists(dataset_file):
            with open(dataset_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            rules_list: List[Dict[str, Any]] = []
            if isinstance(raw_data, list):
                rules_list = raw_data
            elif isinstance(raw_data, dict):
                rules_list = raw_data.get("rules", [])

            canonical_entries = [
                _map_canonical_rule_entry(r) for r in rules_list 
                if r.get("rule_id") and r.get("rule_id") not in DUPLICATE_RULE_IDS
            ]

        # 3. Combine without duplicates
        seen_rids = set()
        all_entries: List[Dict[str, Any]] = []
        for e in (statutory_entries + canonical_entries):
            rid = e.get("rule_id")
            if rid and rid not in seen_rids and rid not in DUPLICATE_RULE_IDS:
                seen_rids.add(rid)
                all_entries.append(e)

        for mapped in all_entries:
            rule_id = mapped["rule_id"]
            if not rule_id:
                continue

            existing = local_db.query(ComplianceRuleDB).filter(ComplianceRuleDB.rule_id == rule_id).first()

            if existing:
                # Clean upsert: update attributes on existing record
                existing.regulation = mapped.get("regulation")
                existing.regulation_section = mapped.get("regulation_section")
                existing.product_category = mapped.get("product_category", "ALL")
                existing.field_name = mapped.get("field_name")
                existing.rule_type = mapped.get("rule_type", "MANDATORY_FIELD")
                existing.condition = mapped.get("condition")
                existing.required = mapped.get("required", True)
                existing.severity = mapped.get("severity", "HIGH")
                existing.error_message = mapped.get("error_message")
                existing.explanation = mapped.get("explanation")
                existing.version = mapped.get("version", "2026.1.0")
                existing.source_reference = mapped.get("source_reference")
                existing.is_active = mapped.get("is_active", True)
                existing.rule_category = mapped.get("rule_category", "ALL")
                existing.statutory_reference = mapped.get("statutory_reference")
                existing.target_parameter = mapped.get("target_parameter")
                existing.compliance_condition = mapped.get("compliance_condition")
                existing.violation_condition = mapped.get("violation_condition")
            else:
                # Insert new rule record
                new_rule = ComplianceRuleDB(
                    rule_id=rule_id,
                    regulation=mapped.get("regulation"),
                    regulation_section=mapped.get("regulation_section"),
                    product_category=mapped.get("product_category", "ALL"),
                    field_name=mapped.get("field_name"),
                    rule_type=mapped.get("rule_type", "MANDATORY_FIELD"),
                    condition=mapped.get("condition"),
                    required=mapped.get("required", True),
                    severity=mapped.get("severity", "HIGH"),
                    error_message=mapped.get("error_message"),
                    explanation=mapped.get("explanation"),
                    version=mapped.get("version", "2026.1.0"),
                    source_reference=mapped.get("source_reference"),
                    is_active=mapped.get("is_active", True),
                    rule_category=mapped.get("rule_category", "ALL"),
                    statutory_reference=mapped.get("statutory_reference"),
                    target_parameter=mapped.get("target_parameter"),
                    compliance_condition=mapped.get("compliance_condition"),
                    violation_condition=mapped.get("violation_condition")
                )
                local_db.add(new_rule)

            local_db.commit()
            seeded_count += 1

        return seeded_count

    finally:
        if close_on_finish:
            local_db.close()


