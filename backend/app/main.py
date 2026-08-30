"""
main.py - METRIX-LM FastAPI Application Entry Point
"""

import json
import os
from fastapi import FastAPI  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import User, ComplianceRuleDB
from app.auth import get_password_hash

from app.api.auth_routes import router as auth_router
from app.api.inspection_routes import router as inspection_router
from app.api.report_routes import router as report_router
from app.api.analytics_routes import router as analytics_router
from app.api.ocr_routes import router as ocr_router
from app.api.detection_routes import router as detection_router

RESULTS_DIR = r"c:\SIH\backend\results"
os.makedirs(RESULTS_DIR, exist_ok=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Serve cropped and annotated package images at /results/
app.mount("/results", StaticFiles(directory=RESULTS_DIR), name="results")

# CORS Middleware for React Web & Mobile App Integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(inspection_router, prefix=settings.API_V1_STR)
app.include_router(report_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(ocr_router)
app.include_router(detection_router)

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Upsert Single Official Account: officer.test@legalmetrology.gov.in
    existing_user = db.query(User).filter(User.id == "OFF-2026").first()
    if existing_user:
        existing_user.email = "officer.test@legalmetrology.gov.in"
        existing_user.hashed_password = get_password_hash("OfficialTestPass123!")
        existing_user.name = "Official Inspector"
        existing_user.designation = "Senior Legal Metrology Officer"
        existing_user.zone_office = "Central Ministry HQ, New Delhi"
        db.commit()
    else:
        user = User(
            id="OFF-2026",
            name="Official Inspector",
            email="officer.test@legalmetrology.gov.in",
            hashed_password=get_password_hash("OfficialTestPass123!"),
            designation="Senior Legal Metrology Officer",
            zone_office="Central Ministry HQ, New Delhi",
            role="inspector"
        )
        db.add(user)
        db.commit()

    # Seed Versioned Statutory Rules Dataset (Rules 1-34 + Schedules 1-7)
    dataset_json_path = r"c:\SIH\legal_metrology_rules_2011.json"
    if os.path.exists(dataset_json_path) and db.query(ComplianceRuleDB).count() == 0:
        with open(dataset_json_path, "r", encoding="utf-8") as f:
            dataset_data = json.load(f)
            rules_list = dataset_data.get("rules", [])
            for r in rules_list:
                db_rule = ComplianceRuleDB(
                    rule_id=r["rule_id"],
                    rule_category=r["chapter"],
                    statutory_reference=f"Rule {r['rule_number']} - Legal Metrology (Packaged Commodities) Rules, 2011",
                    target_parameter=r["title"],
                    compliance_condition=r["text_verbatim"],
                    violation_condition=f"Violation of {r['title']}"
                )
                db.add(db_rule)
            db.commit()

    db.close()

@app.get("/")
def root():
    return {
        "system": settings.PROJECT_NAME,
        "version": "1.0.0",
        "stage_1_endpoint": "/api/detect-package",
        "docs": "/docs",
        "status": "ONLINE",
        "message": "METRIX-LM AI Statutory Inspection System Backend REST API Gateway"
    }
