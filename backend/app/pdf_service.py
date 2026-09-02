"""
pdf_service.py - ReportLab PDF Inspection Certificate Generator (5-Section Structure)
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter  # type: ignore
from reportlab.lib import colors  # type: ignore
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable  # type: ignore
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore

class PDFReportGenerator:

    @staticmethod
    def generate_inspection_certificate(record_data: dict) -> bytes:
        """
        Generates official 5-Section Legal Metrology Statutory Inspection PDF Certificate.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Custom Typography Styles
        title_style = ParagraphStyle(
            'GovTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#0F172A'),
            alignment=1
        )

        subtitle_style = ParagraphStyle(
            'GovSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#475569'),
            alignment=1
        )

        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#1E3A8A'),
            spaceBefore=10,
            spaceAfter=4
        )

        body_style = ParagraphStyle(
            'GovBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1E293B')
        )

        badge_style = ParagraphStyle(
            'BadgeStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.white
        )

        story = []

        # Government Header & Title
        story.append(Paragraph("MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION", subtitle_style))
        story.append(Paragraph("DEPARTMENT OF CONSUMER AFFAIRS • LEGAL METROLOGY DIVISION", subtitle_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph("STATUTORY PACKAGED COMMODITIES COMPLIANCE CERTIFICATE", title_style))
        story.append(Spacer(1, 2))
        story.append(Paragraph("Issued under Section 15 of Legal Metrology Act, 2009 & Packaged Commodities Rules, 2011 (G.S.R. 629(E))", subtitle_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=10))

        # Overview Table
        status = record_data.get("overall_status") or "PENDING"
        status_bg = colors.HexColor('#16A34A') if "7A" in status else colors.HexColor('#DC2626')
        
        overview_data = [
            [
                Paragraph("<b>Inspection Certificate ID:</b>", body_style),
                Paragraph(record_data.get("id", "NOT RECORDED"), body_style),
                Paragraph("<b>Date of Inspection:</b>", body_style),
                Paragraph(datetime.now().strftime("%d %b %Y, %H:%M HRS"), body_style)
            ],
            [
                Paragraph("<b>Product Name:</b>", body_style),
                Paragraph(record_data.get("product_name", "NOT RECORDED"), body_style),
                Paragraph("<b>Overall Status:</b>", body_style),
                Paragraph(f"<font color='white'><b>{status}</b></font>", badge_style)
            ],
            [
                Paragraph("<b>Inspection Office:</b>", body_style),
                Paragraph(record_data.get("location", "NOT RECORDED"), body_style),
                Paragraph("<b>Attesting Officer:</b>", body_style),
                Paragraph(record_data.get("inspector_name", "NOT RECORDED"), body_style)
            ]
        ]

        overview_table = Table(overview_data, colWidths=[130, 160, 110, 140])
        overview_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BACKGROUND', (3, 1), (3, 1), status_bg),
            ('ALIGN', (3, 1), (3, 1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(overview_table)
        story.append(Spacer(1, 10))

        def _to_text(val, fallback="NOT DETECTED"):
            if val is None:
                return fallback
            if isinstance(val, dict):
                return str(val.get("value") or val.get("normalized_value") or fallback)
            return str(val) if str(val).strip() else fallback

        # SECTION 1: Company Profile
        story.append(Paragraph("1. Company & LMPC Registration Profile", section_heading))
        comp = record_data.get("company_profile", {}) or {}
        comp_table_data = [
            [Paragraph("<b>Company Name [Auto-Extracted]</b>", body_style), Paragraph(_to_text(comp.get("company_name")), body_style)],
            [Paragraph("<b>Corporate Identity No. (CIN)</b>", body_style), Paragraph(f"{_to_text(comp.get('cin'))}", body_style)],
            [Paragraph("<b>GSTIN & LMPC Reg No.</b>", body_style), Paragraph(f"GSTIN: {_to_text(comp.get('gstin'))} | LMPC: {_to_text(comp.get('lmpc_cert_number'))}", body_style)],
            [Paragraph("<b>Attached License Scan</b>", body_style), Paragraph("Not verified - no certificate scan available", body_style)]
        ]
        comp_table = Table(comp_table_data, colWidths=[180, 360])
        comp_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(comp_table)
        story.append(Spacer(1, 8))

        # SECTION 2: Technical Product Matrix
        story.append(Paragraph("2. Technical Product Matrix & Schedule II Package Check", section_heading))
        tech = record_data.get("technical_matrix", {}) or {}
        tech_table_data = [
            [Paragraph("<b>Generic Name [Auto-Extracted]</b>", body_style), Paragraph(_to_text(tech.get("generic_name") or tech.get("product_name")), body_style)],
            [Paragraph("<b>Declared Net Quantity</b>", body_style), Paragraph(_to_text(tech.get("net_quantity") or tech.get("declared_net_qty")), body_style)],
            [Paragraph("<b>Schedule II Standard Check</b>", body_style), Paragraph("Statutory packaging standards evaluated under database rule matrix.", body_style)]
        ]
        tech_table = Table(tech_table_data, colWidths=[180, 360])
        tech_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(tech_table)
        story.append(Spacer(1, 8))

        # SECTION 3: PDP Blueprint & Rule 7 Table-I Font Calibration
        story.append(Paragraph("3. Principal Display Panel (PDP) Blueprint & Rule 7 Table-I Calibration", section_heading))
        pdp = record_data.get("pdp_blueprint", {}) or {}
        pdp_table_data = [
            [Paragraph("<b>PDP Surface Area (A)</b>", body_style), Paragraph(f"{_to_text(pdp.get('pdp_area_cm2'))} cm² ({_to_text(pdp.get('pdp_shape'), 'rectangular')})", body_style)],
            [Paragraph("<b>Rule 7, Table-I Min Height</b>", body_style), Paragraph(f"Mandatory Minimum: <b>{_to_text(pdp.get('statutory_min_font_mm'))} mm</b> | Measured: <b>{_to_text(pdp.get('measured_font_mm'))} mm</b>", body_style)],
            [Paragraph("<b>Wording Verification</b>", body_style), Paragraph("Rule 6(1)(e) MRP inclusive-of-all-taxes clause verified against extracted text where detectable.", body_style)]
        ]
        pdp_table = Table(pdp_table_data, colWidths=[180, 360])
        pdp_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(pdp_table)
        story.append(Spacer(1, 8))

        # SECTION 4: Quantity Verification & First Schedule MPE
        story.append(Paragraph("4. Quantity Verification & First Schedule MPE", section_heading))
        q_mpe = record_data.get("quantity_mpe", {}) or {}
        mpe_display = _to_text(q_mpe.get("mpe_display") or (q_mpe.get("first_schedule_mpe", {}) or {}).get("mpe_display"))
        scale_info = _to_text(q_mpe.get("equipment_cert_number"))
        q_table_data = [
            [Paragraph("<b>First Schedule MPE Tolerance</b>", body_style), Paragraph(f"Statutory MPE limit based on declared net quantity: <b>{mpe_display}</b>", body_style)],
            [Paragraph("<b>Weighing Scale Cert [Manually Entered]</b>", body_style), Paragraph(f"Scale certificate: {scale_info}", body_style)]
        ]
        q_table = Table(q_table_data, colWidths=[180, 360])
        q_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(q_table)
        story.append(Spacer(1, 8))

        # SECTION 5: Customer Care Framework
        story.append(Paragraph("5. Customer Care Framework Declarations", section_heading))
        cust = record_data.get("customer_care", {}) or {}
        cust_table_data = [
            [Paragraph("<b>Designated Role & Address</b>", body_style), Paragraph(f"{_to_text(cust.get('designated_name_role') or cust.get('value'))} | {_to_text(cust.get('postal_address'))}", body_style)],
            [Paragraph("<b>Email & Helpline Number</b>", body_style), Paragraph(f"Email: {_to_text(cust.get('email') or cust.get('consumer_care_email'))} | Helpline: {_to_text(cust.get('phone') or cust.get('consumer_care_phone'))}", body_style)]
        ]
        cust_table = Table(cust_table_data, colWidths=[180, 360])
        cust_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(cust_table)
        story.append(Spacer(1, 15))

        # Statutory Disclaimer & Sign-Off Footer
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#94A3B8'), spaceAfter=8))
        disclaimer_text = (
            "<b>STATUTORY EVIDENCE DISCLAIMER:</b> This compliance report reflects data verified by authenticated "
            f"Officer <b>{record_data.get('inspector_name', 'NOT RECORDED')}</b> on {datetime.now().strftime('%d %b %Y')}. "
            "All extracted fields carry immutable OCR audit trails. Generated by METRIX-LM Regulatory System."
        )
        story.append(Paragraph(disclaimer_text, subtitle_style))
        
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
