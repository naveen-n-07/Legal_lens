"""
compliance_service.py - High-Level Compliance Screening & Rule Orchestration Service
Coordinates category detection, dynamic rule fetching, RuleEngine evaluation, and overall screening result aggregation.
"""

from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session  # type: ignore

from app.rules.repository import RuleRepository
from app.rules.engine import RuleEngine
from app.database import SessionLocal

class ComplianceService:

    @staticmethod
    def identify_product_category(
        declarations: Dict[str, Any],
        user_selected_category: Optional[str] = None
    ) -> Tuple_Cat:
        """
        Determines the product category. User selection takes top priority.
        If not selected or 'ALL', infers category from detected declarations.
        Returns: (final_category_name, is_user_specified)
        """
        if user_selected_category and user_selected_category.strip() not in ["", "ALL", "Auto-Detect", "None"]:
            return user_selected_category.strip(), True

        # Automatic category inference based on extracted field presence
        has_fssai = declarations.get("fssai_license", {}).get("detected") or bool(declarations.get("fssai_license", {}).get("value"))
        has_ingredients = declarations.get("ingredients", {}).get("detected") or bool(declarations.get("ingredients", {}).get("value"))
        has_allergen = declarations.get("allergen_declaration", {}).get("detected") or bool(declarations.get("allergen_declaration", {}).get("value"))

        if has_fssai or (has_ingredients and has_allergen):
            return "Food & Beverages", False

        raw_generic = str(declarations.get("product_name", {}).get("value") or declarations.get("generic_name", {}).get("value") or "").upper()
        food_terms = ["BISCUIT", "COOKIE", "CHIPS", "NOODLE", "SNACK", "FLOUR", "ATTA", "OIL", "MILK", "CHOCOLATE", "TEA", "COFFEE", "RICE", "SUGAR"]
        if any(term in raw_generic for term in food_terms):
            return "Food & Beverages", False

        cosmetic_terms = ["CREAM", "LOTION", "SHAMPOO", "SOAP", "SERUM", "PERFUME", "LIPSTICK", "DEODORANT"]
        if any(term in raw_generic for term in cosmetic_terms):
            return "Cosmetics", False

        pharma_terms = ["TABLET", "CAPSULE", "SYRUP", "OINTMENT", "INJECTION", "IP", "BP", "USP"]
        if any(term in raw_generic for term in pharma_terms):
            return "Pharmaceuticals", False

        return "ALL", False

    @staticmethod
    def validate_product(
        declarations: Dict[str, Any],
        category: Optional[str] = None,
        effective_date: Optional[Union[datetime, date]] = None,
        regulation: Optional[str] = None,
        ocr_overall_confidence: float = 90.0,
        image_quality_passed: bool = True,
        review_threshold: Optional[float] = None,
        high_conf_threshold: Optional[float] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates full compliance screening:
        1. Resolves product category & date
        2. Retrieves active statutory rules dynamically from database
        3. Runs stateless RuleEngine
        4. Calculates overall status and auditable screening summary
        """
        final_category, is_user_specified = ComplianceService.identify_product_category(declarations, category)
        eval_dt = effective_date or datetime.now(timezone.utc).date()
        if isinstance(eval_dt, datetime):
            eval_dt = eval_dt.date()

        # Retrieve applicable rules from database repository
        rules = RuleRepository.get_applicable_rules(
            category=final_category,
            effective_date=eval_dt,
            regulation=regulation,
            is_active=True,
            db=db
        )

        # Run RuleEngine evaluation
        results = RuleEngine.validate_declarations(
            declarations=declarations,
            rules=rules,
            ocr_overall_confidence=ocr_overall_confidence,
            image_quality_passed=image_quality_passed,
            review_threshold=review_threshold,
            high_conf_threshold=high_conf_threshold,
            evaluation_date=eval_dt
        )

        # Calculate counts
        total_rules = len(results)
        passed_count = sum(1 for r in results if r["status"] == "PASS")
        failed_count = sum(1 for r in results if r["status"] == "FAIL")
        review_count = sum(1 for r in results if r["status"] == "NEEDS_REVIEW")

        # Determine overall screening status safely
        if failed_count > 0:
            overall_status = "NON-COMPLIANT"
        elif review_count > 0:
            overall_status = "NEEDS REVIEW"
        else:
            overall_status = "COMPLIANT"

        return {
            "overall_status": overall_status,
            "screening_title": "Compliance Screening Result",
            "legal_disclaimer": "This is an automated preliminary image-based compliance screening result and does not guarantee absolute legal compliance under the Legal Metrology Act, 2009.",
            "category": final_category,
            "category_inferred": not is_user_specified,
            "regulation": regulation or "Legal Metrology & Applicable Statutory Regulations",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_rules": total_rules,
                "passed": passed_count,
                "failed": failed_count,
                "needs_review": review_count
            },
            "results": results
        }

Tuple_Cat = tuple[str, bool]
