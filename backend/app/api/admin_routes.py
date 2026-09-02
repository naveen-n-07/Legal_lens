"""
admin_routes.py - System Administration, User Management & Compliance Rule Matrix Gateway
"""

from typing import List, Optional, Dict, Any, Union
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
