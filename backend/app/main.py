"""
main.py - METRIX-LM FastAPI Application Entry Point & Multi-Role Seeder
"""

# ============================================================================
# SUPPRESS PADDLE / PADDLEOCR TELEMETRY & SIGNAL HANDLERS
# Must be set BEFORE any paddle* import to prevent outbound TCP connections
# to Google servers (172.217.x.x / translate.googleapis.com) that cause
# "wsarecv: An established connection was aborted" errors on Windows.
# ============================================================================
import os
os.environ.setdefault("PADDLE_DISABLE_SIGNAL_HANDLER", "1")   # No signal hijacking
os.environ.setdefault("PADDLE_NO_GLOBAL_PROGRESS", "1")        # Suppress download bars
os.environ.setdefault("PADDLEX_DISABLE_CE_REPORT", "1")        # Disable PaddleX telemetry
os.environ.setdefault("PADDLEX_CE_DISABLE", "1")               # Alternate flag
os.environ.setdefault("FLAGS_call_stack_level", "0")           # Suppress C++ stack output
os.environ.setdefault("GLOG_minloglevel", "3")                 # Silence PaddlePaddle GLOG
os.environ.setdefault("FLAGS_use_mkldnn", "0")                 # Avoid MKLDNN hang on Windows
os.environ.setdefault("NO_PROXY", "translate.googleapis.com,*.google.com")
os.environ.setdefault("no_proxy", "translate.googleapis.com,*.google.com")
# Block deep_translator / TranslationMiddleware from making outbound calls
os.environ.setdefault("METRIX_DISABLE_TRANSLATION", "1")

from contextlib import asynccontextmanager
from fastapi import FastAPI  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import User, ComplianceRuleDB, ScanSession
from app.auth import get_password_hash

from app.api.auth_routes import router as auth_router
from app.api.admin_routes import router as admin_router
from app.api.inspection_routes import router as inspection_router
from app.api.report_routes import router as report_router
from app.api.analytics_routes import router as analytics_router
from app.api.ocr_routes import router as ocr_router
from app.api.detection_routes import router as detection_router
from app.api.scanner_routes import router as scanner_router
from app.api.ws_routes import router as ws_router

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Seed 3 User Accounts for 3 Distinct RBAC Roles
    users_to_seed = [
        {
            "id": "ADM-2026",
            "name": "System Administrator",
            "email": "admin@legalmetrology.gov.in",
            "password": "AdminPass2026!",
            "designation": "System & Legal Rule Administrator",
            "zone_office": "Central Ministry HQ, New Delhi",
            "role": "admin"
        },
        {
            "id": "INS-2026",
            "name": "Field Inspector",
            "email": "inspector@legalmetrology.gov.in",
            "password": "InspectorPass2026!",
            "designation": "Field Enforcement Inspector",
            "zone_office": "Northern Zonal Enforcement Office",
            "role": "inspector"
        },
        {
            "id": "OFF-2026",
            "name": "Reviewing Senior Officer",
            "email": "officer.test@legalmetrology.gov.in",
            "password": "OfficialTestPass123!",
            "designation": "Senior Legal Metrology Officer",
            "zone_office": "Central Ministry HQ, New Delhi",
            "role": "reviewing_officer"
        },
        {
            "id": "OFF-2026-ALIAS",
            "name": "Reviewing Officer Lead",
            "email": "officer@legalmetrology.gov.in",
            "password": "OfficialTestPass123!",
            "designation": "Adjudication Lead Officer",
            "zone_office": "Central Ministry HQ, New Delhi",
            "role": "reviewing_officer"
        }
    ]

    for u_info in users_to_seed:
        existing = db.query(User).filter(User.email == u_info["email"]).first()
        if existing:
            existing.name = u_info["name"]
            existing.hashed_password = get_password_hash(u_info["password"])
            existing.designation = u_info["designation"]
            existing.zone_office = u_info["zone_office"]
            existing.role = u_info["role"]
            db.commit()
        else:
            new_u = User(
                id=u_info["id"],
                name=u_info["name"],
                email=u_info["email"],
                hashed_password=get_password_hash(u_info["password"]),
                designation=u_info["designation"],
                zone_office=u_info["zone_office"],
                role=u_info["role"]
            )
            db.add(new_u)
            db.commit()

    # Migrate & Seed Dynamic Statutory Rules Dataset
    from app.rules.migrate_db import migrate_database_schema
    from app.rules.dataset_seeder import seed_rules_from_dataset
    migrate_database_schema()
    seed_rules_from_dataset(db=db, force_reload=False)

    db.close()

    from app.ocr.pipeline import MetrixOCRPipeline
    print("[STARTUP] Pre-warming OCR/YOLO pipeline...")
    MetrixOCRPipeline.get_instance()
    print("[STARTUP] OCR/YOLO pipeline ready.")

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Serve cropped and annotated package images at /results/
app.mount("/results", StaticFiles(directory=RESULTS_DIR), name="results")

# CORS Middleware for React Web & Mobile App Integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|172\.\d+\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(inspection_router, prefix=settings.API_V1_STR)
app.include_router(report_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(scanner_router, prefix=settings.API_V1_STR)

# Direct /api route aliases for statutory report & inspection endpoints
app.include_router(inspection_router, prefix="/api")
app.include_router(report_router, prefix="/api")
app.include_router(ocr_router)
app.include_router(detection_router)
app.include_router(scanner_router)
app.include_router(ws_router)

from app.api.ws_manager import ws_manager
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/notifications")
async def direct_ws_notifications(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        await ws_manager.disconnect(websocket)

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
