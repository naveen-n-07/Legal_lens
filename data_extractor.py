"""
data_extractor.py - Root Entrypoint Wrapper for StatutoryDataExtractor

Enterprise-grade regex and heuristic extraction pipeline designed for SIH 26034.
Processes translated OCR output dictionaries and deterministically extracts mandatory
Legal Metrology (Packaged Commodities) Rules, 2011 declarations.
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

from backend.app.ocr.data_extractor import (
    StatutoryDataExtractor,
    DataExtractor,
    StatutoryRegexPatterns,
    ExtractionComplianceReport,
    MRPDeclaration,
    NetQuantityDeclaration,
    DateDeclaration,
    CustomerCareDeclaration,
    EvidenceMeta
)

if __name__ == "__main__":
    import json

    print("=" * 80)
    print("[METRIX-LM] STAGE 5: STATUTORY DATA EXTRACTOR BENCHMARK (SIH 26034)")
    print("=" * 80)

    mock_translated_detections = [
        {
            "translated_text": "Nestle Everyday Dairy Whitener",
            "original_text": "नेस्ले एवरीडे डेयरी व्हाइटनर",
            "confidence": 0.985,
            "bounding_box": [[45, 30], [550, 30], [550, 75], [45, 75]]
        },
        {
            "translated_text": "Net Weight : 1.0 kg (High Quality Standard Pack)",
            "original_text": "மொத்த எடை : 1.0 கிலோகிராம் (உயர்தர கோதுமை மாவு)",
            "confidence": 0.978,
            "bounding_box": [[45, 95], [620, 95], [620, 135], [45, 135]]
        },
        {
            "translated_text": "Maximum Retail Price : ₹245.50 (Inclusive of all taxes)",
            "original_text": "அதிகபட்ச சில்லறை விலை : ₹௨௪௫.௫௦ (வரிகள் உட்பட)",
            "confidence": 0.992,
            "bounding_box": [[45, 155], [710, 155], [710, 195], [45, 195]]
        },
        {
            "translated_text": "Date of Mfg : 24/08/2026",
            "original_text": "उत्पादन तिथि : २४/०८/२०२६",
            "confidence": 0.981,
            "bounding_box": [[45, 215], [420, 215], [420, 250], [45, 250]]
        },
        {
            "translated_text": "Expiry Date : 25/02/2027 (Best Before 6 Months From PKD)",
            "original_text": "उपयोग समाप्ति : २५/०२/२०२७",
            "confidence": 0.969,
            "bounding_box": [[45, 270], [680, 270], [680, 310], [45, 310]]
        },
        {
            "translated_text": "Customer Care Helpline : 1800-120-4567 | care@nestle.in",
            "original_text": "ग्राहक सेवा : 1800-120-4567 | care@nestle.in",
            "confidence": 0.995,
            "bounding_box": [[45, 330], [750, 330], [750, 370], [45, 370]]
        },
        {
            "translated_text": "FSSAI Lic No: 10014022002654",
            "original_text": "एफएसएसएआई लाइसेंस: 10014022002654",
            "confidence": 0.988,
            "bounding_box": [[45, 390], [460, 390], [460, 425], [45, 425]]
        },
        {
            "translated_text": "Country of Origin : India",
            "original_text": "मूल देश : भारत",
            "confidence": 0.994,
            "bounding_box": [[45, 445], [380, 445], [380, 480], [45, 480]]
        },
        {
            "translated_text": "Unit Sale Price: ₹ 0.25 / g",
            "original_text": "इकाई विक्रय मूल्य: ₹ ०.२५ / ग्राम",
            "confidence": 0.975,
            "bounding_box": [[45, 500], [390, 500], [390, 535], [45, 535]]
        },
        {
            "translated_text": "Manufactured by: Nestle India Limited, Industrial Area, Solan, H.P.",
            "original_text": "निर्माता: नेस्ले इंडिया लिमिटेड",
            "confidence": 0.962,
            "bounding_box": [[45, 555], [780, 555], [780, 595], [45, 595]]
        }
    ]

    print("[*] Initializing StatutoryDataExtractor...")
    extractor = StatutoryDataExtractor(confidence_threshold=0.50)

    print(f"[*] Input Batch: {len(mock_translated_detections)} translated OCR lines with bounding boxes")
    print("-" * 80)

    report = extractor.extract_all(mock_translated_detections)
    report_dict = report.to_dict()

    print("\n" + "=" * 80)
    print("STAGE 5 EXTRACTED STATUTORY COMPLIANCE SCHEMA (STRUCTURED JSON)")
    print("=" * 80)
    print(json.dumps(report_dict, indent=2, ensure_ascii=False))

    # Assertions & Verification
    print("\n" + "=" * 80)
    print("STATUTORY EXTRACTION VERIFICATION CHECKS")
    print("=" * 80)

    # 1. MRP Verification
    assert report.mrp.detected, "TEST FAILED: MRP was not detected!"
    assert report.mrp.value == 245.50, f"TEST FAILED: Expected 245.50, got {report.mrp.value}"
    assert report.mrp.is_inclusive_of_taxes, "TEST FAILED: Tax inclusion was not identified!"
    assert report.mrp.evidence is not None, "TEST FAILED: Bounding box evidence missing for MRP!"
    print(f"[PASS] MRP Extracted: ₹ {report.mrp.value:.2f} (Taxes Included: {report.mrp.is_inclusive_of_taxes})")
    print(f"       Bounding Box: {report.mrp.evidence.bbox_xyxy} | Conf: {report.mrp.evidence.confidence}")

    # 2. Net Quantity Verification
    assert report.net_quantity.detected, "TEST FAILED: Net Quantity not detected!"
    assert report.net_quantity.value == 1.0, f"TEST FAILED: Expected 1.0, got {report.net_quantity.value}"
    assert report.net_quantity.standardized_unit == "kg", f"TEST FAILED: Unit mismatch: {report.net_quantity.standardized_unit}"
    assert report.net_quantity.base_value == 1000.0, f"TEST FAILED: Base value conversion: {report.net_quantity.base_value}"
    assert report.net_quantity.base_unit == "g", f"TEST FAILED: Base unit mismatch: {report.net_quantity.base_unit}"
    print(f"[PASS] Net Quantity Extracted: {report.net_quantity.formatted} -> SI Base: {report.net_quantity.base_value} {report.net_quantity.base_unit}")
    print(f"       Bounding Box: {report.net_quantity.evidence.bbox_xyxy} | Conf: {report.net_quantity.evidence.confidence}")

    # 3. Date Verification
    assert report.manufacturing_date.detected, "TEST FAILED: Manufacturing date not detected!"
    assert report.manufacturing_date.iso_date == "2026-08-24", f"TEST FAILED: MFD format mismatch: {report.manufacturing_date.iso_date}"
    assert report.expiry_date.detected, "TEST FAILED: Expiry date not detected!"
    print(f"[PASS] Manufacturing Date: {report.manufacturing_date.iso_date} (Year: {report.manufacturing_date.year}, Month: {report.manufacturing_date.month})")
    print(f"[PASS] Expiry Date:        {report.expiry_date.iso_date or report.expiry_date.relative_statement}")

    # 4. Customer Care Verification
    assert report.customer_care.detected, "TEST FAILED: Customer Care not detected!"
    assert len(report.customer_care.phones) > 0, "TEST FAILED: Customer phone missing!"
    assert len(report.customer_care.emails) > 0, "TEST FAILED: Customer email missing!"
    print(f"[PASS] Customer Care Phones: {[p.number for p in report.customer_care.phones]}")
    print(f"[PASS] Customer Care Emails: {[e.email for e in report.customer_care.emails]}")

    # 5. Additional Fields Verification
    assert report.additional_fields.fssai_license is not None, "TEST FAILED: FSSAI License missing!"
    assert report.additional_fields.country_of_origin is not None, "TEST FAILED: Country of Origin missing!"
    assert report.additional_fields.unit_sale_price is not None, "TEST FAILED: Unit Sale Price missing!"
    print(f"[PASS] FSSAI License:    {report.additional_fields.fssai_license['license_number']}")
    print(f"[PASS] Country of Origin:{report.additional_fields.country_of_origin['country']}")
    print(f"[PASS] Unit Sale Price:  {report.additional_fields.unit_sale_price['formatted']}")

    # 6. Overall Compliance Summary Verification
    assert report.summary["is_fully_compliant"], "TEST FAILED: Summary marked non-compliant!"
    print(f"[PASS] Compliance Score: {report.summary['mandatory_fields_detected']}/5 Mandatory Declarations Verified.")

    print("\n[+] All Stage 5 Data Extractor requirements successfully verified.")
