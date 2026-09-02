"""
ocr_routes.py - PaddleOCR REST API Endpoint Gateway (POST /ocr/process)
"""

import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from app.database import get_db
from app.models import OCRResultDB, DeclarationDB
from app.ocr.ocr_service import PaddleOCRService
from app.ocr.schemas import OCRProcessResponse

router = APIRouter(prefix="", tags=["OCR Engine"])

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

@router.post("/ocr/process", response_model=OCRProcessResponse)
@router.post("/api/v1/ocr/process", response_model=OCRProcessResponse)
async def process_ocr_image(
    file: UploadFile = File(...),
    inspection_id: str = "INS-TEST-2026",
    db: Session = Depends(get_db)
):
    # 1. Validate File Extension
    filename = file.filename or "upload.jpg"
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Allowed formats: JPG, JPEG, PNG, WEBP."
        )

    # 2. Validate File Size
    image_bytes = await file.read()
    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum limit of 25MB (received {len(image_bytes)/(1024*1024):.2f}MB)."
        )

    try:
        # 3. OpenCV Preprocessing & Multi-Pass OCR Extraction
        ocr_output = PaddleOCRService.process_image(image_bytes, filename=filename)
        
        if not ocr_output.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ocr_output.get("error", {}).get("message", "OCR processing failed.")
            )

        full_text = ocr_output["full_text"]
        results = ocr_output["results"]
        declarations = ocr_output["declarations"]
        overall_conf = ocr_output["overall_confidence"]

        # 4. Store OCR Results in Database (ocr_results table)
        for res in results:
            db_ocr = OCRResultDB(
                inspection_id=inspection_id,
                image_id=filename,
                full_text=full_text,
                detected_text=res["text"],
                confidence=res["confidence"],
                bounding_box=json.dumps(res["bbox"])
            )
            db.add(db_ocr)
        
        # 5. Store Extracted Declarations in Database (declarations table)
        for field_name, field_data in declarations.items():
            field_val = field_data.get("value") if isinstance(field_data, dict) else field_data
            field_conf = field_data.get("confidence", overall_conf) if isinstance(field_data, dict) else overall_conf
            if field_val:
                db_decl = DeclarationDB(
                    inspection_id=inspection_id,
                    field_name=field_name,
                    field_value=str(field_val),
                    confidence=field_conf,
                    source_ocr_id=filename
                )
                db.add(db_decl)

        db.commit()

        return OCRProcessResponse(
            success=True,
            full_text=full_text,
            overall_confidence=overall_conf,
            low_confidence_warning=ocr_output.get("low_confidence_warning"),
            results=results,
            extracted_declarations=declarations,
            ocr=ocr_output.get("ocr")
        )

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR Processing engine encountered an error: {str(e)}"
        )
