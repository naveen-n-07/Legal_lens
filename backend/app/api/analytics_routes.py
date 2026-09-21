"""
analytics_routes.py - Analytics & Dashboard Telemetry Router
"""

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import InspectionRecord
from app.schemas import AnalyticsResponse

router = APIRouter(tags=["Analytics"])

@router.get("/analytics/overview", response_model=AnalyticsResponse)
@router.get("/dashboard/analytics", response_model=AnalyticsResponse)
def get_analytics(
    db: Session = Depends(get_db)
):
    total = db.query(InspectionRecord).count()
    compliant = db.query(InspectionRecord).filter(InspectionRecord.overall_status.like("%7A%")).count()
    violation_count = db.query(InspectionRecord).filter(InspectionRecord.overall_status.like("%7B%")).count()
    pending = db.query(InspectionRecord).filter(InspectionRecord.overall_status == "PENDING").count()
    route_7b_triggers = db.query(InspectionRecord).filter(InspectionRecord.route_7b_triggered == True).count()

    # Signed Section 36 reports: records where officer sign-off decision is recorded
    signed_reports = db.query(InspectionRecord).filter(InspectionRecord.officer_decision.isnot(None)).count()

    # Pending reviews queue: items flagged or pending that have not yet been signed off by an officer
    pending_queue = db.query(InspectionRecord).filter(
        (InspectionRecord.overall_status == "PENDING") |
        (InspectionRecord.route_7b_triggered == True) |
        (InspectionRecord.overall_status.like("%7B%"))
    ).filter(InspectionRecord.officer_decision.is_(None)).count()

    comp_rate = (compliant / max(total, 1)) * 100.0

    # Build category and violation breakdowns strictly from the database.
    category_breakdown = {}
    top_violations_map = {}
    records = db.query(InspectionRecord).all()
    for rec in records:
        cat = rec.category or "Uncategorized"
        category_breakdown[cat] = category_breakdown.get(cat, 0) + 1

        rec_violations = rec.get_violations()
        for v in rec_violations:
            rid = v.get("rule_id") or "UNKNOWN"
            name = v.get("target_parameter") or v.get("detected_issue") or rid
            top_violations_map.setdefault(rid, {"rule_id": rid, "name": name, "title": name, "count": 0})
            top_violations_map[rid]["count"] += 1

    top_violations = sorted(
        top_violations_map.values(), key=lambda x: x["count"], reverse=True
    )[:5]

    return {
        "total_inspections": total,
        "compliant_count": compliant,
        "violation_count": violation_count,
        "pending_review_count": pending_queue if pending_queue > 0 else pending,
        "compliance_rate_percent": round(comp_rate, 1),
        "route_7b_trigger_count": route_7b_triggers,
        "signed_reports_count": signed_reports,
        "category_breakdown": category_breakdown,
        "top_violations": top_violations
    }
