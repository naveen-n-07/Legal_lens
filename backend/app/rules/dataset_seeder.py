"""
dataset_seeder.py - External Rules Dataset Database Import / Seeding Utility
Populates database from canonical verified JSON dataset (rule engine dataset/rule_engine_rules.json).
"""

import json
import os
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session  # type: ignore

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


# Statutory complementary provisions for full package screening (Food Safety & Customer Care)
COMPLEMENTARY_STATUTORY_RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "LM-PCR-2011-R06-S1-E-MRP",
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "regulation_section": "Rule 6(1)(e)",
        "product_category": "ALL",
        "field_name": "mrp",
        "rule_type": "MANDATORY_FIELD",
        "condition": json.dumps({"operator": "present"}),
        "required": True,
        "severity": "HIGH",
        "error_message": "Maximum Retail Price (MRP) declaration is mandatory under Rule 6(1)(e).",
        "explanation": "Rule 6(1)(e) mandates that the retail sale price (MRP) inclusive of all taxes must be declared.",
        "version": "2026.1.0",
        "source_reference": "Rule 6(1)(e) - Legal Metrology (Packaged Commodities) Rules, 2011",
        "is_active": True,
        "rule_category": "ALL",
        "statutory_reference": "Rule 6(1)(e) - Retail Sale Price",
        "target_parameter": "mrp",
        "compliance_condition": "Retail Sale Price (MRP) must be declared inclusive of all taxes.",
        "violation_condition": "Missing MRP declaration."
    },
    {
        "rule_id": "LM-PCR-2011-R06-S1-F-CARE",
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "regulation_section": "Rule 6(1)(n)",
        "product_category": "ALL",
        "field_name": "consumer_care",
        "rule_type": "MANDATORY_FIELD",
        "condition": json.dumps({"operator": "present"}),
        "required": True,
        "severity": "HIGH",
        "error_message": "Consumer care details (name, address, telephone/email) missing under Rule 6(1)(n).",
        "explanation": "Rule 6(1)(n) mandates the declaration of name, address, telephone number and email address of the person or office to contact in case of consumer complaints.",
        "version": "2026.1.0",
        "source_reference": "Rule 6(1)(n) - Legal Metrology (Packaged Commodities) Rules, 2011",
        "is_active": True,
        "rule_category": "ALL",
        "statutory_reference": "Rule 6(1)(n) - Consumer Care Details",
        "target_parameter": "consumer_care",
        "compliance_condition": "Consumer care contact details must be provided.",
        "violation_condition": "Missing consumer care details."
    },
    {
        "rule_id": "FSSAI-LDR-2020-R05-S7-LIC",
        "regulation": "Food Safety and Standards (Labelling and Display) Regulations, 2020",
        "regulation_section": "Regulation 5(7)",
        "product_category": "Food & Beverages",
        "field_name": "fssai_license",
        "rule_type": "FORMAT_CHECK",
        "condition": json.dumps({"operator": "regex", "pattern": r"^\d{14}$"}),
        "required": True,
        "severity": "HIGH",
        "error_message": "FSSAI logo and 14-digit license number is mandatory on pre-packaged food.",
        "explanation": "Regulation 5(7) of FSSAI requires the FSSAI logo and 14-digit license number to be displayed on the label of food products.",
        "version": "2026.1.0",
        "source_reference": "Regulation 5(7) - FSSAI Labelling and Display Regulations, 2020",
        "is_active": True,
        "rule_category": "Food & Beverages",
        "statutory_reference": "FSSAI Regulation 5(7) - License Number",
        "target_parameter": "fssai_license",
        "compliance_condition": "14-digit FSSAI license must be present.",
        "violation_condition": "Invalid or missing FSSAI license."
    },
    {
        "rule_id": "FSSAI-LDR-2020-R05-S2-ING",
        "regulation": "Food Safety and Standards (Labelling and Display) Regulations, 2020",
        "regulation_section": "Regulation 5(2)",
        "product_category": "Food & Beverages",
        "field_name": "ingredients",
        "rule_type": "MANDATORY_FIELD",
        "condition": json.dumps({"operator": "present"}),
        "required": True,
        "severity": "HIGH",
        "error_message": "List of ingredients is mandatory for pre-packaged food commodities.",
        "explanation": "Regulation 5(2) mandates a complete list of ingredients in descending order of weight or volume.",
        "version": "2026.1.0",
        "source_reference": "Regulation 5(2) - FSSAI Labelling and Display Regulations, 2020",
        "is_active": True,
        "rule_category": "Food & Beverages",
        "statutory_reference": "FSSAI Regulation 5(2) - Ingredients List",
        "target_parameter": "ingredients",
        "compliance_condition": "List of ingredients must be declared.",
        "violation_condition": "Missing ingredients list."
    },
    {
        "rule_id": "FSSAI-LDR-2020-R05-S3-ALG",
        "regulation": "Food Safety and Standards (Labelling and Display) Regulations, 2020",
        "regulation_section": "Regulation 5(3)",
        "product_category": "Food & Beverages",
        "field_name": "allergen_declaration",
        "rule_type": "MANDATORY_FIELD",
        "condition": json.dumps({"operator": "present"}),
        "required": False,
        "severity": "MEDIUM",
        "error_message": "Allergen declaration required if product contains allergenic ingredients.",
        "explanation": "Regulation 5(3) mandates allergen declaration for known major allergens.",
        "version": "2026.1.0",
        "source_reference": "Regulation 5(3) - FSSAI Labelling and Display Regulations, 2020",
        "is_active": True,
        "rule_category": "Food & Beverages",
        "statutory_reference": "FSSAI Regulation 5(3) - Allergen Declaration",
        "target_parameter": "allergen_declaration",
        "compliance_condition": "Allergen statement should be declared where applicable.",
        "violation_condition": "Missing allergen declaration."
    }
]


def seed_rules_from_dataset(db: Optional[Session] = None, force_reload: bool = False) -> int:
    """
    Imports statutory rules from 'rule engine dataset' into the database.
    Performs clean upserts to avoid primary key collisions or sqlite3.IntegrityError.
    """
    dataset_file = get_dataset_path()
    if not os.path.exists(dataset_file):
        return 0

    local_db = db or SessionLocal()
    close_on_finish = db is None
    seeded_count = 0

    try:
        with open(dataset_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        rules_list: List[Dict[str, Any]] = []
        if isinstance(raw_data, list):
            rules_list = raw_data
        elif isinstance(raw_data, dict):
            rules_list = raw_data.get("rules", [])

        # 1. Transform canonical rules from rule engine dataset
        canonical_entries = [_map_canonical_rule_entry(r) for r in rules_list if r.get("rule_id")]

        # 2. Append complementary statutory rules (FSSAI & Rule 6 aliases)
        all_entries = canonical_entries + COMPLEMENTARY_STATUTORY_RULES

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

