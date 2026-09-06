"""
repository.py - Dynamic Compliance Rule Database Abstraction Layer (RuleRepository)
Loads and queries versioned statutory rules dynamically from database storage without hard-coded rules.
"""

import json
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any, Union, Tuple
from sqlalchemy.orm import Session  # type: ignore
from sqlalchemy import or_, and_  # type: ignore

from app.models import ComplianceRuleDB
from app.database import SessionLocal

VALID_RULE_TYPES = {
    "MANDATORY_FIELD",
    "VALUE_CHECK",
    "FORMAT_CHECK",
    "RANGE_CHECK",
    "DATE_CHECK",
    "TEXT_CHECK",
    "CONDITIONAL_RULE",
    "PRESENCE",
    "UNIT",
    "FORMAT",
    "DATE",
    "NUMERIC",
    "DIMENSION",
    "CONDITIONAL",
    "APPLICABILITY_EXCLUSION",
    "CROSS_FIELD"
}

GENERIC_CATEGORIES = {"ALL", "All Commodities", "Pre-Packaged Commodities", "General Commodities", "*", "pre_packaged_general"}


class RuleRepository:

    @staticmethod
    def validate_rule_schema(data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates rule attributes to ensure invalid rule definitions cannot enter the database.
        """
        rule_id = data.get("rule_id")
        if not rule_id or not str(rule_id).strip():
            return False, "Missing mandatory field 'rule_id'."

        rule_type = data.get("rule_type", "MANDATORY_FIELD")
        if rule_type not in VALID_RULE_TYPES:
            return False, f"Unsupported rule_type '{rule_type}'. Allowed types: {', '.join(sorted(VALID_RULE_TYPES))}."

        # Validate condition format
        cond = data.get("condition")
        if cond is not None and not isinstance(cond, (dict, str)):
            return False, "Condition must be a valid structured JSON object or dictionary."

        # Validate date consistency if provided
        ef_from = data.get("effective_from")
        ef_to = data.get("effective_to")
        if ef_from and ef_to:
            try:
                dt_from = datetime.fromisoformat(ef_from) if isinstance(ef_from, str) else ef_from
                dt_to = datetime.fromisoformat(ef_to) if isinstance(ef_to, str) else ef_to
                if dt_to < dt_from:
                    return False, "effective_to date cannot be earlier than effective_from date."
            except Exception as e:
                return False, f"Invalid date format in effective dates: {str(e)}"

        return True, None

    @staticmethod
    def get_rule_by_id(rule_id: str, db: Optional[Session] = None) -> Optional[ComplianceRuleDB]:
        """Fetches a single compliance rule by primary key."""
        local_db = db or SessionLocal()
        try:
            return local_db.query(ComplianceRuleDB).filter(ComplianceRuleDB.rule_id == rule_id).first()
        finally:
            if db is None:
                local_db.close()

    @staticmethod
    def get_applicable_rules(
        category: Optional[str] = "ALL",
        effective_date: Optional[Union[datetime, date]] = None,
        regulation: Optional[str] = None,
        is_active: bool = True,
        db: Optional[Session] = None
    ) -> List[ComplianceRuleDB]:
        """
        Dynamically fetches applicable compliance rules from the database based on category, date, and regulation.
        Applies hierarchy: specific category rules + generic (ALL / Pre-Packaged Commodities) rules.
        """
        local_db = db or SessionLocal()
        close_on_finish = db is None

        try:
            query = local_db.query(ComplianceRuleDB)

            # 1. Filter by active status
            if is_active:
                query = query.filter(ComplianceRuleDB.is_active.is_(True))

            # 2. Filter by regulation if specified
            if regulation and regulation.strip():
                reg_clean = regulation.strip()
                query = query.filter(
                    or_(
                        ComplianceRuleDB.regulation.ilike(f"%{reg_clean}%"),
                        ComplianceRuleDB.statutory_reference.ilike(f"%{reg_clean}%")
                    )
                )

            # 3. Filter by effective date
            check_dt = effective_date or datetime.now(timezone.utc)
            if isinstance(check_dt, date) and not isinstance(check_dt, datetime):
                check_dt = datetime(check_dt.year, check_dt.month, check_dt.day, tzinfo=timezone.utc)

            # Date window conditions:
            # effective_from is None OR effective_from <= check_dt
            # effective_to is None OR effective_to >= check_dt
            query = query.filter(
                or_(ComplianceRuleDB.effective_from.is_(None), ComplianceRuleDB.effective_from <= check_dt),
                or_(ComplianceRuleDB.effective_to.is_(None), ComplianceRuleDB.effective_to >= check_dt)
            )

            # 4. Filter by Category Hierarchy
            target_cat = (category or "ALL").strip()
            applicable_categories = list(GENERIC_CATEGORIES)
            if target_cat and target_cat not in GENERIC_CATEGORIES:
                applicable_categories.append(target_cat)
                # If "Food & Beverages", also match "Food", "Beverages"
                if "&" in target_cat:
                    for sub in target_cat.split("&"):
                        applicable_categories.append(sub.strip())

            # Category filter (case-insensitive)
            cat_filters = [
                ComplianceRuleDB.product_category.ilike(f"%{c}%") for c in applicable_categories
            ]
            cat_filters.append(ComplianceRuleDB.product_category.is_(None))
            query = query.filter(or_(*cat_filters))
            query = query.filter(ComplianceRuleDB.field_name.isnot(None), ComplianceRuleDB.field_name != "")

            rules = query.all()

            # Deduplicate by rule_id while preserving order
            seen_ids = set()
            unique_rules = []
            for r in rules:
                if r.rule_id not in seen_ids:
                    seen_ids.add(r.rule_id)
                    unique_rules.append(r)

            return unique_rules

        finally:
            if close_on_finish:
                local_db.close()

    @staticmethod
    def create_rule(data: Dict[str, Any], db: Optional[Session] = None) -> ComplianceRuleDB:
        """Creates and stores a new statutory compliance rule in the database."""
        is_valid, err = RuleRepository.validate_rule_schema(data)
        if not is_valid:
            raise ValueError(err)

        local_db = db or SessionLocal()
        close_on_finish = db is None

        try:
            rule_id = data["rule_id"]
            existing = local_db.query(ComplianceRuleDB).filter(ComplianceRuleDB.rule_id == rule_id).first()
            if existing:
                raise ValueError(f"Rule with rule_id '{rule_id}' already exists.")

            cond_str = json.dumps(data["condition"]) if isinstance(data.get("condition"), dict) else data.get("condition")
            
            rule = ComplianceRuleDB(
                rule_id=rule_id,
                regulation=data.get("regulation"),
                regulation_section=data.get("regulation_section"),
                product_category=data.get("product_category", "ALL"),
                field_name=data.get("field_name"),
                rule_type=data.get("rule_type", "MANDATORY_FIELD"),
                condition=cond_str,
                required=data.get("required", True),
                severity=data.get("severity", "HIGH"),
                error_message=data.get("error_message"),
                explanation=data.get("explanation"),
                effective_from=data.get("effective_from"),
                effective_to=data.get("effective_to"),
                version=data.get("version", "1.0.0"),
                source_reference=data.get("source_reference"),
                is_active=data.get("is_active", True),
                # Legacy compatibility
                rule_category=data.get("product_category", "ALL"),
                statutory_reference=data.get("regulation") or f"{data.get('regulation_section', '')} - {data.get('regulation', '')}",
                target_parameter=data.get("field_name") or data.get("rule_id"),
                compliance_condition=data.get("explanation") or "",
                violation_condition=data.get("error_message") or ""
            )

            local_db.add(rule)
            local_db.commit()
            local_db.refresh(rule)
            return rule

        finally:
            if close_on_finish:
                local_db.close()

    @staticmethod
    def update_rule(rule_id: str, data: Dict[str, Any], db: Optional[Session] = None) -> Optional[ComplianceRuleDB]:
        """Updates an existing compliance rule in the database."""
        local_db = db or SessionLocal()
        close_on_finish = db is None

        try:
            rule = local_db.query(ComplianceRuleDB).filter(ComplianceRuleDB.rule_id == rule_id).first()
            if not rule:
                return None

            if "rule_type" in data and data["rule_type"] not in VALID_RULE_TYPES:
                raise ValueError(f"Invalid rule_type '{data['rule_type']}'.")

            for field in [
                "regulation", "regulation_section", "product_category", "field_name",
                "rule_type", "required", "severity", "error_message", "explanation",
                "effective_from", "effective_to", "version", "source_reference", "is_active"
            ]:
                if field in data:
                    setattr(rule, field, data[field])

            if "condition" in data:
                rule.set_condition_dict(data["condition"] if isinstance(data["condition"], dict) else json.loads(data["condition"]))

            # Sync legacy compatibility fields
            rule.rule_category = rule.product_category
            rule.statutory_reference = rule.regulation or rule.statutory_reference
            rule.target_parameter = rule.field_name or rule.target_parameter
            rule.compliance_condition = rule.explanation or rule.compliance_condition
            rule.violation_condition = rule.error_message or rule.violation_condition
            rule.updated_at = datetime.now(timezone.utc)

            local_db.commit()
            local_db.refresh(rule)
            return rule

        finally:
            if close_on_finish:
                local_db.close()

    @staticmethod
    def delete_rule(rule_id: str, db: Optional[Session] = None) -> bool:
        """Deletes a rule by ID."""
        local_db = db or SessionLocal()
        close_on_finish = db is None

        try:
            rule = local_db.query(ComplianceRuleDB).filter(ComplianceRuleDB.rule_id == rule_id).first()
            if not rule:
                return False
            local_db.delete(rule)
            local_db.commit()
            return True
        finally:
            if close_on_finish:
                local_db.close()

    @staticmethod
    def list_rules(
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        regulation: Optional[str] = None,
        db: Optional[Session] = None
    ) -> List[ComplianceRuleDB]:
        """Lists all compliance rules with optional filters."""
        local_db = db or SessionLocal()
        close_on_finish = db is None

        try:
            query = local_db.query(ComplianceRuleDB)
            if is_active is not None:
                query = query.filter(ComplianceRuleDB.is_active.is_(is_active))
            if category and category != "ALL":
                query = query.filter(ComplianceRuleDB.product_category.ilike(f"%{category}%"))
            if regulation:
                query = query.filter(ComplianceRuleDB.regulation.ilike(f"%{regulation}%"))
            return query.order_by(ComplianceRuleDB.rule_id.asc()).all()
        finally:
            if close_on_finish:
                local_db.close()

# Type alias helper
Tuple_Validation = tuple[bool, Optional[str]]
