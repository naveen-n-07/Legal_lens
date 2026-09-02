"""
dataset_seeder.py - External Rules Dataset Database Import / Seeding Utility
Populates database from external verified JSON dataset (zero hardcoded rules in code).
"""

import json
import os
from typing import Optional
from sqlalchemy.orm import Session  # type: ignore

from app.models import ComplianceRuleDB
from app.rules.repository import RuleRepository
from app.database import SessionLocal

def get_dataset_path() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    primary_path = os.path.join(current_dir, "data", "statutory_rules.json")
    if os.path.exists(primary_path):
        return primary_path

    # Fallback paths
    backend_dir = os.path.dirname(os.path.dirname(current_dir))
    fallback_path = os.path.join(backend_dir, "legal_metrology_compliance_rules.json")
    return fallback_path

def seed_rules_from_dataset(db: Optional[Session] = None, force_reload: bool = False) -> int:
    """
    Imports statutory rules from external dataset into the database.
    """
    dataset_file = get_dataset_path()
    if not os.path.exists(dataset_file):
        return 0

    local_db = db or SessionLocal()
    close_on_finish = db is None
    seeded_count = 0

    try:
        with open(dataset_file, "r", encoding="utf-8") as f:
            rules_data = json.load(f)

        if not isinstance(rules_data, list):
            rules_data = rules_data.get("rules", [])

        for r_entry in rules_data:
            rule_id = r_entry.get("rule_id")
            if not rule_id:
                continue

            existing = local_db.query(ComplianceRuleDB).filter(ComplianceRuleDB.rule_id == rule_id).first()
            if existing and not force_reload:
                # Update any empty new schema fields without overwriting admin edits
                if not existing.regulation and r_entry.get("regulation"):
                    existing.regulation = r_entry.get("regulation")
                if not existing.regulation_section and r_entry.get("regulation_section"):
                    existing.regulation_section = r_entry.get("regulation_section")
                if not existing.rule_type and r_entry.get("rule_type"):
                    existing.rule_type = r_entry.get("rule_type")
                if not existing.condition and r_entry.get("condition"):
                    existing.set_condition_dict(r_entry.get("condition"))
                if not existing.source_reference and r_entry.get("source_reference"):
                    existing.source_reference = r_entry.get("source_reference")
                if not existing.explanation and r_entry.get("explanation"):
                    existing.explanation = r_entry.get("explanation")
                local_db.commit()
                seeded_count += 1
                continue

            cond_str = json.dumps(r_entry.get("condition")) if isinstance(r_entry.get("condition"), dict) else r_entry.get("condition")

            if existing and force_reload:
                existing.regulation = r_entry.get("regulation")
                existing.regulation_section = r_entry.get("regulation_section")
                existing.product_category = r_entry.get("product_category", "ALL")
                existing.field_name = r_entry.get("field_name")
                existing.rule_type = r_entry.get("rule_type", "MANDATORY_FIELD")
                existing.condition = cond_str
                existing.required = r_entry.get("required", True)
                existing.severity = r_entry.get("severity", "HIGH")
                existing.error_message = r_entry.get("error_message")
                existing.explanation = r_entry.get("explanation")
                existing.version = r_entry.get("version", "2026.1.0")
                existing.source_reference = r_entry.get("source_reference")
                existing.is_active = r_entry.get("is_active", True)
            else:
                new_rule = ComplianceRuleDB(
                    rule_id=rule_id,
                    regulation=r_entry.get("regulation"),
                    regulation_section=r_entry.get("regulation_section"),
                    product_category=r_entry.get("product_category", "ALL"),
                    field_name=r_entry.get("field_name"),
                    rule_type=r_entry.get("rule_type", "MANDATORY_FIELD"),
                    condition=cond_str,
                    required=r_entry.get("required", True),
                    severity=r_entry.get("severity", "HIGH"),
                    error_message=r_entry.get("error_message"),
                    explanation=r_entry.get("explanation"),
                    version=r_entry.get("version", "2026.1.0"),
                    source_reference=r_entry.get("source_reference"),
                    is_active=r_entry.get("is_active", True),
                    rule_category=r_entry.get("product_category", "ALL"),
                    statutory_reference=r_entry.get("regulation") or f"{r_entry.get('regulation_section', '')} - {r_entry.get('regulation', '')}",
                    target_parameter=r_entry.get("field_name") or rule_id,
                    compliance_condition=r_entry.get("explanation") or "",
                    violation_condition=r_entry.get("error_message") or ""
                )
                local_db.add(new_rule)

            local_db.commit()
            seeded_count += 1

        return seeded_count

    finally:
        if close_on_finish:
            local_db.close()
