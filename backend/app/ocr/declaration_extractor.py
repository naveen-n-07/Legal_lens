"""
declaration_extractor.py - Statutory Declaration Parsing Engine (Stage 5)
Converts raw OCR / Translated text into structured legal metadata using
fault-tolerant Token-Anchored Named Capture Regex pipelines (re.VERBOSE).

Designed for SIH 26034 (METRIX-LM Pan-India Legal Metrology Inspection Engine).
"""

import re
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Standardized Unit Normalization Map (SI Canonical vs Illegal units under Rule 12)
LEGAL_SI_UNITS = {"g", "kg", "mg", "ml", "l", "m", "cm", "mm", "sq.m", "n", "u"}
ILLEGAL_UNITS_RULE12 = {"gm", "gms", "gram", "grams", "kilogram", "kgs", "ltr", "litres", "pcs", "piece"}


class StatutoryExtractor:
    """
    Token-Anchored Modular Regex with Named Capture Groups (`(?P<name>...)`)
    and the `re.VERBOSE` flag (`re.X`).

    Robust against OCR rogue spaces (e.g., 'M R P'), dropped periods ('RS' vs 'Rs.'),
    comma-decimals ('245,00'), and multi-line declaration splits.
    """

    def __init__(self):
        # 1. MRP Pattern: Handles "MRP", "M.R.P.", "Max Retail Price", "Rs.", "₹", "INR"
        # Captures: mrp_val, tax_clause, usp_val, usp_unit
        self.mrp_pattern = re.compile(r"""
            (?:M\s*\.?\s*R\s*\.?\s*P\s*\.?|MAX(?:IMUM)?\s*RETAIL\s*PRICE)   # Anchor
            [^\d₹RsINR]*                                                    # Separators (: = - space)
            (?:Rs\.?|₹|INR|\u20B9)?\s*                                      # Currency symbol
            (?P<mrp_val>\d+(?:[\.,]\d{1,2})?)                              # Price value
            (?:\s*(?P<tax_clause>\(?\s*INCL(?:USIVE)?\.?\s*(?:OF\s*)?ALL\s*TAXES\s*\)?))? # Tax clause
            (?:\s*(?:[-–/|]|USP|UNIT\s*PRICE)?\s*(?:Rs\.?|₹)?\s*(?P<usp_val>\d+(?:[\.,]\d{1,2})?)\s*(?:/|PER)\s*(?P<usp_unit>[a-zA-Z0-9]+))? # Unit Sale Price
        """, re.IGNORECASE | re.VERBOSE)

        # 2. Net Quantity Pattern: Handles "Net Wt", "Net Qty", "Net Content", "Volume"
        # Captures: qty_val, qty_unit (Preserves illegal units like 'gm' for Rule 12 checks)
        self.net_qty_pattern = re.compile(r"""
            (?:NET\s*(?:WT|WEIGHT|QTY|QUANTITY|CONTENTS?|VOL(?:UME)?)|QUANTITY|SHUDDHA\s+MATRA) # Anchor
            [^\d]*                                                                              # Separators
            (?P<qty_val>\d+(?:[\.,]\d+)?)                                                      # Quantity value
            \s*
            (?P<qty_unit>kg|g|gm|gms|ml|l|ltr|litres?|m|cm|mm|n|nos?|units?|pcs?)\b           # Standard/Non-standard units
        """, re.IGNORECASE | re.VERBOSE)

        # 3. Manufacturing / Expiry / Packing Date Pattern
        # Captures: date_type, date_val
        self.date_pattern = re.compile(r"""
            (?P<date_type>MFD|MFG|PACKED|PKD|EXP(?:IRY)?|USE\s*BY|BEST\s*BEFORE) # Date Anchor
            [^\w\d]*                                                             # Separators
            (?P<date_val>
                (?:(?:\d{1,2}[-/\.\s])?(?:[01]?\d|(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[a-z]*)[-/\.\s](?:20\d{2}|\d{2}))
            )
        """, re.IGNORECASE | re.VERBOSE)

        # 4. Consumer Care Helpline & Email Pattern
        self.consumer_care_pattern = re.compile(r"""
            (?:
                (?P<phone>1800[-\s]?\d{3}[-\s]?\d{4}|1800\d{6,8}|\+?91[\s\-]?[6-9]\d{9}|\b[6-9]\d{9}\b)
                |
                (?P<email>[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})
            )
        """, re.IGNORECASE | re.VERBOSE)

        # 5. FSSAI License Pattern (14 consecutive digits)
        self.fssai_pattern = re.compile(r"""
            (?:FSSAI(?:\s*LIC(?:ENSE)?(?:\s*NO\.?)?)?[\s:.\-–—]*)
            (?P<fssai_lic>\b\d{14}\b)
        """, re.IGNORECASE | re.VERBOSE)

        # 6. Country of Origin Pattern
        self.coo_pattern = re.compile(r"""
            (?:COUNTRY\s*OF\s*ORIGIN|MADE\s*IN|PRODUCT\s*OF)
            [\s:.\-–—]*
            (?P<country>[A-Za-z\s]+)
        """, re.IGNORECASE | re.VERBOSE)

    def _clean_number(self, val_str: str) -> float:
        """Converts OCR comma-decimals (e.g. 245,00) to standard floats."""
        return float(val_str.replace(',', '.'))

    def extract_declarations(self, ocr_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parses OCR records and maps statutory entities while retaining 
        bounding boxes for evidentiary UI highlighting (Stage 10).

        Accepts records with either 'text' or 'translated_text' keys.
        """
        extracted: Dict[str, Any] = {
            "mrp": None,
            "net_quantity": None,
            "dates": [],
            "customer_care": None,
            "fssai_license": None,
            "country_of_origin": None,
            "raw_text_stream": []
        }

        consumer_phones = []
        consumer_emails = []

        for record in ocr_records:
            # Handle both raw OCR output and TranslationMiddleware output
            text = (record.get("text") or record.get("translated_text") or "").strip()
            box = record.get("bounding_box", [])
            conf = float(record.get("confidence", 0.0))
            if not text:
                continue

            extracted["raw_text_stream"].append(text)

            # --- Check MRP ---
            if not extracted["mrp"]:
                mrp_match = self.mrp_pattern.search(text)
                if mrp_match:
                    groups = mrp_match.groupdict()
                    extracted["mrp"] = {
                        "value": self._clean_number(groups["mrp_val"]),
                        "currency": "INR",
                        "tax_inclusive_stated": bool(groups["tax_clause"]),
                        "unit_sale_price": {
                            "value": self._clean_number(groups["usp_val"]) if groups.get("usp_val") else None,
                            "unit": groups.get("usp_unit")
                        } if groups.get("usp_val") else None,
                        "confidence": conf,
                        "bounding_box": box,
                        "raw_line": text
                    }

            # --- Check Net Quantity ---
            if not extracted["net_quantity"]:
                qty_match = self.net_qty_pattern.search(text)
                if qty_match:
                    groups = qty_match.groupdict()
                    raw_unit = groups["qty_unit"].lower()
                    is_legal_unit = raw_unit in LEGAL_SI_UNITS
                    extracted["net_quantity"] = {
                        "value": self._clean_number(groups["qty_val"]),
                        "unit": raw_unit,
                        "is_statutory_unit_legal": is_legal_unit,
                        "confidence": conf,
                        "bounding_box": box,
                        "raw_line": text
                    }

            # --- Check Dates (Uses finditer to catch multiple dates on a single line) ---
            for date_match in self.date_pattern.finditer(text):
                groups = date_match.groupdict()
                extracted["dates"].append({
                    "type": groups["date_type"].upper(),
                    "date_str": groups["date_val"].strip(),
                    "confidence": conf,
                    "bounding_box": box,
                    "raw_line": text
                })

            # --- Check Consumer Care ---
            for care_match in self.consumer_care_pattern.finditer(text):
                g = care_match.groupdict()
                if g.get("phone"):
                    consumer_phones.append({
                        "number": g["phone"],
                        "bounding_box": box,
                        "confidence": conf
                    })
                if g.get("email"):
                    consumer_emails.append({
                        "email": g["email"],
                        "bounding_box": box,
                        "confidence": conf
                    })

            # --- Check FSSAI ---
            if not extracted["fssai_license"]:
                fssai_m = self.fssai_pattern.search(text)
                if fssai_m:
                    extracted["fssai_license"] = {
                        "license_number": fssai_m.group("fssai_lic"),
                        "bounding_box": box,
                        "confidence": conf,
                        "raw_line": text
                    }

            # --- Check Country of Origin ---
            if not extracted["country_of_origin"]:
                coo_m = self.coo_pattern.search(text)
                if coo_m:
                    extracted["country_of_origin"] = {
                        "country": coo_m.group("country").strip(),
                        "bounding_box": box,
                        "confidence": conf,
                        "raw_line": text
                    }

        if consumer_phones or consumer_emails:
            extracted["customer_care"] = {
                "phones": consumer_phones,
                "emails": consumer_emails
            }

        return extracted


# =============================================================================
# Legacy & Route Compatibility Adapter: DeclarationExtractor
# =============================================================================
class DeclarationExtractor:
    """
    Maintains 100% backward compatibility for existing FastAPI routes
    (inspection_routes.py, scanner_routes.py, ocr_service.py).
    """

    _statutory_extractor = StatutoryExtractor()

    @staticmethod
    def _clean_text(text: str) -> str:
        """Removes duplicate whitespace and normalizes common OCR typos."""
        t = re.sub(r'[\r\t]', ' ', text)
        t = re.sub(r'\s+', ' ', t)
        return t.strip()

    @staticmethod
    def _find_matching_detection(val: str, detections: List[Dict[str, Any]]) -> Tuple[Optional[List[int]], float, str]:
        """Finds best matching detection for bounding box and confidence."""
        if not val or not detections:
            return None, 0.0, ""

        val_clean = re.sub(r'[^\w\d]', '', val).upper()
        if not val_clean:
            return None, 0.0, ""

        best_bbox = None
        best_conf = 0.0
        best_variant = ""
        max_overlap_score = 0.0

        for d in detections:
            d_text = d.get("text", "")
            d_clean = re.sub(r'[^\w\d]', '', d_text).upper()
            if not d_clean:
                continue

            if val_clean in d_clean or d_clean in val_clean:
                overlap = min(len(val_clean), len(d_clean)) / max(len(val_clean), len(d_clean), 1)
                if overlap > max_overlap_score:
                    max_overlap_score = overlap
                    best_bbox = d.get("bbox") or d.get("bounding_box")
                    best_conf = float(d.get("confidence", 0.0))
                    best_variant = d.get("variant", "")

        return best_bbox, best_conf, best_variant

    @classmethod
    def parse_declarations(
        cls,
        raw_text: str,
        detections: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Parses declarations into the dictionary format expected by the legacy Rule Engine.
        Utilizes StatutoryExtractor internally for robust named-group regex extraction.
        """
        detections = detections or []
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

        # Convert detections or raw lines into structured OCR records
        ocr_records = detections if detections else [{"text": line, "confidence": 0.90, "bounding_box": []} for line in lines]
        parsed = cls._statutory_extractor.extract_declarations(ocr_records)

        declarations: Dict[str, Dict[str, Any]] = {}

        def record_field(field_name: str, value: Optional[str], default_conf: float = 0.0, custom_bbox: Optional[Any] = None, **extra):
            bbox, conf, variant = cls._find_matching_detection(value or "", detections)
            if custom_bbox:
                bbox = custom_bbox
            final_conf = max(conf, default_conf if value else 0.0)
            declarations[field_name] = {
                "value": value,
                "normalized_value": value,
                "confidence": round(final_conf, 1),
                "bbox": bbox,
                "bounding_box": bbox,
                "detected": bool(value),
                "status": "detected" if value else "not_detected",
                **extra
            }

        # 1. MRP
        if parsed.get("mrp"):
            mrp_data = parsed["mrp"]
            record_field(
                "mrp",
                f"₹{mrp_data['value']:.2f}",
                default_conf=mrp_data.get("confidence", 95.0),
                custom_bbox=mrp_data.get("bounding_box"),
                numeric_value=mrp_data["value"],
                tax_inclusive=mrp_data.get("tax_inclusive_stated", False),
                unit_sale_price=mrp_data.get("unit_sale_price")
            )
        else:
            record_field("mrp", None)

        # 2. Net Quantity
        if parsed.get("net_quantity"):
            qty_data = parsed["net_quantity"]
            record_field(
                "net_quantity",
                f"{qty_data['value']} {qty_data['unit']}",
                default_conf=qty_data.get("confidence", 95.0),
                custom_bbox=qty_data.get("bounding_box"),
                numeric_value=qty_data["value"],
                unit=qty_data["unit"],
                is_legal_unit=qty_data.get("is_statutory_unit_legal", True)
            )
        else:
            record_field("net_quantity", None)

        # 3. Dates
        mfd_val, exp_val = None, None
        for d in parsed.get("dates", []):
            if d["type"] in ["MFD", "MFG", "PKD", "PACKED"] and not mfd_val:
                mfd_val = d["date_str"]
            elif d["type"] in ["EXP", "EXPIRY", "USE BY", "BEST BEFORE"] and not exp_val:
                exp_val = d["date_str"]

        record_field("manufacturing_date", mfd_val)
        record_field("expiry_date", exp_val)

        # 4. Customer Care
        care_str = None
        if parsed.get("customer_care"):
            phones = [p["number"] for p in parsed["customer_care"].get("phones", [])]
            emails = [e["email"] for e in parsed["customer_care"].get("emails", [])]
            care_str = " | ".join(phones + emails) if (phones or emails) else None
        record_field("consumer_care", care_str)

        # 5. FSSAI & COO
        record_field("fssai_license", parsed["fssai_license"]["license_number"] if parsed.get("fssai_license") else None)
        record_field("country_of_origin", parsed["country_of_origin"]["country"] if parsed.get("country_of_origin") else None)

        return declarations


# =============================================================================
# Verification Test Harness (__main__)
# =============================================================================
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
