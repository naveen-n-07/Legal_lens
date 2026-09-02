"""
declaration_extractor.py - Deterministic Legal Metrology Statutory Declaration Parser (Rules 2011)
Supports multi-line, split OCR text, spatial proximity matching, and structured extraction.
"""

import re
from typing import Dict, Any, Optional, List, Tuple

from app.rules.normalization import DataNormalizer

class DeclarationExtractor:

    @staticmethod
    def _clean_text(text: str) -> str:
        """Removes duplicate whitespace and normalizes common OCR typos."""
        t = re.sub(r'[\r\t]', ' ', text)
        t = re.sub(r'\s+', ' ', t)
        return t.strip()

    @staticmethod
    def _find_matching_detection(val: str, detections: List[Dict[str, Any]]) -> Tuple[Optional[List[int]], float, str]:
        """
        Finds the best matching OCR detection for an extracted value to retrieve its bounding box and confidence.
        """
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
                    best_bbox = d.get("bbox")
                    best_conf = float(d.get("confidence", 0.0))
                    best_variant = d.get("variant", "")

        return best_bbox, best_conf, best_variant

    @staticmethod
    def parse_declarations(
        raw_text: str,
        detections: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Parses raw text and OCR bounding box detections to extract mandatory Legal Metrology declarations.
        Returns a structured dictionary where EVERY declaration field is represented with:
        - value: str or None
        - normalized_value: str or None
        - numeric_value: float or None
        - unit: str or None
        - date_obj: date or None
        - confidence: float (0.0 to 100.0)
        - bbox: [x1, y1, x2, y2] or None
        - bounding_box: [x1, y1, x2, y2] or None
        - source_text: str or None
        - detected: bool
        - status: 'detected' | 'not_detected' | 'low_confidence' | 'needs_review'
        """
        detections = detections or []
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        full_text = " \n ".join(lines)
        full_text_upper = full_text.upper()

        declarations: Dict[str, Dict[str, Any]] = {}

        def record_field(field_name: str, value: Optional[str], default_conf: float = 0.0, custom_bbox: Optional[List[int]] = None):
            if value:
                val_str = str(value).strip()
                bbox, conf, variant = DeclarationExtractor._find_matching_detection(val_str, detections)
                final_bbox = custom_bbox if custom_bbox is not None else bbox
                final_conf = round(conf if conf > 0 else default_conf, 2)
                
                if final_conf >= 90.0:
                    status = "detected"
                elif final_conf >= 75.0:
                    status = "detected"
                else:
                    status = "low_confidence"

                norm_data = DataNormalizer.normalize_field(field_name, val_str)

                declarations[field_name] = {
                    "value": val_str,
                    "normalized_value": norm_data.get("normalized_value"),
                    "numeric_value": norm_data.get("numeric_value"),
                    "unit": norm_data.get("unit"),
                    "date_obj": norm_data.get("date_obj"),
                    "confidence": final_conf,
                    "bbox": final_bbox,
                    "bounding_box": final_bbox,
                    "source_text": val_str,
                    "extraction_method": "regex_multi_pass_consensus",
                    "detected": True,
                    "status": status,
                    "variant": variant
                }
            else:
                declarations[field_name] = {
                    "value": None,
                    "normalized_value": None,
                    "numeric_value": None,
                    "unit": None,
                    "date_obj": None,
                    "confidence": 0.0,
                    "bbox": None,
                    "bounding_box": None,
                    "source_text": None,
                    "extraction_method": "not_detected",
                    "detected": False,
                    "status": "not_detected",
                    "variant": ""
                }

        # -------------------------------------------------------------
        # 1. MRP (Maximum Retail Price) & Inclusive of Taxes
        # -------------------------------------------------------------
        mrp_val = None
        mrp_bbox = None
        mrp_conf = 0.0

        # Pattern 1: Inline MRP (e.g. MRP Rs. 55.00 / MRP ₹55.00 / M.R.P. 10.00 / "MRPRS.10.00 / MKPR: 55.00 / MKP: 55)
        mrp_pattern = re.compile(
            r'(?:M\.?R\.?P\.?|MAX(?:IMUM)?\s*RETAIL\s*PRICE|MKPR|MKP|M\.K\.P\.R|M\.K\.P|M\.R\.P)\s*[\:\.\-]?\s*(?:RS\.?|INR|₹)?\s*(\d+(?:\.\d{1,2})?)',
            re.IGNORECASE
        )
        for i, line in enumerate(lines):
            match = mrp_pattern.search(line)
            if match:
                mrp_val = f"₹{match.group(1)}"
                if i < len(detections):
                    mrp_bbox = detections[i].get("bbox")
                    mrp_conf = float(detections[i].get("confidence", 85.0))
                break

        # Pattern 2: Multi-line MRP (near MRP / MKP / MKPR / INCLUSIVE OF TAXES keyword)
        if not mrp_val:
            for i, line in enumerate(lines):
                line_up = line.upper()
                if re.search(r'\b(M\.?R\.?P\.?|MKPR|MKP|M\.K\.P|M\.K\.P\.R|RETAIL\s*PRICE|INCL[U\.\w\s]*TAX)\b', line_up):
                    # Check current and adjacent 3 lines for standalone decimal price like 55.00, 10.00, Rs. 55
                    for j in range(max(0, i - 1), min(i + 4, len(lines))):
                        cand = lines[j]
                        # Look for price candidate (e.g. 55.00, 10.00, Rs. 55)
                        p_match = re.search(r'^(?:RS\.?|₹)?\s*(\d{1,5}(?:\.\d{1,2})?)$', cand.strip(), re.IGNORECASE)
                        if not p_match:
                            p_match = re.search(r'(?:RS\.?|₹)\s*(\d{1,5}(?:\.\d{1,2})?)', cand, re.IGNORECASE)
                        if p_match and not re.search(r'(?:PER|USP|\/G|\/KG|\/ML|PKD|USE|BY|MFD|BATCH)', cand, re.IGNORECASE):
                            val_num = float(p_match.group(1))
                            if 0.5 <= val_num <= 100000:
                                mrp_val = f"₹{p_match.group(1)}"
                                if j < len(detections):
                                    mrp_bbox = detections[j].get("bbox")
                                    mrp_conf = float(detections[j].get("confidence", 85.0))
                                break
                    if mrp_val:
                        break

        # Pattern 3: Standalone price with currency symbol or standard format (e.g. ₹55.00)
        if not mrp_val:
            curr_match = re.search(r'[₹]\s*(\d+(?:\.\d{1,2})?)', full_text)
            if curr_match:
                mrp_val = f"₹{curr_match.group(1)}"

        record_field("mrp", mrp_val, default_conf=88.0, custom_bbox=mrp_bbox)

        # MRP Inclusive of Taxes
        incl_taxes = False
        if re.search(r'INCL[U\.\w\s]*TAX', full_text_upper) or re.search(r'INCLUSIVE\s*OF\s*ALL\s*TAXES', full_text_upper):
            incl_taxes = True
        record_field("mrp_inclusive_tax", "Inclusive of all taxes" if incl_taxes else None, default_conf=92.0 if incl_taxes else 0.0)

        # -------------------------------------------------------------
        # 2. Net Quantity & Unit of Measurement
        # -------------------------------------------------------------
        net_qty_val = None
        unit_val = None

        # Check compound quantity like 54g+9gEXTRA= 63g or 54g + 9g = 63g
        for i, line in enumerate(lines):
            if re.search(r'\b(NET\s*(?:WEIGHT|WT|QTY|QUANTITY))\b', line, re.IGNORECASE):
                combined_snippet = " ".join(lines[i:min(i + 3, len(lines))])
                all_qtys = re.findall(r'\b(\d+(?:\.\d+)?\s*(?:g|kg|ml|l|ltr|gm|gms|n|units?))\b', combined_snippet, re.IGNORECASE)
                if all_qtys:
                    valid_qtys = [q for q in all_qtys if not re.search(r'%', q)]
                    if valid_qtys:
                        net_qty_val = valid_qtys[-1].strip()
                        break

        if not net_qty_val:
            qty_match = re.search(
                r'(?:NET\s*(?:QUANTITY|QTY|WEIGHT|WT\.?|CONTENT))\s*[\:\.\-]?\s*(\d+(?:\.\d+)?\s*(?:g|kg|ml|l|ltr|gm|gms|n|units?|tablets?|capsules?))\b',
                full_text,
                re.IGNORECASE
            )
            if qty_match:
                net_qty_val = qty_match.group(1).strip()

        if not net_qty_val:
            standalone_qty = re.search(r'\b(\d+(?:\.\d+)?\s*(?:g|kg|ml|l|gm|gms|n))\b', full_text, re.IGNORECASE)
            if standalone_qty:
                ctx = full_text[max(0, standalone_qty.start()-10):standalone_qty.end()+10].upper()
                if not any(k in ctx for k in ["PER", "USP", "COCOA", "FAT", "CARB", "SALT", "%"]):
                    net_qty_val = standalone_qty.group(1).strip()

        if net_qty_val:
            unit_match = re.search(r'(kg|g|gm|gms|ml|l|ltr|n|units?|tablets?|capsules?)', net_qty_val, re.IGNORECASE)
            if unit_match:
                unit_val = unit_match.group(1).lower()

        record_field("net_quantity", net_qty_val, default_conf=90.0)
        record_field("unit_of_measurement", unit_val, default_conf=92.0)

        # -------------------------------------------------------------
        # 3. Unit Sale Price (USP)
        # -------------------------------------------------------------
        usp_val = None
        usp_match = re.search(r'(?:USP|UNIT\s*SALE\s*PRICE|\bRS\.?|\b₹)?\s*[\:\.\(]?\s*([0-9\.]+\s*(?:PER|\/)\s*(?:G|KG|ML|L|N|GM|PIECE|UNIT))', full_text_upper)
        if usp_match:
            usp_val = f"Rs. {usp_match.group(1).strip('()')}"
        elif re.search(r'([0-9\.]+\s*PER\s*G)', full_text_upper):
            usp_match2 = re.search(r'([0-9\.]+\s*PER\s*G)', full_text_upper)
            usp_val = f"Rs. {usp_match2.group(1)}"
        record_field("unit_sale_price", usp_val, default_conf=86.0)

        # -------------------------------------------------------------
        # 4. Dates: Manufacturing / Packing Date & Expiry / Use By
        # -------------------------------------------------------------
        mfg_date_val = None
        exp_date_val = None

        date_pattern = re.compile(
            r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{1,2}[\/\-]\d{2,4}|(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s*[\'\`\-]?\s*\d{2,4})\b',
            re.IGNORECASE
        )

        for i, line in enumerate(lines):
            line_up = line.upper()

            if re.search(r'\b(PKD|MFD|MFG|PACKED\s*ON|DATE\s*OF\s*MFG|DATE\s*OF\s*PACKING)\b', line_up):
                d_m = date_pattern.search(line_up)
                if d_m:
                    mfg_date_val = d_m.group(1)
                else:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        d_next = date_pattern.search(lines[j])
                        if d_next and not re.search(r'(USE|EXP|BEST)', lines[j], re.IGNORECASE):
                            mfg_date_val = d_next.group(1)
                            break

            if re.search(r'\b(USE\s*BY|EXPIRY|EXP\.?|BEST\s*BEFORE)\b', line_up):
                d_e = date_pattern.search(line_up)
                if d_e:
                    exp_date_val = d_e.group(1)
                else:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        d_next = date_pattern.search(lines[j])
                        if d_next:
                            exp_date_val = d_next.group(1)
                            break

        if not mfg_date_val:
            all_dates = date_pattern.findall(full_text)
            if len(all_dates) >= 1:
                mfg_date_val = all_dates[0]
            if len(all_dates) >= 2 and not exp_date_val:
                exp_date_val = all_dates[1]

        if mfg_date_val:
            mfg_date_val = re.sub(r'(\d{2})[\/\-](\d{2})1(\d{2})', r'\1/\2/\3', mfg_date_val)
        if exp_date_val:
            exp_date_val = re.sub(r'(\d{2})[\/\-](\d{2})1(\d{2})', r'\1/\2/\3', exp_date_val)

        record_field("manufacturing_date", mfg_date_val, default_conf=88.0)
        record_field("expiry_date", exp_date_val, default_conf=88.0)

        # -------------------------------------------------------------
        # 5. Batch / Lot Number
        # -------------------------------------------------------------
        batch_val = None
        for i, line in enumerate(lines):
            line_up = line.upper()
            if re.search(r'\b(BATCH\s*(?:NO\.?|NUMBER)?|LOT\s*(?:NO\.?|NUMBER)?|B\.NO\.?)\b', line_up):
                for cand_line in lines[i:min(i + 3, len(lines))]:
                    tokens = cand_line.replace(":", " ").replace(".", " ").split()
                    for tok in tokens:
                        tok_clean = tok.strip()
                        if re.match(r'^[A-Z0-9]{4,12}$', tok_clean):
                            if not re.search(r'(BATCH|LOT|PKD|USE|EXP|MRP|FSSAI|LIC|TAX)', tok_clean, re.IGNORECASE):
                                if any(c.isdigit() for c in tok_clean) and tok_clean not in ["2024", "2025", "2026", "2027"]:
                                    batch_val = tok_clean
                                    break
                    if batch_val:
                        break
            if batch_val:
                break

        if not batch_val:
            code_match = re.search(r'\b([A-Z]{2,4}\d{2}[A-Z]\d{2,5}|\d{4}[A-Z]\d{2,4})\b', full_text)
            if code_match:
                batch_val = code_match.group(1)

        record_field("batch_number", batch_val, default_conf=84.0)

        # -------------------------------------------------------------
        # 6. Manufacturer, Packer, Marketer & Importer Details
        # -------------------------------------------------------------
        mfg_name = None
        packer_name = None
        marketer_name = None
        importer_name = None

        mfg_match = re.search(r'(?:MANUFACTURED\s*BY|MFG\s*BY|MFD\s*BY|PRODUCED\s*BY)\s*[\:\.\-]?\s*([A-Z0-9\s\,\.\-\&]{3,80}?)(?=(?:PACKED|MARKETED|IMPORTED|NET|MRP|CONSUMER|LIC|CIN|GSTIN|\n|$))', full_text_upper)
        if mfg_match:
            mfg_name = DeclarationExtractor._clean_text(mfg_match.group(1))

        mkt_match = re.search(r'(?:MARKETED\s*BY|MKT\s*BY)\s*[\:\.\-]?\s*([A-Z0-9\s\,\.\-\&]{3,80}?)(?=(?:MANUFACTURED|PACKED|IMPORTED|NET|MRP|CONSUMER|LIC|STORE|\n|$))', full_text_upper)
        if mkt_match:
            marketer_name = DeclarationExtractor._clean_text(mkt_match.group(1))

        pkr_match = re.search(r'(?:PACKED\s*BY|PACKER)\s*[\:\.\-]?\s*([A-Z0-9\s\,\.\-\&]{3,80}?)(?=(?:MANUFACTURED|MARKETED|IMPORTED|NET|MRP|CONSUMER|\n|$))', full_text_upper)
        if pkr_match:
            packer_name = DeclarationExtractor._clean_text(pkr_match.group(1))

        imp_match = re.search(r'(?:IMPORTED\s*BY|IMPORTER)\s*[\:\.\-]?\s*([A-Z0-9\s\,\.\-\&]{3,80}?)(?=(?:MANUFACTURED|MARKETED|PACKED|NET|MRP|CONSUMER|\n|$))', full_text_upper)
        if imp_match:
            importer_name = DeclarationExtractor._clean_text(imp_match.group(1))

        primary_manufacturer = mfg_name or marketer_name or packer_name
        record_field("manufacturer", primary_manufacturer, default_conf=88.0)
        record_field("packer", packer_name, default_conf=85.0)
        record_field("marketer", marketer_name, default_conf=87.0)
        record_field("importer", importer_name, default_conf=85.0)

        # -------------------------------------------------------------
        # 7. Country of Origin
        # -------------------------------------------------------------
        country_val = None
        if re.search(r'(?:MADE\s*IN\s*INDIA|PRODUCT\s*OF\s*INDIA|COUNTRY\s*OF\s*ORIGIN\s*[\:\-]?\s*INDIA)', full_text_upper):
            country_val = "India"
        else:
            origin_match = re.search(r'(?:COUNTRY\s*OF\s*ORIGIN|MADE\s*IN)\s*[\:\.\-]?\s*([A-Z\s]{3,20})', full_text_upper)
            if origin_match:
                country_val = origin_match.group(1).strip()
            elif primary_manufacturer and any(city in full_text_upper for city in ["MUMBAI", "DELHI", "BENGALURU", "BANGALORE", "KOLKATA", "CHENNAI", "HYDERABAD", "PUNE", "AHMEDABAD"]):
                country_val = "India (Inferred from Registered Address)"

        record_field("country_of_origin", country_val, default_conf=92.0 if country_val else 0.0)

        # -------------------------------------------------------------
        # 8. Consumer Care Details (Phone, Email, Postal Address)
        # -------------------------------------------------------------
        consumer_care_full = None
        care_phone = None
        care_email = None

        phone_match = re.search(r'\b(1800[\s\-]?\d{2,4}[\s\-]?\d{3,6}|1860[\s\-]?\d{2,4}[\s\-]?\d{3,6}|\+?91[\s\-]?\d{5}[\s\-]?\d{5})\b', full_text)
        if not phone_match:
            phone_merged = re.search(r'(1800\d{6,9}|1860\d{6,9})', full_text)
            if phone_merged:
                care_phone = phone_merged.group(1)
        else:
            care_phone = phone_match.group(0).replace(" ", "").replace("-", "")

        email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', full_text)
        if email_match:
            care_email = email_match.group(0)
            care_email = re.sub(r'(\.in|\.com|\.org|\.net)\d+', r'\1', care_email)

        care_match = re.search(
            r'(?:CONSUMER\s*CARE|CUSTOMER\s*CARE|FEEDBACK\s*[\/\&]?\s*COMPLAINT)\s*[\:\.\-]?\s*([A-Z0-9\s\,\.\-\@\#\n]{10,180}?)(?=(?:LIC|FSSAI|STORE|QUALITY|\n\n|$))',
            full_text_upper
        )
        if care_match:
            consumer_care_full = DeclarationExtractor._clean_text(care_match.group(0))
        elif care_phone or care_email:
            parts = []
            if care_phone: parts.append(f"Phone: {care_phone}")
            if care_email: parts.append(f"Email: {care_email}")
            consumer_care_full = " | ".join(parts)

        record_field("consumer_care", consumer_care_full, default_conf=88.0)
        record_field("consumer_care_phone", care_phone, default_conf=94.0 if care_phone else 0.0)
        record_field("consumer_care_email", care_email, default_conf=94.0 if care_email else 0.0)

        # -------------------------------------------------------------
        # 9. Generic / Commodity Name
        # -------------------------------------------------------------
        generic_name = None
        for line in lines:
            line_up = line.upper()
            if any(term in line_up for term in ["BOURBON", "FANTASY", "CHIPS", "BISCUIT", "NOODLES", "CREAM", "POTATO", "SNACKS"]):
                generic_name = DeclarationExtractor._clean_text(line)
                break

        if not generic_name:
            skip_keywords = ["MRP", "NET", "MFG", "PKD", "USE BY", "BATCH", "INGREDIENT", "NUTRITION", "CONSUMER", "LIC", "FSSAI", "STORE IN", "CONTAINS", "STARCH", "FLAVOUR"]
            for line in lines:
                if len(line) >= 4 and not any(sk in line.upper() for sk in skip_keywords):
                    generic_name = DeclarationExtractor._clean_text(line)
                    break

        record_field("generic_name", generic_name, default_conf=88.0)
        record_field("product_name", generic_name, default_conf=88.0)

        # -------------------------------------------------------------
        # 10. FSSAI License Number (for Food Commodities)
        # -------------------------------------------------------------
        fssai_val = None
        fssai_match = re.search(r'(?:FSSAI|LIC\.?\s*NO\.?|LICENSE\s*NO\.?)\s*[\:\.\-]?\s*(\d{14})', full_text_upper)
        if fssai_match:
            fssai_val = fssai_match.group(1)
        else:
            fssai_14 = re.search(r'\b(1\d{13})\b', full_text)
            if fssai_14:
                fssai_val = fssai_14.group(1)

        record_field("fssai_license", fssai_val, default_conf=92.0 if fssai_val else 0.0)

        # -------------------------------------------------------------
        # 11. Ingredients List
        # -------------------------------------------------------------
        ingredients_val = None
        ing_match = re.search(
            r'(?:INGREDIENTS|INGREDIENT)\s*[\:\.\-]?\s*([A-Z0-9\s\,\.\-\(\)\%\;\:\/]{10,250}?)(?=(?:NUTRITIONAL|CONTAINS|ALLERGEN|MFD|MFG|NET|MRP|LIC|FSSAI|BEST|STORE|\n\n|$))',
            full_text_upper
        )
        if ing_match:
            ingredients_val = DeclarationExtractor._clean_text(ing_match.group(1))
        elif "INGREDIENTS" in full_text_upper:
            for i, line in enumerate(lines):
                if "INGREDIENTS" in line.upper():
                    cand_snippet = " ".join(lines[i:min(i + 4, len(lines))])
                    ingredients_val = DeclarationExtractor._clean_text(cand_snippet.replace("INGREDIENTS:", "").replace("Ingredients:", "").strip())
                    break

        record_field("ingredients", ingredients_val, default_conf=88.0)

        # -------------------------------------------------------------
        # 12. Address (Postal Address / Factory Location)
        # -------------------------------------------------------------
        address_val = None
        addr_match = re.search(
            r'(?:REGD\.\s*OFFICE|REGISTERED\s*OFFICE|ADDRESS|PLOT\s*NO|SURVEY\s*NO|INDUSTRIAL\s*AREA|VILLAGE|ROAD|STREET|DISTRICT|TALUKA|STATE|PIN|PINCODE)\s*[\:\.\-]?\s*([A-Z0-9\s\,\.\-\#\/]{10,180}?)(?=(?:NET|MRP|MFD|PKD|USE|EXP|LIC|FSSAI|\n\n|$))',
            full_text_upper
        )
        if addr_match:
            address_val = DeclarationExtractor._clean_text(addr_match.group(0))
        elif primary_manufacturer:
            address_val = primary_manufacturer

        record_field("address", address_val, default_conf=85.0)

        # -------------------------------------------------------------
        # 13. Allergen Declaration
        # -------------------------------------------------------------
        allergen_val = None
        allergen_match = re.search(
            r'(?:ALLERGEN\s*(?:INFORMATION|DECLARATION|ADVICE)?|CONTAINS|MAY\s*CONTAIN)\s*[\:\.\-]?\s*([A-Z0-9\s\,\.\-\(\)]{5,120}?)(?=(?:MFD|PKD|USE|EXP|MRP|NET|STORE|\n\n|$))',
            full_text_upper
        )
        if allergen_match:
            allergen_val = DeclarationExtractor._clean_text(allergen_match.group(0))
        elif any(k in full_text_upper for k in ["CONTAINS WHEAT", "CONTAINS MILK", "CONTAINS SOY", "CONTAINS NUTS", "CONTAINS GLUTEN", "CONTAINS PEANUTS"]):
            for line in lines:
                if "CONTAINS" in line.upper():
                    allergen_val = DeclarationExtractor._clean_text(line)
                    break

        record_field("allergen_declaration", allergen_val, default_conf=90.0 if allergen_val else 0.0)

        # -------------------------------------------------------------
        # 14. Vegetarian / Non-Vegetarian Declaration
        # -------------------------------------------------------------
        veg_val = None
        if "100% VEGETARIAN" in full_text_upper or "VEG" in full_text_upper or "GREEN DOT" in full_text_upper:
            veg_val = "100% Vegetarian (Green Symbol)"
        elif "NON-VEG" in full_text_upper or "BROWN DOT" in full_text_upper:
            veg_val = "Non-Vegetarian (Brown Symbol)"

        record_field("veg_nonveg_declaration", veg_val, default_conf=90.0 if veg_val else 0.0)

        return declarations
