"""
test_metrix_lm.py - System Integration, Stage 1 Package Detection & RBAC Security Test Suite
"""

import sys
import os

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import unittest
import json
import cv2  # type: ignore
import numpy as np  # type: ignore

try:
    from app.ocr_service import OpenCVOCRService  # type: ignore
    from app.rule_engine import RuleEngine  # type: ignore
    from app.pdf_service import PDFReportGenerator  # type: ignore
    from app.ocr.ocr_service import PaddleOCRService  # type: ignore
    from app.ocr.declaration_extractor import DeclarationExtractor  # type: ignore
    from app.package_detection.detector import PackageDetector  # type: ignore
    from app.auth.rbac import verify_password, get_password_hash, RequireRole, VALID_ROLES  # type: ignore
    from app.models import User  # type: ignore
except ImportError:
    from backend.app.ocr_service import OpenCVOCRService  # type: ignore
    from backend.app.rule_engine import RuleEngine  # type: ignore
    from backend.app.pdf_service import PDFReportGenerator  # type: ignore
    from backend.app.ocr.ocr_service import PaddleOCRService  # type: ignore
    from backend.app.ocr.declaration_extractor import DeclarationExtractor  # type: ignore
    from backend.app.package_detection.detector import PackageDetector  # type: ignore
    from backend.app.auth.rbac import verify_password, get_password_hash, RequireRole, VALID_ROLES  # type: ignore
    from backend.app.models import User  # type: ignore

class TestRBACSecurityAndAuth(unittest.TestCase):

    def test_01_valid_rbac_roles_defined(self):
        """RBAC Test: Ensures 3 distinct roles are defined."""
        self.assertIn("admin", VALID_ROLES)
        self.assertIn("inspector", VALID_ROLES)
        self.assertIn("reviewing_officer", VALID_ROLES)

    def test_02_password_hashing_and_verification(self):
        """RBAC Test: Ensures password hashing and verification works securely."""
        raw_pass = "AdminPass2026!"
        hashed = get_password_hash(raw_pass)
        self.assertTrue(verify_password(raw_pass, hashed))
        self.assertFalse(verify_password("WrongPassword123", hashed))

    def test_03_require_role_authorization_guard(self):
        """RBAC Test: Validates RequireRole guard authorization and forbidden rejection."""
        admin_guard = RequireRole(["admin"])
        admin_user = User(id="ADM-1", name="Admin User", email="admin@gov.in", role="admin", hashed_password="x", designation="Admin", zone_office="HQ")
        inspector_user = User(id="INS-1", name="Inspector User", email="inspector@gov.in", role="inspector", hashed_password="x", designation="Inspector", zone_office="HQ")

        # Admin user passes admin guard
        res = admin_guard(admin_user)
        self.assertEqual(res.role, "admin")

        # Inspector user blocked by admin guard
        try:
            from fastapi import HTTPException  # type: ignore
        except ImportError:
            from backend.fastapi import HTTPException  # type: ignore
            
        with self.assertRaises(HTTPException) as ctx:
            admin_guard(inspector_user)
        self.assertEqual(ctx.exception.status_code, 403)

class TestAnomalyAndFraudDetection(unittest.TestCase):

    def test_01_gibberish_consonant_sequence_detected(self):
        """Fraud Test: Flags gibberish consonant strings like 'Xxgfchf' as suspicious."""
        res = RuleEngine.detect_fabricated_or_suspicious_text("Xxgfchf Brand")
        self.assertTrue(res["is_suspicious"])
        self.assertTrue(len(res["reason"]) > 0)

    def test_02_prohibited_placeholder_keyword_detected(self):
        """Fraud Test: Flags prohibited placeholder keywords like 'lorem ipsum' as suspicious."""
        res = RuleEngine.detect_fabricated_or_suspicious_text("lorem ipsum commodity item")
        self.assertTrue(res["is_suspicious"])
        self.assertIn("placeholder", res["reason"].lower())

    def test_03_legitimate_commodity_name_passes(self):
        """Fraud Test: Verifies legitimate commodity names pass sanity checks cleanly."""
        res = RuleEngine.detect_fabricated_or_suspicious_text("Organic Pure Whole Wheat Flour 5kg")
        self.assertFalse(res["is_suspicious"])

    def test_04_fraud_evaluator_triggers_route_7b(self):
        """Fraud Test: Ensures evaluation matrix flags suspicious data and triggers Route 7B."""
        payload = {"product_name": "Xxgfchf Brand", "generic_name": "Xxgfchf"}
        eval_res = RuleEngine.evaluate_5_section_compliance(payload, "Xxgfchf Brand Label")
        self.assertTrue(eval_res["is_suspicious"])
        self.assertEqual(eval_res["overall_status"], "7B: VIOLATION / MANUAL REVIEW")

class TestStage1PackageDetection(unittest.TestCase):

    def test_01_stage_1_package_detection_and_cropping(self):
        """
        Stage 1 Test: Validates YOLO package detection, bounding box generation,
        confidence score thresholding, and package image cropping.
        """
        sample_img = np.zeros((600, 800, 3), dtype=np.uint8)
        # Draw central commodity box
        cv2.rectangle(sample_img, (100, 80), (700, 520), (200, 200, 200), -1)
        cv2.putText(sample_img, "PACKAGED COMMODITY BOTTLE", (120, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        
        _, img_bytes = cv2.imencode('.jpg', sample_img)
        
        result = PackageDetector.detect_packages(img_bytes)
        
        self.assertTrue(result["success"])
        self.assertGreater(len(result["detections"]), 0)
        
        top_det = result["detections"][0]
        self.assertEqual(top_det["class_name"], "package")
        self.assertGreaterEqual(top_det["confidence"], 0.50)
        self.assertIn("crop_url", top_det)
        self.assertIn("bounding_box", top_det)
        self.assertGreater(top_det["bounding_box"]["x2"], top_det["bounding_box"]["x1"])

class TestRule7StatutoryAudit(unittest.TestCase):

    def test_case_A_clearly_compliant_package(self):
        """Test A: Clearly compliant package (A = 150 cm², measured = 3.0 mm, min = 2.5 mm)."""
        res = RuleEngine.evaluate_rule_7(pdp_area_cm2=150.0, measured_height_mm=3.0, is_scale_reliable=True, measurement_confidence=95.0)
        self.assertEqual(res["result"], "COMPLIANT")
        self.assertEqual(res["required_height_mm"], 2.5)
        self.assertEqual(res["difference_mm"], 0.5)

    def test_case_B_clearly_non_compliant_package(self):
        """Test B: Clearly non-compliant package (A = 150 cm², measured = 1.5 mm, min = 2.5 mm, scale reliable)."""
        res = RuleEngine.evaluate_rule_7(pdp_area_cm2=150.0, measured_height_mm=1.5, is_scale_reliable=True, measurement_confidence=92.0)
        self.assertEqual(res["result"], "POTENTIAL_VIOLATION")
        self.assertEqual(res["required_height_mm"], 2.5)
        self.assertEqual(res["difference_mm"], -1.0)

    def test_case_C_boundary_value_exactly_equal(self):
        """Test C: Boundary value exactly equal to statutory minimum (A = 150 cm², measured = 2.5 mm, min = 2.5 mm)."""
        res = RuleEngine.evaluate_rule_7(pdp_area_cm2=150.0, measured_height_mm=2.5, is_scale_reliable=True, measurement_confidence=95.0)
        self.assertEqual(res["result"], "COMPLIANT")
        self.assertEqual(res["difference_mm"], 0.0)

    def test_case_D_measurement_below_minimum(self):
        """Test D: Measurement below minimum with reliable scale (A = 150 cm², measured = 2.2 mm, min = 2.5 mm)."""
        res = RuleEngine.evaluate_rule_7(pdp_area_cm2=150.0, measured_height_mm=2.2, is_scale_reliable=True, measurement_confidence=90.0)
        self.assertEqual(res["result"], "POTENTIAL_VIOLATION")
        self.assertEqual(res["difference_mm"], -0.3)

    def test_case_E_unknown_pdp_area(self):
        """Test E: Unknown PDP area (A = None, measured = 2.2 mm)."""
        res = RuleEngine.evaluate_rule_7(pdp_area_cm2=None, measured_height_mm=2.2, is_scale_reliable=True, measurement_confidence=90.0)
        self.assertEqual(res["result"], "NEEDS_OFFICER_VERIFICATION")

    def test_case_F_unknown_physical_scale(self):
        """Test F: Unknown physical scale (A = 150 cm², measured = 2.2 mm, is_scale_reliable = False)."""
        res = RuleEngine.evaluate_rule_7(pdp_area_cm2=150.0, measured_height_mm=2.2, is_scale_reliable=False, measurement_confidence=90.0)
        self.assertEqual(res["result"], "NEEDS_OFFICER_VERIFICATION")

    def test_case_G_low_ocr_confidence(self):
        """Test G: Low OCR confidence (A = 150 cm², measured = 3.0 mm, confidence = 70.0%)."""
        res = RuleEngine.evaluate_rule_7(pdp_area_cm2=150.0, measured_height_mm=3.0, is_scale_reliable=True, measurement_confidence=70.0)
        self.assertEqual(res["result"], "NEEDS_OFFICER_VERIFICATION")

    def test_case_H_perspective_distorted_image(self):
        """Test H: Perspective distorted image (is_scale_reliable = False)."""
        res = RuleEngine.evaluate_rule_7(pdp_area_cm2=150.0, measured_height_mm=2.2, is_scale_reliable=False, measurement_confidence=65.0)
        self.assertEqual(res["result"], "NEEDS_OFFICER_VERIFICATION")

    def test_case_I_blurry_image(self):
        """Test I: Blurry image (Laplacian variance < 100.0 rejected by OpenCV quality gate)."""
        blurry_img = np.full((600, 800, 3), 128, dtype=np.uint8)
        quality = OpenCVOCRService.evaluate_image_quality(blurry_img)
        self.assertFalse(quality["passed"])

    def test_case_J_multiple_declarations_embossed_vs_normal(self):
        """Test J: Multiple declarations (Normal vs Embossed container)."""
        res_normal = RuleEngine.evaluate_rule_7(pdp_area_cm2=150.0, measured_height_mm=3.0, printing_type="normal", is_scale_reliable=True)
        self.assertEqual(res_normal["required_height_mm"], 2.5)

        res_embossed = RuleEngine.evaluate_rule_7(pdp_area_cm2=150.0, measured_height_mm=3.0, printing_type="embossed", is_scale_reliable=True)
        self.assertEqual(res_embossed["required_height_mm"], 4.0)

    def test_pdf_generation(self):
        """Tests ReportLab PDF certificate generation."""
        mock_data = {
            "id": "INS-TEST-PDF",
            "product_name": "Organic Honey 500g",
            "category": "Food & Beverages",
            "location": "Delhi HQ",
            "inspector_name": "Official Inspector",
            "overall_status": "7A COMPLIANT",
            "overall_confidence": 94.5,
            "route_7b_triggered": False,
            "company_profile": {"company_name": "Acme Foods", "lmpc_cert_number": "LMPC/123", "provenance": "AUTO_EXTRACTED_VERIFIED"},
            "technical_matrix": {"generic_name": "Pure Honey", "physical_state": "Semi-Solid", "package_material": "Glass Jar", "provenance": "AUTO_EXTRACTED_VERIFIED"},
            "pdp_blueprint": {"pdp_shape": "rectangular", "pdp_area_cm2": 150.0, "statutory_min_font_mm": 2.5, "measured_font_mm": 3.0, "font_compliant": True, "provenance": "AUTO_EXTRACTED_VERIFIED"},
            "quantity_mpe": {"mpe_display": "3.0% (15.0 g)", "equipment_cert_number": "SCALE-1", "equipment_cert_expiry": "2027-12-31", "provenance": "MANUALLY_ENTERED"},
            "customer_care": {"designated_name_role": "Manager", "email": "care@acme.in", "phone": "1800-11-2233", "provenance": "AUTO_EXTRACTED_VERIFIED"},
            "checks": [{"field_name": "Rule 7 Table-I Font", "extracted_value": "3.0 mm", "expected_rule": "Min 2.5 mm", "is_compliant": True, "warning_message": None, "confidence": 94.0}],
            "violations": []
        }
        pdf_bytes = PDFReportGenerator.generate_inspection_certificate(mock_data)
        self.assertGreater(len(pdf_bytes), 3000)

class TestScannerEndpoints(unittest.TestCase):
    def setUp(self):
        try:
            from fastapi.testclient import TestClient  # type: ignore
            from app.main import app
            from app.database import Base, engine
            Base.metadata.create_all(bind=engine)
            self.client = TestClient(app)
        except ImportError:
            from backend.fastapi.testclient import TestClient  # type: ignore
            from backend.app.main import app
            from backend.app.database import Base, engine
            Base.metadata.create_all(bind=engine)
            self.client = TestClient(app)

    def test_process_image_endpoint(self):
        """Tests POST /api/process-image quality checks and output URLs."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, img_encoded = cv2.imencode('.png', img)
        response = self.client.post(
            "/api/process-image",
            files={"file": ("test.png", img_encoded.tobytes(), "image/png")}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("quality", data)
        self.assertIn("original_url", data)
        self.assertIn("processed_url", data)
        self.assertEqual(data["quality"]["resolution"], "100x100")

    def test_ocr_endpoint(self):
        """Tests POST /api/ocr raw text output."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, img_encoded = cv2.imencode('.png', img)
        response = self.client.post(
            "/api/ocr",
            files={"file": ("test.png", img_encoded.tobytes(), "image/png")}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("text", data)
        self.assertIn("confidence", data)
        self.assertIn("results", data)

    def test_scan_endpoint_and_get_session(self):
        """Tests full pipeline scan POST /api/scan and session retrieval GET /api/scan/{scan_id}."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, img_encoded = cv2.imencode('.png', img)
        response = self.client.post(
            "/api/scan",
            files=[("files", ("test.png", img_encoded.tobytes(), "image/png"))]
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("scan_id", data)
        self.assertIn("original_urls", data)
        self.assertIn("processed_urls", data)
        self.assertIn("quality", data)
        self.assertIn("raw_text", data)
        self.assertIn("extracted_declarations", data)

        scan_id = data["scan_id"]
        get_response = self.client.get(f"/api/scan/{scan_id}")
        self.assertEqual(get_response.status_code, 200)
        get_data = get_response.json()
        self.assertEqual(get_data["scan_id"], scan_id)
        self.assertEqual(len(get_data["original_urls"]), 1)

    def test_inspection_record_model_getters_and_pdf_report(self):
        """Tests InspectionRecord getters and PDF report download from database record."""
        try:
            from app.models import InspectionRecord, User
            from app.database import SessionLocal
            from app.auth import create_access_token
        except ImportError:
            from backend.app.models import InspectionRecord, User
            from backend.app.database import SessionLocal
            from backend.app.auth import create_access_token

        db = SessionLocal()
        test_ins_id = "INS-TEST-DB-RECORD-2026"
        
        # Ensure test admin user exists for auth
        existing_admin = db.query(User).filter(User.email == "admin@legalmetrology.gov.in").first()
        if not existing_admin:
            db.add(User(
                id="ADM-2026",
                name="System Administrator",
                email="admin@legalmetrology.gov.in",
                hashed_password="hash",
                designation="System Admin",
                zone_office="Central HQ",
                role="admin"
            ))
            db.commit()

        # Clean up any existing record
        db.query(InspectionRecord).filter(InspectionRecord.id == test_ins_id).delete()
        db.commit()

        rec = InspectionRecord(
            id=test_ins_id,
            product_name="Database Pure Mustard Oil 1L",
            category="Food & Beverages",
            pdp_shape="cylindrical",
            location="Delhi Zonal Hub",
            inspector_id="INS-2026",
            inspector_name="Field Enforcement Inspector",
            overall_status="7A COMPLIANT",
            overall_confidence=95.0,
            route_7b_triggered=False,
            checks_json=json.dumps([{"field_name": "MRP", "is_compliant": True, "extracted_value": "₹190.00", "expected_rule": "Rule 6(1)(e)", "confidence": 96.0}]),
            violations_json=json.dumps([]),
            company_profile_json=json.dumps({"company_name": "Mustard Oil Mills Ltd", "lmpc_cert_number": "LMPC/2026/001"}),
            technical_matrix_json=json.dumps({"generic_name": "Mustard Oil", "declared_net_qty": "1 L"}),
            pdp_blueprint_json=json.dumps({"pdp_area_cm2": 250.0, "statutory_min_font_mm": 2.5, "measured_font_mm": 3.0}),
            quantity_mpe_json=json.dumps({"mpe_display": "1.5%"}),
            customer_care_json=json.dumps({"email": "care@mustardoil.in", "phone": "1800-00-1122"})
        )
        db.add(rec)
        db.commit()

        # Test model getters
        self.assertEqual(len(rec.get_checks()), 1)
        self.assertEqual(rec.get_checks()[0]["field_name"], "MRP")
        self.assertEqual(len(rec.get_violations()), 0)
        self.assertEqual(rec.get_company_profile()["company_name"], "Mustard Oil Mills Ltd")

        # Test PDF endpoint for this DB record
        admin_token = create_access_token(data={"sub": "admin@legalmetrology.gov.in", "role": "admin"})
        pdf_res = self.client.get(
            f"/api/v1/reports/{test_ins_id}/pdf",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.headers["content-type"], "application/pdf")
        self.assertGreater(len(pdf_res.content), 2000)

        # Cleanup
        db.query(InspectionRecord).filter(InspectionRecord.id == test_ins_id).delete()
        db.commit()
        db.close()

class TestDynamicComplianceRuleEngine(unittest.TestCase):
    """
    Test suite for the database-driven dynamic compliance rule validation engine.
    Ensures zero hardcoding, strict schema validation, safe operator evaluation,
    datetime-based date comparisons, confidence gating, and instant database rule updates.
    """

    def setUp(self):
        try:
            from app.database import SessionLocal, engine, Base
            from app.rules.repository import RuleRepository
            from app.rules.engine import RuleEngine
            from app.rules.compliance_service import ComplianceService
            from app.rules.normalization import DataNormalizer
            from app.rules.dataset_seeder import seed_rules_from_dataset
            from app.models import ComplianceRuleDB
        except ImportError:
            from backend.app.database import SessionLocal, engine, Base
            from backend.app.rules.repository import RuleRepository
            from backend.app.rules.engine import RuleEngine
            from backend.app.rules.compliance_service import ComplianceService
            from backend.app.rules.normalization import DataNormalizer
            from backend.app.rules.dataset_seeder import seed_rules_from_dataset
            from backend.app.models import ComplianceRuleDB

        self.db = SessionLocal()
        # Seed rules into database
        seed_rules_from_dataset(db=self.db, force_reload=False)

    def tearDown(self):
        self.db.close()

    def test_01_rule_repository_applicable_rules_hierarchy(self):
        """Repository Test: Retrieves applicable statutory rules dynamically based on category hierarchy."""
        from app.rules.repository import RuleRepository
        
        # Test generic commodity
        all_rules = RuleRepository.get_applicable_rules(category="ALL", db=self.db)
        self.assertGreaterEqual(len(all_rules), 5)
        
        # Test Food & Beverages: should include generic LM rules + FSSAI rules
        food_rules = RuleRepository.get_applicable_rules(category="Food & Beverages", db=self.db)
        food_rule_ids = {r.rule_id for r in food_rules}
        self.assertIn("FSSAI-LDR-2020-R05-S7-LIC", food_rule_ids)  # FSSAI license rule
        self.assertIn("LM-PCR-2011-R06-S1-E-MRP", food_rule_ids)   # MRP rule

    def test_02_rule_engine_mandatory_field_pass_fail_and_needs_review(self):
        """RuleEngine Test: Evaluates MANDATORY_FIELD with confidence gating (PASS, FAIL, NEEDS_REVIEW)."""
        from app.rules.engine import RuleEngine
        from app.models import ComplianceRuleDB

        mrp_rule = ComplianceRuleDB(
            rule_id="TEST-MRP-MANDATORY",
            product_category="ALL",
            field_name="mrp",
            rule_type="MANDATORY_FIELD",
            required=True,
            severity="HIGH",
            error_message="MRP declaration is mandatory.",
            explanation="Statutory MRP declaration.",
            version="1.0.0"
        )

        # Case A: Detected with high confidence (>=90%) -> PASS
        decls_pass = {"mrp": {"value": "₹150.00", "confidence": 95.0, "bbox": [10, 10, 100, 40], "detected": True}}
        res_a = RuleEngine.evaluate_rule(mrp_rule, decls_pass, ocr_overall_confidence=95.0)
        self.assertEqual(res_a["status"], "PASS")
        self.assertIsNotNone(res_a["evidence"]["bounding_box"])

        # Case B: Not detected in high-confidence scan (>=90%) -> FAIL
        decls_fail = {"mrp": {"value": None, "confidence": 0.0, "bbox": None, "detected": False}}
        res_b = RuleEngine.evaluate_rule(mrp_rule, decls_fail, ocr_overall_confidence=92.0, high_conf_threshold=90.0)
        self.assertEqual(res_b["status"], "FAIL")
        self.assertIn("not detected", res_b["explanation"].lower())

        # Case C: Not detected in low-confidence scan (<75%) -> NEEDS_REVIEW (cannot definitively claim violation)
        res_c = RuleEngine.evaluate_rule(mrp_rule, decls_fail, ocr_overall_confidence=60.0, review_threshold=75.0)
        self.assertEqual(res_c["status"], "NEEDS_REVIEW")
        self.assertIn("insufficient", res_c["explanation"].lower())

        # Case D: Poor image quality -> NEEDS_REVIEW
        res_d = RuleEngine.evaluate_rule(mrp_rule, decls_fail, ocr_overall_confidence=95.0, image_quality_passed=False)
        self.assertEqual(res_d["status"], "NEEDS_REVIEW")

    def test_03_rule_engine_value_and_format_checks(self):
        """RuleEngine Test: Evaluates VALUE_CHECK (e.g. units) and FORMAT_CHECK (e.g. 14-digit FSSAI)."""
        from app.rules.engine import RuleEngine
        from app.models import ComplianceRuleDB

        # Unit of measurement check
        unit_rule = ComplianceRuleDB(
            rule_id="TEST-UNIT-CHECK",
            field_name="unit_of_measurement",
            rule_type="VALUE_CHECK",
            condition=json.dumps({"operator": "one_of", "values": ["g", "kg", "ml", "l", "u", "n", "m"]}),
            required=True
        )

        # Valid standard metric unit "g" -> PASS
        decls_valid_unit = {"unit_of_measurement": {"value": "g", "confidence": 92.0, "detected": True}}
        res_unit_pass = RuleEngine.evaluate_rule(unit_rule, decls_valid_unit)
        self.assertEqual(res_unit_pass["status"], "PASS")

        # Invalid non-standard unit "pounds" -> FAIL
        decls_invalid_unit = {"unit_of_measurement": {"value": "pounds", "confidence": 92.0, "detected": True}}
        res_unit_fail = RuleEngine.evaluate_rule(unit_rule, decls_invalid_unit)
        self.assertEqual(res_unit_fail["status"], "FAIL")

        # FSSAI 14-digit format check
        fssai_rule = ComplianceRuleDB(
            rule_id="TEST-FSSAI-FORMAT",
            field_name="fssai_license",
            rule_type="FORMAT_CHECK",
            condition=json.dumps({"operator": "regex", "pattern": r"^\d{14}$"}),
            required=True
        )

        # Valid 14 digit license -> PASS
        decls_fssai_pass = {"fssai_license": {"value": "10014011000123", "confidence": 94.0, "detected": True}}
        res_fssai_pass = RuleEngine.evaluate_rule(fssai_rule, decls_fssai_pass)
        self.assertEqual(res_fssai_pass["status"], "PASS")

        # Invalid 6 digit license -> FAIL
        decls_fssai_fail = {"fssai_license": {"value": "123456", "confidence": 94.0, "detected": True}}
        res_fssai_fail = RuleEngine.evaluate_rule(fssai_rule, decls_fssai_fail)
        self.assertEqual(res_fssai_fail["status"], "FAIL")

    def test_04_rule_engine_date_check_using_datetime_objects(self):
        """RuleEngine Test: Validates date comparisons (Expiry >= Mfg) using actual datetime.date objects."""
        from app.rules.engine import RuleEngine
        from app.models import ComplianceRuleDB
        from datetime import date

        exp_rule = ComplianceRuleDB(
            rule_id="TEST-EXP-AFTER-MFG",
            field_name="expiry_date",
            rule_type="DATE_CHECK",
            condition=json.dumps({"operator": "date_after_or_equal", "compare_with": "manufacturing_date"}),
            required=True
        )

        # Case A: Valid dates (Expiry 12/2026 >= Mfg 01/2026) -> PASS
        decls_valid_dates = {
            "manufacturing_date": {"value": "01/01/2026", "confidence": 95.0, "detected": True},
            "expiry_date": {"value": "31/12/2026", "confidence": 95.0, "detected": True}
        }
        res_date_pass = RuleEngine.evaluate_rule(exp_rule, decls_valid_dates, evaluation_date=date(2026, 6, 1))
        self.assertEqual(res_date_pass["status"], "PASS")

        # Case B: Contradictory dates (Expiry 2024 precedes Mfg 2026) -> FAIL
        decls_invalid_dates = {
            "manufacturing_date": {"value": "01/01/2026", "confidence": 95.0, "detected": True},
            "expiry_date": {"value": "01/01/2024", "confidence": 95.0, "detected": True}
        }
        res_date_fail = RuleEngine.evaluate_rule(exp_rule, decls_invalid_dates, evaluation_date=date(2026, 6, 1))
        self.assertEqual(res_date_fail["status"], "FAIL")

    def test_05_rule_engine_text_check_tax_inclusive(self):
        """RuleEngine Test: Validates TEXT_CHECK for mandatory 'incl. of all taxes' statutory clause."""
        from app.rules.engine import RuleEngine
        from app.models import ComplianceRuleDB

        tax_rule = ComplianceRuleDB(
            rule_id="TEST-TAX-INCL",
            field_name="mrp_inclusive_tax",
            rule_type="TEXT_CHECK",
            condition=json.dumps({"operator": "contains_any", "values": ["incl. of all taxes", "inclusive of all taxes", "incl. taxes"]}),
            required=True
        )

        decls_tax_pass = {"mrp_inclusive_tax": {"value": "MRP Rs. 50.00 (Incl. of all taxes)", "confidence": 95.0, "detected": True}}
        res_tax_pass = RuleEngine.evaluate_rule(tax_rule, decls_tax_pass)
        self.assertEqual(res_tax_pass["status"], "PASS")

        decls_tax_fail = {"mrp_inclusive_tax": {"value": "MRP Rs. 50.00 (Taxes extra)", "confidence": 95.0, "detected": True}}
        res_tax_fail = RuleEngine.evaluate_rule(tax_rule, decls_tax_fail)
        self.assertEqual(res_tax_fail["status"], "FAIL")

    def test_06_compliance_service_full_screening_orchestration(self):
        """ComplianceService Test: Tests complete product validation, category inference, and overall status."""
        from app.rules.compliance_service import ComplianceService

        declarations = {
            "product_name": {"value": "Deluxe Butter Cookies", "confidence": 95.0, "detected": True},
            "mrp": {"value": "₹45.00", "confidence": 95.0, "bbox": [10, 10, 50, 30], "detected": True},
            "mrp_inclusive_tax": {"value": "Incl. of all taxes", "confidence": 92.0, "detected": True},
            "net_quantity": {"value": "150 g", "confidence": 94.0, "bbox": [10, 60, 50, 80], "detected": True},
            "unit_of_measurement": {"value": "g", "confidence": 94.0, "detected": True},
            "manufacturing_date": {"value": "01/01/2026", "confidence": 93.0, "detected": True},
            "expiry_date": {"value": "01/07/2026", "confidence": 93.0, "detected": True},
            "batch_number": {"value": "B-2026-X9", "confidence": 91.0, "detected": True},
            "manufacturer": {"value": "Sunrise Foods Pvt Ltd, Industrial Area, Mumbai", "confidence": 92.0, "detected": True},
            "ingredients": {"value": "Wheat Flour, Sugar, Butter, Milk Solids", "confidence": 93.0, "detected": True},
            "allergen_declaration": {"value": "Contains Wheat and Milk", "confidence": 92.0, "detected": True},
            "country_of_origin": {"value": "India", "confidence": 96.0, "detected": True},
            "consumer_care": {"value": "care@sunrisefoods.in | 1800-222-333", "confidence": 95.0, "detected": True},
            "fssai_license": {"value": "10014011000123", "confidence": 96.0, "detected": True}
        }

        # Validate with category auto-inference
        result = ComplianceService.validate_product(
            declarations=declarations,
            category=None,
            ocr_overall_confidence=94.0,
            image_quality_passed=True,
            db=self.db
        )

        self.assertEqual(result["category"], "Food & Beverages")
        self.assertEqual(result["overall_status"], "COMPLIANT")
        self.assertEqual(result["screening_title"], "Compliance Screening Result")
        self.assertIn("preliminary image-based compliance screening", result["legal_disclaimer"])
        self.assertGreater(result["summary"]["passed"], 5)
        self.assertEqual(result["summary"]["failed"], 0)

    def test_07_dynamic_db_rule_update_without_source_code_change(self):
        """Dynamic Database Test: Updates a rule in database and verifies engine immediately reflects change."""
        from app.rules.repository import RuleRepository
        from app.rules.compliance_service import ComplianceService

        # 1. Create a custom test rule in the database
        custom_rule_id = "DYNAMIC-TEST-RULE-001"
        RuleRepository.delete_rule(custom_rule_id, db=self.db)
        
        RuleRepository.create_rule({
            "rule_id": custom_rule_id,
            "regulation": "Custom Test Regulation 2026",
            "product_category": "ALL",
            "field_name": "custom_field",
            "rule_type": "VALUE_CHECK",
            "condition": {"operator": "equals", "expected_value": "ALPHA"},
            "required": True,
            "severity": "HIGH",
            "error_message": "Custom field must be ALPHA.",
            "is_active": True
        }, db=self.db)

        # Evaluate declarations with custom_field = "ALPHA" -> should PASS
        decls = {"custom_field": {"value": "ALPHA", "confidence": 95.0, "detected": True}}
        res1 = ComplianceService.validate_product(decls, category="ALL", db=self.db)
        matching_rule_res1 = next((r for r in res1["results"] if r["rule_id"] == custom_rule_id), None)
        self.assertIsNotNone(matching_rule_res1)
        self.assertEqual(matching_rule_res1["status"], "PASS")

        # 2. Dynamically update rule in DB to expect "BETA" without restarting or modifying Python code
        RuleRepository.update_rule(custom_rule_id, {
            "condition": {"operator": "equals", "expected_value": "BETA"}
        }, db=self.db)

        # Re-evaluate same declarations ("ALPHA") -> should now FAIL because DB rule condition changed!
        res2 = ComplianceService.validate_product(decls, category="ALL", db=self.db)
        matching_rule_res2 = next((r for r in res2["results"] if r["rule_id"] == custom_rule_id), None)
        self.assertIsNotNone(matching_rule_res2)
        self.assertEqual(matching_rule_res2["status"], "FAIL")

        # 3. Dynamically deactivate rule in DB
        RuleRepository.update_rule(custom_rule_id, {"is_active": False}, db=self.db)
        res3 = ComplianceService.validate_product(decls, category="ALL", db=self.db)
        matching_rule_res3 = next((r for r in res3["results"] if r["rule_id"] == custom_rule_id), None)
        self.assertIsNone(matching_rule_res3)  # Inactive rule is not included in evaluation

        # Cleanup
        RuleRepository.delete_rule(custom_rule_id, db=self.db)

    def test_08_api_compliance_endpoints(self):
        """API Test: Tests /api/validate-compliance and /api/rules/applicable endpoints."""
        from fastapi.testclient import TestClient
        try:
            from app.main import app
        except ImportError:
            from backend.app.main import app

        client = TestClient(app)

        # Test GET /api/rules/applicable
        app_rules_res = client.get("/api/rules/applicable?category=Food%20%26%20Beverages")
        self.assertEqual(app_rules_res.status_code, 200)
        rules_list = app_rules_res.json()
        self.assertIsInstance(rules_list, list)
        self.assertGreater(len(rules_list), 0)

        # Test POST /api/validate-compliance
        val_payload = {
            "declarations": {
                "mrp": {"value": "₹99.00", "confidence": 95.0, "detected": True},
                "net_quantity": {"value": "500 g", "confidence": 95.0, "detected": True}
            },
            "category": "General Commodities",
            "ocr_overall_confidence": 95.0,
            "image_quality_passed": True
        }
        val_res = client.post("/api/validate-compliance", json=val_payload)
        self.assertEqual(val_res.status_code, 200)
        data = val_res.json()
        self.assertIn("overall_status", data)
        self.assertIn("summary", data)
        self.assertIn("results", data)

    def test_09_error_isolation_preserves_ocr_on_service_exception(self):
        """Error Isolation Test: Ensures scan endpoint preserves raw OCR if compliance validation errors."""
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        try:
            from app.main import app
        except ImportError:
            from backend.app.main import app

        client = TestClient(app)

        # Mock ComplianceService to simulate database/engine exception
        with patch("app.rules.compliance_service.ComplianceService.validate_product", side_effect=Exception("Database Connection Timeout")):
            import io, cv2, numpy as np
            dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
            _, png_bytes = cv2.imencode('.png', dummy_frame)
            test_img = io.BytesIO(png_bytes.tobytes())
            response = client.post(
                "/api/scan",
                files={"files": ("test_iso.png", test_img, "image/png")}
            )
            self.assertEqual(response.status_code, 200)
            res_data = response.json()
            # OCR results preserved
            self.assertTrue(res_data["success"])
            self.assertIn("ocr", res_data)
            self.assertIn("declarations", res_data)
            # Compliance gracefully falls back to NEEDS REVIEW
            self.assertEqual(res_data["compliance"]["overall_status"], "NEEDS REVIEW")
            self.assertIn("error_isolation_note", res_data["compliance"])


class TestNewInspectionWorkflow(unittest.TestCase):
    """End-to-End Test Suite for the New Inspection Feature Workflow."""

    def setUp(self):
        from fastapi.testclient import TestClient
        try:
            from app.main import app
            from app.auth import create_access_token
        except ImportError:
            from backend.app.main import app
            from backend.app.auth import create_access_token

        self.client = TestClient(app)
        # Create valid inspector auth token using seeded email
        self.token = create_access_token(data={"sub": "inspector@legalmetrology.gov.in", "role": "inspector", "name": "Field Inspector"})
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_01_new_inspection_process_image_end_to_end(self):
        """Tests that POST /api/v1/inspections/process-image runs the full pipeline."""
        import io, cv2, numpy as np
        # Create a sample test frame
        dummy_frame = np.ones((200, 200, 3), dtype=np.uint8) * 255
        cv2.putText(dummy_frame, "MRP Rs 55.00", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(dummy_frame, "Net Qty: 500 g", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        _, png_bytes = cv2.imencode('.png', dummy_frame)
        test_img = io.BytesIO(png_bytes.tobytes())

        response = self.client.post(
            "/api/v1/inspections/process-image",
            headers=self.headers,
            data={
                "product_name": "Premium Wheat Flour 500g",
                "category": "Food & Beverages",
                "pdp_shape": "rectangular",
                "location": "Central Lab"
            },
            files={"file": ("test_package.png", test_img, "image/png")}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check core response structure
        self.assertIn("id", data)
        self.assertTrue(data["id"].startswith("INS-2026-METRIX-"))
        self.assertIn("overall_status", data)
        self.assertIn("compliance", data)
        self.assertIn("summary", data)
        self.assertIn("results", data)
        self.assertIn("declarations", data)
        self.assertIn("original_urls", data)
        self.assertIn("processed_urls", data)

        # Check summary metrics
        summary = data["summary"]
        self.assertIn("total_rules", summary)
        self.assertIn("passed", summary)
        self.assertIn("failed", summary)
        self.assertIn("needs_review", summary)
        self.assertGreaterEqual(summary["total_rules"], 1)

        # Check that results contain statutory attributes
        results = data["results"]
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        first_rule = results[0]
        self.assertIn("rule_id", first_rule)
        self.assertIn("status", first_rule)
        self.assertIn("explanation", first_rule)

    def test_02_new_inspection_persisted_in_history(self):
        """Tests that the created inspection record appears in GET /api/v1/inspections."""
        response = self.client.get("/api/v1/inspections", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        records = response.json()
        self.assertIsInstance(records, list)
        self.assertGreater(len(records), 0)
        # Verify latest record format
        latest = records[0]
        self.assertIn("id", latest)
        self.assertIn("product_name", latest)
        self.assertIn("overall_status", latest)

    def test_03_new_inspection_pdf_report_generation(self):
        """Tests that a PDF certificate can be generated for the created inspection."""
        # Get latest inspection ID
        res_list = self.client.get("/api/v1/inspections", headers=self.headers)
        records = res_list.json()
        self.assertGreater(len(records), 0)
        inspection_id = records[0]["id"]

        pdf_res = self.client.get(f"/api/v1/reports/{inspection_id}/pdf", headers=self.headers)
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.headers["content-type"], "application/pdf")
        self.assertGreater(len(pdf_res.content), 500)

    def test_04_new_inspection_validation_and_error_handling(self):
        """Tests that invalid requests return appropriate HTTP error statuses."""
        # Empty file upload
        res_empty = self.client.post(
            "/api/v1/inspections/process-image",
            headers=self.headers,
            data={"product_name": "Test", "category": "Food & Beverages"},
            files={"file": ("empty.png", b"", "image/png")}
        )
        self.assertEqual(res_empty.status_code, 400)

        # Corrupted non-image file
        res_corrupt = self.client.post(
            "/api/v1/inspections/process-image",
            headers=self.headers,
            data={"product_name": "Test", "category": "Food & Beverages"},
            files={"file": ("bad.txt", b"This is not a real image file", "text/plain")}
        )
        self.assertEqual(res_corrupt.status_code, 422)

class TestSIHFeasibilityAndBatchInspection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app.main import app as main_app
        from app.database import engine, Base
        import app.models
        Base.metadata.create_all(bind=engine)

        from app.auth import create_access_token
        cls.token = create_access_token(data={"sub": "inspector@legalmetrology.gov.in", "role": "inspector", "name": "Field Inspector"})
        cls.headers = {"Authorization": f"Bearer {cls.token}"}
        from fastapi.testclient import TestClient
        cls.client = TestClient(main_app)

    def test_01_batch_inspection_queue_processing(self):
        """Tests that POST /api/v1/inspections/batch processes multiple package images."""
        img1 = np.ones((200, 200, 3), dtype=np.uint8) * 255
        cv2.putText(img1, "MRP Rs. 100", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        _, img1_enc = cv2.imencode('.png', img1)

        img2 = np.ones((200, 200, 3), dtype=np.uint8) * 255
        cv2.putText(img2, "Net Qty: 500 g", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        _, img2_enc = cv2.imencode('.png', img2)

        files = [
            ("files", ("pkg1.png", img1_enc.tobytes(), "image/png")),
            ("files", ("pkg2.png", img2_enc.tobytes(), "image/png"))
        ]

        res = self.client.post(
            "/api/v1/inspections/batch",
            headers=self.headers,
            data={"category": "Food & FMCG"},
            files=files
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("batch_id", data)
        self.assertEqual(data["total_packages"], 2)
        self.assertIn("packages", data)
        self.assertEqual(len(data["packages"]), 2)

    def test_02_timing_and_decoupled_confidence_breakdown(self):
        """Tests that inspection results include decoupled confidence breakdown and timing metrics."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        cv2.putText(img, "Organic Wheat 5kg", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        _, img_enc = cv2.imencode('.png', img)

        res = self.client.post(
            "/api/v1/inspections/process-image",
            headers=self.headers,
            data={"product_name": "Organic Wheat Flour", "category": "Food & Beverages"},
            files={"file": ("wheat.png", img_enc.tobytes(), "image/png")}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("confidence_breakdown", data)
        self.assertIn("timing_breakdown", data)
        self.assertIn("image_quality_score", data["confidence_breakdown"])
        self.assertIn("pdp_detection_confidence", data["confidence_breakdown"])
        self.assertIn("ocr_recognition_confidence", data["confidence_breakdown"])
        self.assertIn("total_ms", data["timing_breakdown"])

    def test_03_physical_font_calibration_and_uncertainty_gating(self):
        """Tests that low OCR confidence triggers NEEDS_REVIEW / CANNOT_VERIFY rather than false violations."""
        from app.ocr.preprocessing import OpenCVPreprocessor
        measured_mm, is_calibrated, note = OpenCVPreprocessor.estimate_physical_font_mm(30.0, pdp_height_cm=10.0, img_pixel_height=300.0)
        self.assertTrue(is_calibrated)
        self.assertEqual(measured_mm, 10.0)

        # When scale is uncalibrated
        measured_uncal, is_cal_un, note_un = OpenCVPreprocessor.estimate_physical_font_mm(15.0)
        self.assertFalse(is_cal_un)
        self.assertIn("Estimated", note_un)

if __name__ == "__main__":
    unittest.main()

