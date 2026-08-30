"""
auth_routes.py - Authentication Controller Router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, AuditLog
from app.schemas import Token, LoginRequest, UserResponse
from app.auth import verify_password, create_access_token, get_current_user

router = APIRouter(tags=["Authentication"])

@router.post("/auth/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect government email ID or password."
        )

    access_token = create_access_token(data={"sub": user.email, "role": user.role})

    # Audit Log
    log = AuditLog(
        user_id=user.id,
        user_name=user.name,
        action="USER_LOGIN",
        details=f"User {user.email} authenticated successfully as {user.role}."
    )
    db.add(log)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_name": user.name,
        "role": user.role,
        "email": user.email
    }

@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
