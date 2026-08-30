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
    from app.ocr_service import OpenCVOCRService
    from app.rule_engine import RuleEngine
    from app.pdf_service import PDFReportGenerator
    from app.ocr.ocr_service import PaddleOCRService
    from app.ocr.declaration_extractor import DeclarationExtractor
    from app.package_detection.detector import PackageDetector
    from app.auth.rbac import verify_password, get_password_hash, RequireRole, VALID_ROLES
    from app.models import User
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
            from fastapi import HTTPException
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

if __name__ == "__main__":
    unittest.main()
