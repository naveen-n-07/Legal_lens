"""
admin_routes.py - System Administration, User Management & Compliance Rule Matrix Gateway
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from pydantic import BaseModel, EmailStr  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from app.database import get_db
from app.models import (
    User, ComplianceRuleDB, AuditLog, InspectionRecord,
    OCRResultDB, DeclarationDB, ScanSession, ImmutableAuditArchive,
    to_iso_utc
)
from app.auth import get_password_hash, require_admin, log_audit_action, VALID_ROLES

router = APIRouter(prefix="/admin", tags=["Admin: System & Rule Administration"])

class CreateUserPayload(BaseModel):
    id: Optional[str] = None
    name: str
    email: EmailStr
    password: str
    designation: str
    zone_office: str
    role: str  # admin, inspector, reviewing_officer

class UpdateUserRolePayload(BaseModel):
    role: str

class ComplianceRulePayload(BaseModel):
    rule_id: str
    regulation: Optional[str] = None
    regulation_section: Optional[str] = None
    product_category: Optional[str] = "ALL"
    field_name: Optional[str] = None
    rule_type: Optional[str] = "MANDATORY_FIELD"
    condition: Optional[Union[Dict[str, Any], str]] = None
    required: Optional[bool] = True
    severity: Optional[str] = "HIGH"
    error_message: Optional[str] = None
    explanation: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    version: Optional[str] = "1.0.0"
    source_reference: Optional[str] = None
    is_active: Optional[bool] = True

    # Legacy fields
    rule_category: Optional[str] = None
    statutory_reference: Optional[str] = None
    target_parameter: Optional[str] = None
    compliance_condition: Optional[str] = None
    violation_condition: Optional[str] = None

@router.get("/users")
def list_all_users(db: Session = Depends(get_db), current_admin: User = Depends(require_admin)):
    """
    Admin Only: List all registered system users and their active RBAC role assignments.
    """
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "designation": u.designation,
            "zone_office": u.zone_office,
            "role": u.role,
            "created_at": to_iso_utc(u.created_at)
        }
        for u in users
    ]

@router.post("/users")
def create_new_user(payload: CreateUserPayload, db: Session = Depends(get_db), current_admin: User = Depends(require_admin)):
    """
    Admin Only: Create a new system user with explicit role assignment.
    """
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{payload.role}'. Allowed roles: {', '.join(VALID_ROLES)}."
        )

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{payload.email}' already exists."
        )

    user_id = payload.id or f"USR-2026-{db.query(User).count() + 1}"
    new_user = User(
        id=user_id,
        name=payload.name,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        designation=payload.designation,
        zone_office=payload.zone_office,
        role=payload.role
    )
    db.add(new_user)
    db.commit()

    log_audit_action(db, current_admin, "CREATE_USER", resource_id=user_id, details=f"Admin created user {payload.email} with role '{payload.role}'.")
    return {"success": True, "user_id": user_id, "message": f"User {payload.email} created successfully as {payload.role}."}

@router.put("/users/{user_id}/role")
def update_user_role(user_id: str, payload: UpdateUserRolePayload, db: Session = Depends(get_db), current_admin: User = Depends(require_admin)):
    """
    Admin Only: Update role assignment for an existing user.
    """
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{payload.role}'. Allowed roles: {', '.join(VALID_ROLES)}."
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found."
        )

    old_role = target_user.role
    target_user.role = payload.role
    db.commit()

    log_audit_action(db, current_admin, "UPDATE_USER_ROLE", resource_id=user_id, details=f"Role changed for user {target_user.email} from '{old_role}' to '{payload.role}'.")
    return {"success": True, "user_id": user_id, "old_role": old_role, "new_role": payload.role}

@router.get("/rules")
def list_compliance_rules(
    category: Optional[str] = None,
    regulation: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Admin Only: List all Statutory Legal Metrology Rules and dynamic compliance rules.
    """
    from app.rules.repository import RuleRepository
    rules = RuleRepository.list_rules(category=category, regulation=regulation, db=db)
    return [r.to_dict() for r in rules]

@router.post("/rules")
def upsert_compliance_rule(
    payload: ComplianceRulePayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Admin Only: Add or update a dynamic Statutory Compliance Rule with strict schema validation.
    """
    from app.rules.repository import RuleRepository
    from app.rules.normalization import DataNormalizer

    rule_dict = payload.model_dump()
    # Normalize dates if strings
    if rule_dict.get("effective_from"):
        rule_dict["effective_from"] = DataNormalizer.parse_date_to_object(rule_dict["effective_from"])
    if rule_dict.get("effective_to"):
        rule_dict["effective_to"] = DataNormalizer.parse_date_to_object(rule_dict["effective_to"])

    existing = RuleRepository.get_rule_by_id(payload.rule_id, db=db)
    if existing:
        updated = RuleRepository.update_rule(payload.rule_id, rule_dict, db=db)
        log_audit_action(db, current_admin, "UPDATE_RULE", resource_id=payload.rule_id, details=f"Admin updated compliance rule '{payload.rule_id}'.")
        return {"success": True, "rule": updated.to_dict(), "action": "UPDATE_RULE"}
    else:
        try:
            created = RuleRepository.create_rule(rule_dict, db=db)
            log_audit_action(db, current_admin, "CREATE_RULE", resource_id=payload.rule_id, details=f"Admin created compliance rule '{payload.rule_id}'.")
            return {"success": True, "rule": created.to_dict(), "action": "CREATE_RULE"}
        except ValueError as ve:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.put("/rules/{rule_id}")
def update_compliance_rule(
    rule_id: str,
    payload: ComplianceRulePayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Admin Only: Update specific compliance rule by rule_id.
    """
    from app.rules.repository import RuleRepository
    from app.rules.normalization import DataNormalizer

    rule_dict = payload.model_dump()
    if rule_dict.get("effective_from"):
        rule_dict["effective_from"] = DataNormalizer.parse_date_to_object(rule_dict["effective_from"])
    if rule_dict.get("effective_to"):
        rule_dict["effective_to"] = DataNormalizer.parse_date_to_object(rule_dict["effective_to"])

    updated = RuleRepository.update_rule(rule_id, rule_dict, db=db)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule '{rule_id}' not found.")

    log_audit_action(db, current_admin, "UPDATE_RULE", resource_id=rule_id, details=f"Admin updated compliance rule '{rule_id}'.")
    return {"success": True, "rule": updated.to_dict()}

@router.delete("/rules/{rule_id}")
def delete_compliance_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Admin Only: Delete a compliance rule from the database.
    """
    from app.rules.repository import RuleRepository
    deleted = RuleRepository.delete_rule(rule_id, db=db)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rule '{rule_id}' not found.")

    log_audit_action(db, current_admin, "DELETE_RULE", resource_id=rule_id, details=f"Admin deleted compliance rule '{rule_id}'.")
    return {"success": True, "message": f"Rule '{rule_id}' deleted successfully."}

@router.get("/audit-logs")
def get_global_audit_logs(
    limit: int = 200,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Admin Only: View complete system global audit log stream.
    """
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_name": log.user_name,
            "action": log.action,
            "resource_id": log.resource_id,
            "details": log.details,
            "timestamp": to_iso_utc(log.timestamp)
        }
        for log in logs
    ]

@router.post("/clear-system-logs")
def clear_system_logs_and_inspections(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Admin Only: Purges all historic inspection records, audit logs, scan sessions,
    immutable audit archive, declarations, and OCR results to start completely fresh from 0.
    Preserves users, roles, and compliance rules.
    """
    db.query(InspectionRecord).delete()
    db.query(AuditLog).delete()
    db.query(OCRResultDB).delete()
    db.query(DeclarationDB).delete()
    db.query(ScanSession).delete()
    db.query(ImmutableAuditArchive).delete()
    
    init_log = AuditLog(
        user_id=current_admin.id,
        user_name=current_admin.name,
        action="SYSTEM_RESET_ZERO_BASE",
        details="System registry and audit logs cleared. System initialized from 0.",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(init_log)
    db.commit()
    
    return {
        "success": True,
        "message": "All past inspections and audit logs successfully purged. System reset to 0."
    }


# ─── Rule Engine Version Management ─────────────────────────────────────────

class RuleVersionPayload(BaseModel):
    new_version: str          # e.g. "v2.2"
    gsrn_reference: Optional[str] = None   # Gazette reference
    changelog: Optional[str] = None
    affected_rule_ids: Optional[List[str]] = None  # empty = all rules

@router.post("/rules/update-version")
def update_rule_engine_version(
    payload: RuleVersionPayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Admin Only: Bump the rule engine semantic version and optionally
    update the version tag on selected (or all) rules. Hot-reloads without
    server restart.
    """
    from app.rules.repository import RuleRepository

    target_ids = payload.affected_rule_ids
    if target_ids:
        rules = [RuleRepository.get_rule_by_id(rid, db=db) for rid in target_ids]
        rules = [r for r in rules if r is not None]
    else:
        rules = RuleRepository.list_rules(db=db)

    updated_count = 0
    for rule in rules:
        RuleRepository.update_rule(rule.rule_id, {"version": payload.new_version}, db=db)
        updated_count += 1

    changelog_summary = payload.changelog or f"Version bumped to {payload.new_version} by admin {current_admin.name}."
    log_details = (
        f"Rule engine version updated to '{payload.new_version}'. "
        f"GSR/N ref: {payload.gsrn_reference or 'N/A'}. "
        f"Rules updated: {updated_count}. "
        f"Changelog: {changelog_summary}"
    )
    log_audit_action(
        db, current_admin, "RULE_VERSION_UPDATE",
        resource_id=f"RULE_ENGINE_v{payload.new_version}",
        details=log_details
    )

    return {
        "success": True,
        "new_version": payload.new_version,
        "rules_updated": updated_count,
        "gsrn_reference": payload.gsrn_reference,
        "changelog": changelog_summary,
        "synced_at": datetime.utcnow().isoformat()
    }


# ─── Work Assignment / Dispatch Engine ───────────────────────────────────────

class WorkAssignPayload(BaseModel):
    inspection_id: str
    assign_to_user_id: str
    assignment_type: str      # "inspector_dispatch" | "officer_review"
    notes: Optional[str] = None

@router.post("/assign-work")
def assign_work(
    payload: WorkAssignPayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Admin Only: Assign an inspection to a specific inspector or reviewing officer.
    """
    from app.models import InspectionRecord
    target_user = db.query(User).filter(User.id == payload.assign_to_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User '{payload.assign_to_user_id}' not found.")

    record = db.query(InspectionRecord).filter(InspectionRecord.id == payload.inspection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Inspection '{payload.inspection_id}' not found.")

    if payload.assignment_type == "officer_review":
        record.officer_id = target_user.id
        record.officer_name = target_user.name
    elif payload.assignment_type == "inspector_dispatch":
        record.inspector_id = target_user.id
        record.inspector_name = target_user.name

    db.commit()

    log_audit_action(
        db, current_admin, "WORK_ASSIGNED",
        resource_id=payload.inspection_id,
        details=f"Inspection '{payload.inspection_id}' assigned to '{target_user.name}' ({payload.assignment_type}). Notes: {payload.notes or 'None'}."
    )
    return {
        "success": True,
        "inspection_id": payload.inspection_id,
        "assigned_to": target_user.name,
        "assignment_type": payload.assignment_type
    }


# ─── System Telemetry Summary ─────────────────────────────────────────────────

@router.get("/inspections-summary")
def get_inspections_summary(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Admin Only: Returns high-level KPI telemetry — total scans, compliance
    ratio, rule version, pending adjudications, and per-user workload.
    """
    from app.models import InspectionRecord

    records = db.query(InspectionRecord).all()
    total = len(records)
    pending = sum(1 for r in records if not r.officer_decision and (
        (r.overall_status or '').upper() in ('PENDING', '7B VIOLATION') or
        r.route_7b_triggered
    ))
    compliant = sum(1 for r in records if '7A' in (r.overall_status or '').upper() or
                    'COMPLIANT' in (r.overall_status or '').upper())
    violations = sum(1 for r in records if '7B' in (r.overall_status or '').upper() or
                     'VIOLATION' in (r.overall_status or '').upper())
    signed_off = sum(1 for r in records if r.officer_decision)

    compliance_rate = round((compliant / total * 100), 1) if total else 0.0

    # Per-inspector workload
    inspector_workload: Dict[str, Any] = {}
    for r in records:
        uid = r.inspector_id or "unknown"
        uname = r.inspector_name or uid
        if uid not in inspector_workload:
            inspector_workload[uid] = {"name": uname, "total": 0, "pending_officer_review": 0}
        inspector_workload[uid]["total"] += 1
        if not r.officer_decision:
            inspector_workload[uid]["pending_officer_review"] += 1

    # Per-officer workload
    officer_workload: Dict[str, Any] = {}
    for r in records:
        if r.officer_id:
            uid = r.officer_id
            uname = r.officer_name or uid
            if uid not in officer_workload:
                officer_workload[uid] = {"name": uname, "assigned": 0, "signed_off": 0}
            officer_workload[uid]["assigned"] += 1
            if r.officer_decision:
                officer_workload[uid]["signed_off"] += 1

    # Current rule engine version (from first active rule)
    from app.rules.repository import RuleRepository
    active_rules = RuleRepository.list_rules(db=db)
    engine_version = active_rules[0].version if active_rules else "v2.1"

    return {
        "total_scans": total,
        "pending_review": pending,
        "compliant": compliant,
        "violations": violations,
        "signed_off": signed_off,
        "compliance_rate": compliance_rate,
        "active_rule_count": len(active_rules),
        "engine_version": engine_version,
        "inspector_workload": list(inspector_workload.values()),
        "officer_workload": list(officer_workload.values()),
    }

