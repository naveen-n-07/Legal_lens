"""
declaration_extractor.py - Regex & String Matching Declaration Parser (No YOLO / No Generative Filling)
"""

import re
from typing import Dict, Any, Optional

class DeclarationExtractor:

    @staticmethod
    def parse_declarations(raw_text: str) -> Dict[str, Optional[str]]:
        """
        Parses raw text extracted by PaddleOCR using deterministic regex pattern matching.
        Looks for statutory keywords: MRP, Maximum Retail Price, Net Quantity, Manufactured by, Packed, Consumer Care.
        """
        text = raw_text.replace("\n", " ").strip()
        text_upper = text.upper()

        # 1. Extract MRP
        mrp_match = re.search(r"(?:MRP|MAXIMUM RETAIL PRICE)\s*(?:RS\.?|₹|\:)?\s*([₹\d\.\,]+(?:\s*INCL[U\.\w\s]*TAXES)?)", text_upper, re.IGNORECASE)
        mrp = mrp_match.group(0).strip() if mrp_match else None
        if not mrp:
            mrp_fallback = re.search(r"₹\s*\d+(?:\.\d{2})?", text)
            mrp = mrp_fallback.group(0).strip() if mrp_fallback else None

        # 2. Extract Net Quantity
        net_qty_match = re.search(r"(?:NET QUANTITY|NET QTY|NET WEIGHT|NET WT\.?)\s*(?:\:)?\s*(\d+(?:\.\d+)?\s*(?:g|kg|ml|l|n|number|units?))", text, re.IGNORECASE)
        net_qty = net_qty_match.group(1).strip() if net_qty_match else None
        if not net_qty:
            net_qty_fallback = re.search(r"\b\d+(?:\.\d+)?\s*(?:g|kg|ml|l)\b", text, re.IGNORECASE)
            net_qty = net_qty_fallback.group(0).strip() if net_qty_fallback else None

        # 3. Extract Manufacturer Name & Address
        mfg_match = re.search(r"(?:MANUFACTURED BY|MFG BY|PRODUCED BY)\s*([A-Z0-9\s\.\,]+?)(?=(?:PACKED|IMPORTED|NET QTY|MRP|CONSUMER|CIN|GSTIN|$))", text_upper, re.IGNORECASE)
        manufacturer = mfg_match.group(1).strip() if mfg_match else None

        # 4. Extract Packer Name & Address
        packer_match = re.search(r"(?:PACKED BY|PACKER)\s*([A-Z0-9\s\.\,]+?)(?=(?:IMPORTED|NET QTY|MRP|CONSUMER|$))", text_upper, re.IGNORECASE)
        packer = packer_match.group(1).strip() if packer_match else None

        # 5. Extract Importer Name & Address
        importer_match = re.search(r"(?:IMPORTED BY|IMPORTER)\s*([A-Z0-9\s\.\,]+?)(?=(?:NET QTY|MRP|CONSUMER|$))", text_upper, re.IGNORECASE)
        importer = importer_match.group(1).strip() if importer_match else None

        # 6. Extract Month/Year Date of Manufacture/Packing
        date_match = re.search(r"(?:PACKED|MFG|DATE|MONTH\/YEAR)\s*(?:\:)?\s*(\d{2}\/\d{4}|\d{2}-\d{4}|\w+\s*\d{4})", text_upper, re.IGNORECASE)
        date_val = date_match.group(1).strip() if date_match else None

        # 7. Extract Consumer Care Contact
        care_match = re.search(r"(?:CONSUMER CARE|CUSTOMER CARE|CARE CELL)\s*(?:\:)?\s*([\w\d\s\-\@\.\:\,]+?)(?=(?:MFG|PACKED|NET QTY|MRP|$))", text_upper, re.IGNORECASE)
        consumer_care = care_match.group(1).strip() if care_match else None
        if not consumer_care:
            phone_match = re.search(r"(?:1800|1860|\+91)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}", text)
            consumer_care = phone_match.group(0).strip() if phone_match else None

        # 8. Extract Product Name
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        product_name = None
        for line in lines:
            line_up = line.upper()
            if not any(k in line_up for k in ["MRP", "NET QTY", "MANUFACTURED", "PACKED", "CONSUMER CARE", "CIN", "GSTIN", "INGREDIENTS"]):
                product_name = line
                break
        if not product_name and lines:
            product_name = lines[0]

        return {
            "product_name": product_name,
            "mrp": mrp,
            "net_quantity": net_qty,
            "manufacturer": manufacturer,
            "packer": packer,
            "importer": importer,
            "date": date_val,
            "consumer_care": consumer_care,
            "address": manufacturer or packer or importer
        }
