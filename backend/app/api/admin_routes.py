"""
admin_routes.py - System Administration, User Management & Compliance Rule Matrix Gateway
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from pydantic import BaseModel, EmailStr  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from app.database import get_db
from app.models import User, ComplianceRuleDB, AuditLog
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
    rule_category: str
    statutory_reference: str
    target_parameter: str
    compliance_condition: str
    violation_condition: str
    is_active: bool = True

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
            "created_at": u.created_at
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
def list_compliance_rules(db: Session = Depends(get_db), current_admin: User = Depends(require_admin)):
    """
    Admin Only: List all 34 Statutory Legal Metrology Rules and Schedules.
    """
    rules = db.query(ComplianceRuleDB).all()
    return [
        {
            "rule_id": r.rule_id,
            "rule_category": r.rule_category,
            "statutory_reference": r.statutory_reference,
            "target_parameter": r.target_parameter,
            "compliance_condition": r.compliance_condition,
            "violation_condition": r.violation_condition,
            "is_active": r.is_active
        }
        for r in rules
    ]

@router.post("/rules")
def upsert_compliance_rule(payload: ComplianceRulePayload, db: Session = Depends(get_db), current_admin: User = Depends(require_admin)):
    """
    Admin Only: Add or update a Legal Metrology Compliance Rule.
    """
    existing = db.query(ComplianceRuleDB).filter(ComplianceRuleDB.rule_id == payload.rule_id).first()
    if existing:
        existing.rule_category = payload.rule_category
        existing.statutory_reference = payload.statutory_reference
        existing.target_parameter = payload.target_parameter
        existing.compliance_condition = payload.compliance_condition
        existing.violation_condition = payload.violation_condition
        existing.is_active = payload.is_active
        action_name = "UPDATE_RULE"
    else:
        new_rule = ComplianceRuleDB(
            rule_id=payload.rule_id,
            rule_category=payload.rule_category,
            statutory_reference=payload.statutory_reference,
            target_parameter=payload.target_parameter,
            compliance_condition=payload.compliance_condition,
            violation_condition=payload.violation_condition,
            is_active=payload.is_active
        )
        db.add(new_rule)
        action_name = "CREATE_RULE"

    db.commit()
    log_audit_action(db, current_admin, action_name, resource_id=payload.rule_id, details=f"Admin modified compliance rule '{payload.rule_id}'.")
    return {"success": True, "rule_id": payload.rule_id, "action": action_name}

@router.get("/audit-logs")
def get_global_audit_logs(db: Session = Depends(get_db), current_admin: User = Depends(require_admin)):
    """
    Admin Only: View complete system global audit log stream.
    """
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_name": log.user_name,
            "action": log.action,
            "resource_id": log.resource_id,
            "details": log.details,
            "timestamp": log.timestamp
        }
        for log in logs
    ]
