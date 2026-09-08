"""
pdf_generator.py - Statutory Audit PDF Report & Legal Notice Generator (Stage 11)
Built strictly with fpdf2 for SIH 26034 (METRIX-LM).

Generates an official Statutory Audit PDF Report & Legal Notice under:
- Section 36, Legal Metrology Act, 2009
- Legal Metrology (Packaged Commodities) Rules, 2011 (Rules 6, 7, 12 & Fourth Schedule MPE)

Stateless architecture:
- Embeds OpenCV annotated evidence images directly from memory (io.BytesIO).
- Generates and returns PDF byte stream without temporary disk writes.
- Sanitizes all text to prevent Unicode/Latin-1 encoding crashes.
"""

import io
import os
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
import numpy as np  # type: ignore
import cv2  # type: ignore
from fpdf import FPDF  # type: ignore

from app.utils.visualizer import EvidenceVisualizer

logger = logging.getLogger("metrix_pdf")


def sanitize_text(text: Any) -> str:
    """
    Sanitizes text strings to prevent fpdf2 UnicodeEncodeError on standard Latin-1 core fonts.
    Replaces Indian Rupee symbol, Unicode checkmarks, bullet points, smart quotes, etc.
    """
    if text is None:
        return "N/A"
    s = str(text)

    # Unicode glyph mappings to standard ASCII / Latin-1
    replacements = [
        ("\u20b9", "Rs. "),     # Indian Rupee symbol ₹
        ("₹", "Rs. "),
        ("✅", "[PASS] "),
        ("❌", "[FAIL] "),
        ("⚠️", "[REVIEW] "),
        ("⚠", "[REVIEW] "),
        ("🟢", "[PASS] "),
        ("🔴", "[FAIL] "),
        ("🟡", "[REVIEW] "),
        ("•", "- "),
        ("–", "-"),             # en-dash
        ("—", "--"),            # em-dash
        ("“", '"'),             # smart quotes
        ("”", '"'),
        ("‘", "'"),
        ("’", "'"),
        ("\u00a0", " "),        # non-breaking space
        ("\t", "    "),
    ]
    for old, new in replacements:
        s = s.replace(old, new)

    # Encode to latin-1 with character replacement fallback
    try:
        s.encode("latin-1")
    except UnicodeEncodeError:
        # Strip any unencodable characters
        s = s.encode("latin-1", errors="replace").decode("latin-1")

    return s.strip()


class StatutoryPDF(FPDF):
    """Custom FPDF2 subclass with official Legal Metrology header & footer."""

    def __init__(self, inspection_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inspection_id = sanitize_text(inspection_id)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        # We render our elaborate multi-line statutory header on page 1 manually
        # On subsequent pages, render a compact running header
        if self.page_no() > 1:
            self.set_font("helvetica", "I", 8)
            self.set_text_color(100, 116, 139)
            self.cell(0, 6, f"METRIX-LM Statutory Inspection Report | ID: {self.inspection_id}", align="L")
            self.ln(8)
            self.set_draw_color(226, 232, 240)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(120, 130, 145)
        
        # Left: Statutory Act notice
        self.cell(105, 8, "Official Record under Sec 36, Legal Metrology Act, 2009 | Confidentially Handled", align="L")
        # Right: Page count
        self.cell(0, 8, f"Page {self.page_no()} of {{nb}}", align="R")


class StatutoryPDFGenerator:
    """
    Statutory Audit PDF Report & Legal Notice Generator.
    Produces high-fidelity, legally formatted audit documents for enforcement officers.
    """

    @classmethod
    def generate(
        cls,
        inspection_data: Dict[str, Any],
        annotated_image: Optional[Union[np.ndarray, str, bytes]] = None,
        raw_image: Optional[np.ndarray] = None
    ) -> bytes:
        """
        Generates a complete, ready-to-download Statutory PDF byte stream.
        
        Args:
            inspection_data: Dict containing inspection metadata, checks, declarations, and scores.
            annotated_image: Optional pre-annotated image (numpy array, Base64 data URL, or bytes).
            raw_image: Optional raw numpy array to annotate on-the-fly with EvidenceVisualizer.
        
        Returns:
            bytes: Valid PDF file stream.
        """
        inspection_id = str(inspection_data.get("id") or inspection_data.get("inspection_id") or "INS-2026-METRIX")
        pdf = StatutoryPDF(inspection_id=inspection_id, orientation="P", unit="mm", format="A4")
        pdf.alias_nb_pages()
        pdf.add_page()

        # 1. Official Government Emblem & Ministry Header
        cls._render_ministry_header(pdf, inspection_data)

        # 2. Executive Summary & Compliance Score Matrix
        cls._render_executive_summary(pdf, inspection_data)

        # 3. Visual Evidence: Embedded Annotated Bounding Box Image
        cls._render_visual_evidence(pdf, inspection_data, annotated_image, raw_image)

        # 4. Statutory Declarations & Audit Table
        cls._render_audit_table(pdf, inspection_data)

        # 5. Dynamic Section 4 (Clearance / Show-Cause / Provisional Memorandum) & Digital Seals
        cls._render_legal_notice_and_signatures(pdf, inspection_data)

        # Output in-memory bytes
        pdf_bytes = bytes(pdf.output())
        logger.info(f"[PDF] Generated Statutory Audit PDF for {inspection_id} ({len(pdf_bytes)} bytes)")
        return pdf_bytes

    @classmethod
    def _render_ministry_header(cls, pdf: StatutoryPDF, data: Dict[str, Any]):
        """Renders formal Ministry of Consumer Affairs masthead and metadata block."""
        page_w = pdf.w - pdf.l_margin - pdf.r_margin

        # Government of India Banner
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 5, sanitize_text("GOVERNMENT OF INDIA"), align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("helvetica", "B", 13)
        pdf.set_text_color(185, 28, 28)  # Deep statutory crimson
        pdf.cell(0, 6, sanitize_text("MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION"), align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 5, sanitize_text("DEPARTMENT OF CONSUMER AFFAIRS - LEGAL METROLOGY DIVISION"), align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(0, 4.5, sanitize_text("STATUTORY COMPLIANCE INSPECTION AUDIT REPORT & NOTICE"), align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 4, sanitize_text("[ Issued under Section 36, Legal Metrology Act, 2009 read with Legal Metrology (Packaged Commodities) Rules, 2011 ]"), align="C", new_x="LMARGIN", new_y="NEXT")

        # Dual Accent Tricolor Bar
        pdf.ln(2)
        y_bar = pdf.get_y()
        bar_w = page_w / 3.0
        pdf.set_fill_color(249, 115, 22)  # Saffron
        pdf.rect(pdf.l_margin, y_bar, bar_w, 1.2, "F")
        pdf.set_fill_color(30, 41, 59)    # Navy Blue
        pdf.rect(pdf.l_margin + bar_w, y_bar, bar_w, 1.2, "F")
        pdf.set_fill_color(34, 197, 94)   # Green
        pdf.rect(pdf.l_margin + bar_w * 2, y_bar, bar_w, 1.2, "F")
        pdf.ln(3)

        # Inspection Meta Information Block
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(pdf.l_margin, pdf.get_y(), page_w, 20, "DF")

        ins_id = str(data.get("id") or data.get("inspection_id") or "INS-2026-METRIX")
        ts = str(data.get("created_at") or data.get("evaluated_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
        loc = str(data.get("location") or "Central Ministry Enforcement Wing")
        officer = str(data.get("inspector_name") or data.get("officer_name") or "Field Enforcement Inspector")
        product = str(data.get("product_name") or "Packaged Commodity Item")
        cat = str(data.get("category") or "Food & FMCG")

        curr_y = pdf.get_y() + 2
        half_w = page_w / 2.0

        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.set_xy(pdf.l_margin + 3, curr_y)
        pdf.cell(28, 4, "INSPECTION REF:")
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(half_w - 32, 4, sanitize_text(ins_id))

        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.set_xy(pdf.l_margin + half_w + 3, curr_y)
        pdf.cell(28, 4, "COMMODITY ITEM:")
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(half_w - 32, 4, sanitize_text(product[:35]))

        curr_y += 4.5
        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.set_xy(pdf.l_margin + 3, curr_y)
        pdf.cell(28, 4, "TIMESTAMP:")
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(half_w - 32, 4, sanitize_text(ts[:22]))

        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.set_xy(pdf.l_margin + half_w + 3, curr_y)
        pdf.cell(28, 4, "CLASSIFICATION:")
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(half_w - 32, 4, sanitize_text(cat))

        curr_y += 4.5
        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.set_xy(pdf.l_margin + 3, curr_y)
        pdf.cell(28, 4, "LOCATION:")
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(half_w - 32, 4, sanitize_text(loc[:40]))

        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.set_xy(pdf.l_margin + half_w + 3, curr_y)
        pdf.cell(28, 4, "ENFORCEMENT OFF:")
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(half_w - 32, 4, sanitize_text(officer))

        pdf.set_y(curr_y + 8)

    @classmethod
    def _render_executive_summary(cls, pdf: StatutoryPDF, data: Dict[str, Any]):
        """Renders Executive Summary: Decision, Scores, MPE, and Risk Classification."""
        page_w = pdf.w - pdf.l_margin - pdf.r_margin

        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 5, sanitize_text("1. EXECUTIVE SUMMARY & STATUTORY ADJUDICATION"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        # Status resolution
        overall_stat = str(data.get("overall_status") or data.get("overall_status_legacy") or "NEEDS REVIEW").upper()
        is_compliant = "COMPLIANT" in overall_stat and "NON" not in overall_stat and "PARTIAL" not in overall_stat and "7B" not in overall_stat
        is_violation = "7B" in overall_stat or "VIOLATION" in overall_stat or "NON" in overall_stat

        if is_compliant:
            decision_text = "SECTION 7A COMPLIANT - ALL STATUTORY DECLARATIONS CONFORM"
            badge_bg = (236, 253, 245)    # Emerald-50
            badge_border = (52, 211, 153) # Emerald-400
            badge_text = (6, 95, 70)      # Emerald-800
        elif is_violation:
            decision_text = "SECTION 7B STATUTORY VIOLATION - NON-COMPLIANCE IDENTIFIED"
            badge_bg = (254, 242, 242)    # Red-50
            badge_border = (248, 113, 113)# Red-400
            badge_text = (153, 27, 27)    # Red-800
        else:
            decision_text = "PARTIALLY COMPLIANT - OFFICER VERIFICATION REQUIRED"
            badge_bg = (254, 252, 232)    # Amber-50
            badge_border = (251, 191, 36) # Amber-400
            badge_text = (146, 64, 14)    # Amber-800

        # Decision Pill Banner
        curr_y = pdf.get_y()
        pdf.set_fill_color(*badge_bg)
        pdf.set_draw_color(*badge_border)
        pdf.rect(pdf.l_margin, curr_y, page_w, 8.5, "DF")

        pdf.set_xy(pdf.l_margin + 4, curr_y + 1.8)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*badge_text)
        pdf.cell(0, 5, sanitize_text(decision_text), align="L")
        pdf.set_y(curr_y + 10.5)

        # 4-Tile Metric Matrix: Compliance Score | Inspection Confidence | MPE | Risk Level
        tile_w = (page_w - 6) / 4.0
        tile_h = 13.0
        ty = pdf.get_y()

        # Score calculations
        compliance_pct = data.get("compliance_percentage")
        if compliance_pct is None:
            compliance_pct = data.get("summary", {}).get("compliance_percentage", 85.7)
        comp_score_str = f"{float(compliance_pct):.1f}%"

        insp_conf = data.get("inspection_confidence") or data.get("overall_confidence") or 92.0
        insp_conf_str = f"{float(insp_conf):.1f}%"

        # MPE calculation extraction
        mpe_info = data.get("quantity_mpe") or {}
        decl_qty = str(mpe_info.get("declared_quantity") or data.get("declarations", {}).get("net_quantity", {}).get("value") or "Standard")
        mpe_str = str(mpe_info.get("mpe_display") or "3.0%")
        mpe_display = f"{decl_qty} (MPE: {mpe_str})"

        # Risk level
        risk_info = data.get("risk_classification") or {}
        risk_level = str(risk_info.get("level") or ("HIGH" if is_violation else "LOW")).upper()

        tiles = [
            ("COMPLIANCE SCORE", comp_score_str, "Rules Met / Total Rules"),
            ("INSPECTION CONFIDENCE", insp_conf_str, "Image & OCR Integrity"),
            ("STATUTORY MPE (SCHED IV)", sanitize_text(mpe_display[:24]), "Fourth Schedule Limit"),
            ("RISK ASSESSMENT", risk_level, "Enforcement Priority")
        ]

        for i, (title, val, sub) in enumerate(tiles):
            tx = pdf.l_margin + i * (tile_w + 2)
            pdf.set_fill_color(248, 250, 252)
            pdf.set_draw_color(226, 232, 240)
            pdf.rect(tx, ty, tile_w, tile_h, "DF")

            pdf.set_xy(tx + 2, ty + 1.2)
            pdf.set_font("helvetica", "B", 7)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(tile_w - 4, 3, title, align="C")

            pdf.set_xy(tx + 2, ty + 4.2)
            pdf.set_font("helvetica", "B", 9)
            if "RISK" in title:
                pdf.set_text_color(185, 28, 28) if risk_level == "HIGH" else pdf.set_text_color(22, 101, 52)
            else:
                pdf.set_text_color(15, 23, 42)
            pdf.cell(tile_w - 4, 4.5, val, align="C")

            pdf.set_xy(tx + 2, ty + 8.8)
            pdf.set_font("helvetica", "I", 6)
            pdf.set_text_color(148, 163, 184)
            pdf.cell(tile_w - 4, 3, sub, align="C")

        pdf.set_y(ty + tile_h + 3)

    @classmethod
    def _render_visual_evidence(
        cls,
        pdf: StatutoryPDF,
        data: Dict[str, Any],
        annotated_image: Optional[Union[np.ndarray, str, bytes]],
        raw_image: Optional[np.ndarray]
    ):
        """Renders Explainable AI visual evidence: embedded image with color-coded boxes."""
        page_w = pdf.w - pdf.l_margin - pdf.r_margin

        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 5, sanitize_text("2. EXPLAINABLE AI VISUAL EVIDENCE (STATUTORY BOUNDING BOXES)"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)

        # Resolve image to embed
        img_np = None
        evaluations = data.get("explainable_rules") or data.get("checks") or data.get("results") or []

        # 1. From numpy array directly
        if isinstance(annotated_image, np.ndarray):
            img_np = annotated_image
        # 2. From Base64 string
        elif isinstance(annotated_image, str) and (annotated_image.startswith("data:") or len(annotated_image) > 100):
            img_np = EvidenceVisualizer.from_base64(annotated_image)
        # 3. From raw_image + evaluations
        elif raw_image is not None and isinstance(raw_image, np.ndarray):
            img_np = EvidenceVisualizer.draw_evidence_boxes(raw_image, evaluations, max_dim=900)
        # 4. From disk file URL in data
        if img_np is None:
            proc_url = data.get("dewarped_image_url") or data.get("processed_url") or data.get("original_image_url") or data.get("original_url")
            if proc_url and isinstance(proc_url, str):
                # Map relative URL to filesystem path
                clean_rel = proc_url.lstrip("/").replace("/", os.sep)
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                fpath = os.path.join(base_dir, clean_rel)
                if os.path.exists(fpath):
                    loaded = cv2.imread(fpath)
                    if loaded is not None:
                        img_np = EvidenceVisualizer.draw_evidence_boxes(loaded, evaluations, max_dim=900)

        # Render image into PDF if available
        if img_np is not None and img_np.size > 0:
            try:
                # Downscale for crisp PDF insertion
                h, w = img_np.shape[:2]
                target_w_mm = 110.0  # mm in PDF
                target_h_mm = min(62.0, (h / float(w)) * target_w_mm)

                # Encode to high-quality JPEG in memory
                success, buf = cv2.imencode(".jpg", img_np, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
                if success:
                    bio = io.BytesIO(buf.tobytes())
                    img_x = pdf.l_margin + (page_w - target_w_mm) / 2.0
                    curr_y = pdf.get_y()
                    pdf.image(bio, x=img_x, y=curr_y, w=target_w_mm, h=target_h_mm)
                    pdf.set_y(curr_y + target_h_mm + 1.5)
            except Exception as e:
                logger.warning(f"Failed to embed visual evidence image in PDF: {e}")
                pdf.set_font("helvetica", "I", 8)
                pdf.set_text_color(148, 163, 184)
                pdf.cell(0, 6, sanitize_text("[Visual Evidence Image Attached Separately in Inspector Registry]"), align="C", new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("helvetica", "I", 8)
            pdf.set_text_color(148, 163, 184)
            pdf.cell(0, 6, sanitize_text("[Visual Evidence Frame Recorded in Digital Enforcement Registry]"), align="C", new_x="LMARGIN", new_y="NEXT")

        # Evidence Caption & Legend Note
        pdf.set_font("helvetica", "I", 7)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(0, 3.8, sanitize_text("Figure 1: Optical Character Recognition (OCR) Statutory Coordinates Overlay"), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 3.5, sanitize_text("Color Legend: [PASS] Green = Conforming | [FAIL] Red = Non-Compliant | [REVIEW] Yellow = Manual Verification Required"), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2.5)

    @classmethod
    def _render_audit_table(cls, pdf: StatutoryPDF, data: Dict[str, Any]):
        """Renders structured Statutory Declarations Audit Table."""
        page_w = pdf.w - pdf.l_margin - pdf.r_margin

        # Check if we need a page break before table
        if pdf.get_y() > 185:
            pdf.add_page()

        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 5, sanitize_text("3. STATUTORY PACKAGING DECLARATIONS AUDIT TABLE"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        # Column widths (Total = page_w approx 180mm)
        col_w = [42.0, 50.0, 64.0, 24.0]
        headers = ["Statutory Field", "Observed Declaration", "Legal Requirement / Provision", "Audit Status"]

        # Table Header Row
        pdf.set_fill_color(30, 41, 59)  # Slate-800
        pdf.set_draw_color(51, 65, 85)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(255, 255, 255)

        for w, h_txt in zip(col_w, headers):
            pdf.cell(w, 5.5, sanitize_text(h_txt), border=1, fill=True, align="L" if w > 30 else "C")
        pdf.ln()

        # Build comprehensive row list from explainable rules or declarations
        checks = data.get("explainable_rules") or data.get("checks") or data.get("results") or []
        decls = data.get("declarations") or data.get("extracted_declarations") or data.get("technical_matrix") or {}

        # Canonical statutory rows mapping
        mandatory_rows = [
            ("Generic / Product Name", "generic_name", "Rule 6(1)(b) - Identification of Commodity"),
            ("Net Quantity & Unit", "net_quantity", "Rule 6(1)(c) & Rule 12 - Legal SI Units"),
            ("Maximum Retail Price (MRP)", "mrp", "Rule 6(1)(e) - Incl. of all taxes"),
            ("Unit Sale Price (USP)", "unit_sale_price", "Rule 6(11) - Statutory Unit Rate"),
            ("Date of Manufacture / Pkd", "manufacturing_date", "Rule 6(1)(d) - Month & Year"),
            ("Expiry Date / Best Before", "expiry_date", "Rule 6(1)(d) - Consumer Safety Period"),
            ("Batch / Lot Number", "batch_number", "Rule 6(1)(g) - Production Traceability"),
            ("Manufacturer / Packer Name", "manufacturer", "Rule 6(1)(a) - Complete Business Identity"),
            ("Country of Origin (COO)", "country_of_origin", "Rule 6(1)(j) - Country of Manufacture"),
            ("Consumer Care Redressal", "consumer_care", "Rule 6(1)(n) - Name, Tel, Email & Address"),
            ("Rule 7 Font Height Calibration", "font_size", "Rule 7 Table I - Min Numerals vs PDP Area")
        ]

        # Convert checks to lookup dict for status and reasoning
        checks_map = {}
        for c in checks:
            f = str(c.get("field_name") or c.get("field") or "").lower()
            if f:
                checks_map[f] = c

        pdf.set_font("helvetica", "", 7)
        row_idx = 0

        for title, key, legal_rule in mandatory_rows:
            # Resolve observed value
            obs_val = "Not Detected"
            status = "REVIEW"

            # Check from checks map first
            c_item = checks_map.get(key) or checks_map.get(key.replace("_", ""))
            if c_item:
                obs_val = str(c_item.get("detected_evidence") or c_item.get("observed") or c_item.get("extracted_value") or "Not Detected")
                status = str(c_item.get("status") or "REVIEW").upper()
            else:
                # Check from declarations
                d_item = decls.get(key)
                if isinstance(d_item, dict):
                    obs_val = str(d_item.get("value") or "Not Detected")
                    status = "PASS" if d_item.get("detected") else "REVIEW"
                elif d_item:
                    obs_val = str(d_item)
                    status = "PASS"

            # If font size calibration
            if key == "font_size":
                pdp = data.get("pdp_blueprint") or data.get("pdp_info") or {}
                m_font = pdp.get("measured_font_mm", 3.2)
                r_font = pdp.get("statutory_min_font_mm", 2.5)
                obs_val = f"Measured {m_font} mm (Req: {r_font} mm)"
                status = "PASS" if m_font >= r_font else "FAIL"

            # Formatting
            clean_obs = sanitize_text(obs_val[:32])
            clean_rule = sanitize_text(legal_rule[:42])
            clean_status = "PASS" if "PASS" in status else ("FAIL" if "FAIL" in status else "REVIEW")

            # Alternating zebra striping
            bg_col = (255, 255, 255) if row_idx % 2 == 0 else (248, 250, 252)
            pdf.set_fill_color(*bg_col)
            pdf.set_draw_color(226, 232, 240)

            # Field Title
            pdf.set_text_color(15, 23, 42)
            pdf.set_font("helvetica", "B", 7)
            pdf.cell(col_w[0], 5.0, sanitize_text(title[:24]), border=1, fill=True)

            # Observed Declaration
            pdf.set_font("helvetica", "", 7)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(col_w[1], 5.0, clean_obs, border=1, fill=True)

            # Legal Rule Reference
            pdf.set_text_color(71, 85, 105)
            pdf.cell(col_w[2], 5.0, clean_rule, border=1, fill=True)

            # Audit Status Tag with Color Indicator
            if clean_status == "PASS":
                pdf.set_text_color(22, 101, 52)
                pdf.set_font("helvetica", "B", 7)
                pdf.cell(col_w[3], 5.0, "[PASS] CONFORMS", border=1, fill=True, align="C")
            elif clean_status == "FAIL":
                pdf.set_text_color(185, 28, 28)
                pdf.set_font("helvetica", "B", 7)
                pdf.cell(col_w[3], 5.0, "[FAIL] VIOLATION", border=1, fill=True, align="C")
            else:
                pdf.set_text_color(180, 83, 9)
                pdf.set_font("helvetica", "B", 7)
                pdf.cell(col_w[3], 5.0, "[REVIEW] VERIFY", border=1, fill=True, align="C")

            pdf.ln()
            row_idx += 1

        pdf.ln(2.5)

    @classmethod
    def _render_section_4(cls, pdf: StatutoryPDF, data: Dict[str, Any]) -> str:
        """
        Renders dynamic Section 4 grounded in OCR evidence and rule evaluations:
        - Branch 1: Fully Compliant (PASS / 7A COMPLIANT) -> Statutory Clearance Endorsement
        - Branch 2: Non-Compliant (FAIL / 7B VIOLATION) -> Section 36 Show-Cause Notice with dynamic contravention bullets
        - Branch 3: Review Required (REVIEW / PARTIALLY COMPLIANT) -> Provisional Inspection Memorandum with flagged review items

        Returns:
            str: Normalized adjudication branch ('PASS', 'FAIL', or 'REVIEW')
        """
        page_w = pdf.w - pdf.l_margin - pdf.r_margin

        # Resolve status and rule evaluations
        overall_status = str(
            data.get("overall_status")
            or data.get("status")
            or data.get("overall_status_legacy")
            or data.get("officer_decision")
            or ""
        ).strip()
        status_upper = overall_status.upper()

        rule_evaluations = (
            data.get("rule_evaluations")
            or data.get("explainable_rules")
            or data.get("checks")
            or data.get("results")
            or []
        )

        # Categorize rule evaluations
        failed_rules = []
        review_rules = []

        for r in rule_evaluations:
            st = str(r.get("status") or "").strip().upper()
            if any(k in st for k in ["FAIL", "VIOLATION", "NON-COMPLIANT", "NON_COMPLIANT", "7B"]):
                failed_rules.append(r)
            elif any(k in st for k in ["REVIEW", "NEEDS_REVIEW", "NEEDS REVIEW", "PARTIAL", "CANNOT_VERIFY", "PENDING"]):
                review_rules.append(r)

        is_fail_status = any(k in status_upper for k in ["FAIL", "7B", "VIOLATION", "NON-COMPLIANT", "NON_COMPLIANT"])
        is_review_status = any(k in status_upper for k in ["REVIEW", "PARTIAL", "PARTIALLY COMPLIANT", "NEEDS REVIEW", "NEEDS_REVIEW", "CANNOT_VERIFY", "PENDING"])
        is_pass_status = any(k in status_upper for k in ["PASS", "7A", "7A COMPLIANT", "COMPLIANT", "FOLLOWED"])

        # Prevent cramped layout near bottom of page
        if pdf.get_y() > 215:
            pdf.add_page()

        # =========================================================================
        # BRANCH 1: Fully Compliant (PASS / 7A COMPLIANT)
        # =========================================================================
        if (is_pass_status or status_upper in ["PASS", "7A COMPLIANT", "COMPLIANT", "SECTION 7A COMPLIANT"]) and len(failed_rules) == 0 and not is_fail_status and (not is_review_status or len(review_rules) == 0):
            branch = "PASS"

            # Section Title
            pdf.set_font("helvetica", "B", 9)
            pdf.set_text_color(16, 120, 60)  # Conforming Emerald
            pdf.cell(0, 4.5, sanitize_text("4. STATUTORY CLEARANCE ENDORSEMENT & CERTIFICATE OF CONFORMITY"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            # Statutory Clearance Box
            clearance_text = (
                "STATUTORY CLEARANCE ENDORSEMENT: Upon thorough automated examination and optical inspection of the "
                "pre-packaged commodity label conducted under powers conferred by Section 15 of the Legal Metrology Act, 2009, "
                "no legal contraventions, omissions, or labeling discrepancies were observed. The commodity satisfies all "
                "mandatory declarations under Rules 6, 7, and 12 of the Legal Metrology (Packaged Commodities) Rules, 2011, "
                "including Principal Display Panel (PDP) proportion, minimum numeral font height calibrations, verified net "
                "quantity tolerances within Fourth Schedule Maximum Permissible Error (MPE) thresholds, Maximum Retail Price (MRP), "
                "Unit Sale Price (USP), manufacturer identity, and consumer care redressal mechanisms."
            )
            pdf.set_fill_color(240, 253, 244)  # Emerald-50
            pdf.set_draw_color(134, 239, 172)  # Emerald-300
            pdf.set_font("helvetica", "", 7.5)
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(page_w, 3.6, sanitize_text(clearance_text), border=1, fill=True)
            pdf.ln(1.5)

            # Explicit Bold Conclusion
            pdf.set_fill_color(236, 253, 245)  # Emerald-100
            pdf.set_draw_color(34, 197, 94)   # Emerald-500
            pdf.set_font("helvetica", "B", 8)
            pdf.set_text_color(22, 101, 52)   # Emerald-800
            conclusion_text = "No punitive action or show-cause notice under Section 36 is warranted. Product is approved for retail circulation."
            pdf.multi_cell(page_w, 4.2, sanitize_text(conclusion_text), border=1, fill=True)
            pdf.ln(3)

        # =========================================================================
        # BRANCH 2: Non-Compliant (FAIL / 7B VIOLATION)
        # =========================================================================
        elif is_fail_status or len(failed_rules) > 0:
            branch = "FAIL"

            # Section Title
            pdf.set_font("helvetica", "B", 9)
            pdf.set_text_color(185, 28, 28)  # Deep statutory crimson
            pdf.cell(0, 4.5, sanitize_text("4. STATUTORY SHOW-CAUSE NOTICE UNDER SECTION 36, LEGAL METROLOGY ACT, 2009"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            # Formal legal warning about Section 36 penalties
            warning_text = (
                "FORMAL STATUTORY SHOW-CAUSE NOTICE: Upon optical and statutory examination of the pre-packaged commodity label "
                "under powers conferred by Section 15 of the Legal Metrology Act, 2009, this automated audit record identifies non-compliance "
                "and contraventions of mandatory packaging declarations (Section 7B statutory violation). Manufacture, packing, "
                "distribution, or retail sale of non-conforming pre-packaged commodities is an offence punishable under Section 36 of "
                "the Legal Metrology Act, 2009 (with fine up to Rs. 25,000 for the first offence, up to Rs. 50,000 for the second offence, "
                "and with fine up to Rs. 1,00,000 or imprisonment up to one year for subsequent offences). The designated manufacturer, "
                "packer, or importer is hereby notified to produce compounding representation or verification records within "
                "15 statutory days of notice receipt."
            )
            pdf.set_fill_color(254, 242, 242)  # Red-50
            pdf.set_draw_color(248, 113, 113)  # Red-400
            pdf.set_font("helvetica", "", 7.5)
            pdf.set_text_color(69, 10, 10)     # Red-950
            pdf.multi_cell(page_w, 3.6, sanitize_text(warning_text), border=1, fill=True)
            pdf.ln(2)

            # Dynamic Evidence Injection: List of Failed Rules
            pdf.set_font("helvetica", "B", 8)
            pdf.set_text_color(153, 27, 27)
            pdf.cell(0, 4.0, sanitize_text("SUMMARY OF DETECTED CONTRAVENTIONS & STATUTORY GROUNDS:"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            target_fails = failed_rules if failed_rules else [
                {
                    "rule_name": "Packaging Declaration Non-Conformance",
                    "observed": "Discrepancy noted during inspection",
                    "reason": "Mandatory statutory requirements under PCR 2011 not satisfied."
                }
            ]

            for rule in target_fails:
                if pdf.get_y() > 255:
                    pdf.add_page()

                r_name = str(rule.get("rule_name") or rule.get("field_name") or rule.get("rule_id") or "Statutory Packaging Rule")
                obs_val = str(rule.get("detected_evidence") or rule.get("observed") or rule.get("extracted_value") or rule.get("observed_value") or "Not Detected")
                reason = str(rule.get("reason") or rule.get("explanation") or rule.get("statutory_explanation") or rule.get("error_message") or "Non-compliance with statutory requirement.")

                # Bullet header: Rule Name / Statutory Field
                pdf.set_font("helvetica", "B", 7.5)
                pdf.set_text_color(185, 28, 28)
                pdf.multi_cell(page_w, 3.8, sanitize_text(f"-  {r_name}:"))

                # Indented evidence & statutory reason
                pdf.set_font("helvetica", "", 7.0)
                pdf.set_text_color(51, 65, 85)
                pdf.set_x(pdf.l_margin + 5)
                bullet_body = f"Observed Value (OCR): {obs_val}  |  Statutory Reason: {reason}"
                pdf.multi_cell(page_w - 5, 3.4, sanitize_text(bullet_body))
                pdf.ln(1.2)

            pdf.ln(2)

        # =========================================================================
        # BRANCH 3: Review Required (REVIEW / PARTIALLY COMPLIANT)
        # =========================================================================
        else:
            branch = "REVIEW"

            # Section Title
            pdf.set_font("helvetica", "B", 9)
            pdf.set_text_color(180, 83, 9)  # Amber-700
            pdf.cell(0, 4.5, sanitize_text("4. PROVISIONAL INSPECTION MEMORANDUM - VISUAL AUDIT PENDING"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            # Provisional Memorandum Box
            memo_text = (
                "PROVISIONAL AUDIT MEMORANDUM: Automated artificial intelligence examination conducted under Section 15 of the "
                "Legal Metrology Act, 2009 flagged packaging declarations that exhibit low-confidence OCR reads, potential label "
                "curvature distortion, or missing mandatory declarations requiring manual officer visual verification before a final "
                "statutory ruling is entered. No immediate punitive notice or show-cause prosecution under Section 36 is sanctioned "
                "pending physical verification or high-resolution re-audit by an authorized Legal Metrology Officer."
            )
            pdf.set_fill_color(254, 252, 232)  # Amber-50
            pdf.set_draw_color(251, 191, 36)   # Amber-400
            pdf.set_font("helvetica", "", 7.5)
            pdf.set_text_color(120, 53, 15)    # Amber-900
            pdf.multi_cell(page_w, 3.6, sanitize_text(memo_text), border=1, fill=True)
            pdf.ln(2)

            # Dynamic Evidence Injection: List of Review Rules
            pdf.set_font("helvetica", "B", 8)
            pdf.set_text_color(146, 64, 14)
            pdf.cell(0, 4.0, sanitize_text("ITEMS FLAGGED FOR MANUAL OFFICER VERIFICATION:"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            target_reviews = review_rules if review_rules else [
                {
                    "field_name": "Optical Clarity / Packaging Verification",
                    "observed": "Low confidence read",
                    "reason": "Requires physical inspection or higher-resolution scan."
                }
            ]

            for rule in target_reviews:
                if pdf.get_y() > 255:
                    pdf.add_page()

                r_name = str(rule.get("rule_name") or rule.get("field_name") or rule.get("rule_id") or "Packaging Declaration")
                obs_val = str(rule.get("detected_evidence") or rule.get("observed") or rule.get("extracted_value") or rule.get("observed_value") or "Not Detected")
                reason = str(rule.get("reason") or rule.get("explanation") or rule.get("statutory_explanation") or "Requires manual officer inspection / visual audit.")

                # Bullet header: Flagged Field / Rule
                pdf.set_font("helvetica", "B", 7.5)
                pdf.set_text_color(180, 83, 9)
                pdf.multi_cell(page_w, 3.8, sanitize_text(f"-  {r_name}:"))

                # Indented evidence & explanation for human review
                pdf.set_font("helvetica", "", 7.0)
                pdf.set_text_color(51, 65, 85)
                pdf.set_x(pdf.l_margin + 5)
                bullet_body = f"Observed Read: {obs_val}  |  Officer Action Required: {reason}"
                pdf.multi_cell(page_w - 5, 3.4, sanitize_text(bullet_body))
                pdf.ln(1.2)

            pdf.ln(2)

        return branch

    @classmethod
    def _render_signatures(cls, pdf: StatutoryPDF, data: Dict[str, Any], status_branch: str = "PASS"):
        """Renders Dual Digital Signature Seals for Inspecting Officer and Central Adjudication."""
        page_w = pdf.w - pdf.l_margin - pdf.r_margin

        # Ensure signature blocks fit comfortably without colliding with footer
        if pdf.get_y() > 245:
            pdf.add_page()

        sig_w = (page_w - 8) / 2.0
        sy = pdf.get_y()

        # Left: Inspecting Officer Seal
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(pdf.l_margin, sy, sig_w, 20, "DF")

        pdf.set_xy(pdf.l_margin + 3, sy + 2)
        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(sig_w - 6, 3, "INSPECTING FIELD OFFICER:")
        pdf.ln(3.5)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.set_x(pdf.l_margin + 3)
        pdf.cell(sig_w - 6, 4, sanitize_text(str(data.get("inspector_name") or "Authorized LM Officer")))
        pdf.ln(4)
        pdf.set_font("helvetica", "I", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.set_x(pdf.l_margin + 3)
        pdf.cell(sig_w - 6, 3.5, "Digitally Attested via METRIX-LM Inspection Registry")
        pdf.ln(3.5)
        pdf.set_x(pdf.l_margin + 3)
        pdf.cell(sig_w - 6, 3.5, sanitize_text(f"Seal ID: LM-ENF-{datetime.now().strftime('%Y%m%d')}-IND"))

        # Right: Senior Reviewing Officer / Adjudication Seal
        rx = pdf.l_margin + sig_w + 8
        pdf.rect(rx, sy, sig_w, 20, "DF")

        pdf.set_xy(rx + 3, sy + 2)
        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(sig_w - 6, 3, "CENTRAL ADJUDICATION SEAL:")
        pdf.ln(3.5)
        pdf.set_font("helvetica", "B", 8)

        # Adjudication text and color based on branch
        if status_branch == "PASS":
            pdf.set_text_color(22, 101, 52)
            default_adjudication = "7A COMPLIANT - APPROVED"
        elif status_branch == "FAIL":
            pdf.set_text_color(185, 28, 28)
            default_adjudication = "7B VIOLATION - NOTICE ISSUED"
        else:
            pdf.set_text_color(180, 83, 9)
            default_adjudication = "PROVISIONAL - AUDIT PENDING"

        adjudication_text = str(data.get("officer_decision") or default_adjudication)
        pdf.set_x(rx + 3)
        pdf.cell(sig_w - 6, 4, sanitize_text(adjudication_text))
        pdf.ln(4)
        pdf.set_font("helvetica", "I", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.set_x(rx + 3)
        pdf.cell(sig_w - 6, 3.5, "Ministry of Consumer Affairs - Legal Metrology Wing")
        pdf.ln(3.5)
        pdf.set_x(rx + 3)
        pdf.cell(sig_w - 6, 3.5, "Government of India Official Statutory Record")

    @classmethod
    def _render_legal_notice_and_signatures(cls, pdf: StatutoryPDF, data: Dict[str, Any]):
        """Renders dynamic Section 4 and Dual Digital Inspection Seals."""
        branch = cls._render_section_4(pdf, data)
        cls._render_signatures(pdf, data, status_branch=branch)

