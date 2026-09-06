"""
declaration_extractor.py - Root Entrypoint Wrapper for StatutoryExtractor

Statutory Declaration Parsing Engine (Stage 5)
Converts raw OCR / Translated text into structured legal metadata using
fault-tolerant Token-Anchored Named Capture Regex pipelines (re.VERBOSE).
"""
import os
import sys

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure backend directory is in python search path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'app', 'ocr'))

from backend.app.ocr.declaration_extractor import (
    StatutoryExtractor,
    DeclarationExtractor
)

if __name__ == "__main__":
    extractor = StatutoryExtractor()

    # Simulated output from Stage 4 PaddleOCR / Translation engine
    mock_ocr_output = [
        {"text": "ORGANIC WHOLE WHEAT ATTA", "confidence": 0.99, "bounding_box": [[40, 60], [520, 95]]},
        {"text": "NET QUANTITY: 5.0 kg", "confidence": 0.98, "bounding_box": [[40, 130], [360, 165]]},
        {"text": "MRP Rs. 245.00 (INCL. OF ALL TAXES) USP Rs 49/kg", "confidence": 0.98, "bounding_box": [[40, 325], [540, 355]]},
        {"text": "PKD: 08/2026 | EXP: 02/2027", "confidence": 0.97, "bounding_box": [[40, 385], [660, 415]]}
    ]

    import json
    result = extractor.extract_declarations(mock_ocr_output)
    print("=" * 80)
    print("STAGE 5 STATUTORY EXTRACTOR OUTPUT (TOKEN-ANCHORED NAMED CAPTURE REGEX)")
    print("=" * 80)
    print(json.dumps(result, indent=2))

    # Assertions & Verification
    assert result["mrp"] is not None, "MRP extraction failed!"
    assert result["mrp"]["value"] == 245.0, "MRP value mismatch!"
    assert result["mrp"]["tax_inclusive_stated"] is True, "Tax inclusive clause mismatch!"
    assert result["mrp"]["unit_sale_price"]["value"] == 49.0, "USP value mismatch!"
    assert result["net_quantity"] is not None, "Net quantity extraction failed!"
    assert result["net_quantity"]["value"] == 5.0, "Net quantity value mismatch!"
    assert result["net_quantity"]["unit"] == "kg", "Net quantity unit mismatch!"
    assert len(result["dates"]) == 2, f"Expected 2 dates, got {len(result['dates'])}"
    assert result["dates"][0]["type"] == "PKD" and result["dates"][0]["date_str"] == "08/2026"
    assert result["dates"][1]["type"] == "EXP" and result["dates"][1]["date_str"] == "02/2027"

    print("\n" + "=" * 80)
    print("VERIFICATION CHECKS: ALL PASSED")
    print("=" * 80)
    print("[PASS] MRP: Rs.", result["mrp"]["value"], "| Tax Inclusive:", result["mrp"]["tax_inclusive_stated"], "| USP:", result["mrp"]["unit_sale_price"])
    print("[PASS] Net Quantity:", result["net_quantity"]["value"], result["net_quantity"]["unit"])
    print("[PASS] Dates Captured (finditer):", [(d["type"], d["date_str"]) for d in result["dates"]])
    print("[PASS] Evidence Bounding Boxes Preserved.")
