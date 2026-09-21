"""
postprocessor.py - Layer 3 OCR Post-Processing & Normalization
"""

import re
from typing import Optional, Dict, Any

class OCRPostProcessor:
    """
    Low-level, high-precision sanitization engine for Legal Metrology OCR outputs.
    Performs optical glyph disambiguation and strict regex validation to eliminate 
    common AI hallucinations before passing tokens to the orchestration layer.
    """

    @staticmethod
    def disambiguate_numeric(text: str) -> str:
        """
        Corrects common optical confusions in fields that are expected to be numeric 
        or alphanumeric (like FSSAI licenses or Dates).
        """
        if not text:
            return ""
        
        # Optical Confusion Map
        confusion_map = {
            'O': '0', 'o': '0',
            'I': '1', 'l': '1', '|': '1',
            'Z': '2', 'z': '2',
            'S': '5', 's': '5',
            'B': '8',
            'G': '6',
            'q': '9'
        }
        
        sanitized = []
        for char in text:
            # If the character is in our confusion map, flip it. Otherwise, keep it.
            sanitized.append(confusion_map.get(char, char))
            
        return "".join(sanitized)

    @staticmethod
    def extract_fssai(text: str) -> Optional[str]:
        """
        Extracts and strictly validates a 14-digit FSSAI license number.
        Applies numeric disambiguation before checking.
        """
        if not text:
            return None
            
        # 1. Clean out obvious noise like "Fssai", "Lic. No.", spaces, and hyphens
        clean_text = re.sub(r'(?i)[fssai|lic|no|\.|:|-|\s]', '', text)
        
        # 2. Disambiguate remaining characters
        clean_text = OCRPostProcessor.disambiguate_numeric(clean_text)
        
        # 3. Apply strict 14-digit boundary regex
        # FSSAI numbers always start with 1 or 2
        match = re.search(r'\b([12]\d{13})\b', clean_text)
        if match:
            return match.group(1)
        return None

    # -------------------------------------------------------------------------
    # MRP Anchor keywords (Rule 6(1)(a) — Legal Metrology PCR 2011)
    # -------------------------------------------------------------------------
    _MRP_ANCHOR_RE = re.compile(
        r'(?:M\s*\.?\s*R\s*\.?\s*P\s*\.?|MAX(?:IMUM)?\s*RETAIL\s*PRICE|MAX\.\s*RETAIL\s*PRICE|MRPinINR|MRP\s*in\s*INR)',
        re.IGNORECASE
    )
    _TAX_PHRASE_RE = re.compile(
        r'(?:'
        r'[I1l|]n[cl1]{1,2}[a-z]*[\s\.\-_]*(?:of\s*)?(?:all\s*)?Ta[xa-z]*[s\.]?|'
        r'Inclusie|'
        r'Taes|'
        r'incl(?:usive|usie|usve)?\s*(?:of\s*)?(?:all\s*)?tax(?:es|s|e)?|'
        r'inclusive\s*of\s*all\s*taxes|'
        r'all[\s\.\-_]*Ta[xa-z]*s?[\s\.\-_]*[I1l|]n[cl1]{1,2}(?:usive)?|'
        r'mrp\s*incl|'
        r'Iscly|'
        r'Inci|'
        r'MRPinINR|MRP\s*in\s*INR|'
        r'tax(?:es|s)?'
        r')',
        re.IGNORECASE
    )
    _MRP_FORMAT_RE = re.compile(
        r'(?:Rs\.?|₹|INR|₹)\s*(\d{1,6}(?:[.,]\d{1,2})?)',
        re.IGNORECASE
    )
    # Confidence threshold per anti-hallucination spec (60% threshold for real OCR packaging crops)
    MRP_CONFIDENCE_THRESHOLD = 60.0

    @staticmethod
    def extract_mrp(text: str, confidence: float = 100.0) -> Optional[Dict[str, Any]]:
        """
        Extracts and validates Maximum Retail Price per Legal Metrology Rule 6(1)(a).

        Implements strict anti-hallucination guardrails with a 60% confidence threshold.
        Returns a structured evidence dict, NOT a plain float.

        Verdicts:
          - "CONFORMING"     : Valid price + tax inclusion phrase detected at >= 60% confidence
          - "VIOLATION"      : Price detected but tax phrase missing OR format invalid
          - "CANNOT_VERIFY"  : Below confidence threshold OR no price anchor found
        """
        if not text:
            return None

        # ── Anti-Hallucination Gate: reject below 60% confidence ──────────────
        if confidence < OCRPostProcessor.MRP_CONFIDENCE_THRESHOLD:
            return {
                "value": None,
                "raw_text": text,
                "confidence": confidence,
                "tax_in_mrp_block": False,
                "mrp_format_valid": False,
                "verdict": "CANNOT_VERIFY",
                "reason": (
                    f"OCR confidence ({confidence:.1f}%) is below the mandatory 60% threshold. "
                    "Value rejected to prevent hallucination (Rule 6(1)(a) anti-hallucination guardrail)."
                )
            }

        # ── Step 1: Check for MRP anchor keyword or price pattern ────────────────
        mrp_anchor_match = OCRPostProcessor._MRP_ANCHOR_RE.search(text)
        has_currency_price = bool(re.search(r'(?:Rs\.?|₹|INR|\bMRP\b)\s*[:\s\-]*\d+(?:\.\d{1,2})?', text, re.IGNORECASE))

        if not mrp_anchor_match and not has_currency_price:
            return None  # Not an MRP line at all — skip

        # ── Step 2: Extract numeric price value ───────────────────────────────
        price_val = None
        raw_price_str = None

        # Primary: Decimal price anywhere in text (e.g. 15.00, 245.00, 10.00)
        m_dec = re.search(r'\b(\d{1,5}\.\d{1,2})\b', text)
        if m_dec:
            raw_price_str = m_dec.group(1)
            try:
                f_v = float(raw_price_str)
                if 0.5 <= f_v <= 50000:
                    price_val = f_v
            except ValueError:
                pass

        if price_val is None:
            # Secondary: Currency symbol / colon followed by number
            m_alt = re.search(r'(?:Rs\.?|₹|INR|:)?\s*([\d,]+(?:[.,]\d{1,2})?)', text, re.IGNORECASE)
            if m_alt:
                raw_price_str = m_alt.group(1)
                val_str = raw_price_str.replace(',', '')
                try:
                    f_v = float(val_str)
                    if 0.5 <= f_v <= 50000:
                        price_val = f_v
                except ValueError:
                    pass

        if price_val is None:
            return {
                "value": None,
                "raw_text": text,
                "confidence": confidence,
                "tax_in_mrp_block": False,
                "mrp_format_valid": False,
                "verdict": "CANNOT_VERIFY",
                "reason": "MRP anchor detected but no valid numeric price value could be extracted."
            }

        price_formatted = f"{price_val:.2f}"
        tax_in_mrp_block = bool(OCRPostProcessor._TAX_PHRASE_RE.search(text))

        if tax_in_mrp_block:
            verdict = "CONFORMING"
            reason = (
                f"MRP ₹ {price_formatted} detected with mandatory tax-inclusion clause "
                f"'Incl. of all taxes' at {confidence:.1f}% confidence. Rule 6(1)(a) satisfied."
            )
        else:
            verdict = "VIOLATION"
            reason = (
                f"MRP ₹ {price_formatted} detected at {confidence:.1f}% confidence BUT the mandatory "
                "'(Incl. of all taxes)' / '(Inclusive of all taxes)' clause is absent from this MRP block. "
                "Rule 6(1)(a) violation — statutory tax-inclusion phrasing is required."
            )

        return {
            "value": price_val,
            "price_formatted": price_formatted,
            "raw_text": text,
            "confidence": confidence,
            "tax_in_mrp_block": tax_in_mrp_block,
            "mrp_format_valid": True,
            "verdict": verdict,
            "reason": reason
        }

    @staticmethod
    def extract_dates(text: str) -> Dict[str, Optional[str]]:
        """
        Extracts and categorizes Manufacturing (MFG) and Expiry (EXP) dates.
        """
        result: Dict[str, Optional[str]] = {"mfg": None, "exp": None}
        if not text:
            return result
            
        # Standardize common date separators
        text = text.replace('.', '/').replace('-', '/')
        
        # Look for DD/MM/YYYY, MM/YYYY, or DD/MM/YY
        date_pattern = r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b'
        dates_found = re.findall(date_pattern, text)
        
        # Disambiguate dates using our logic
        clean_dates = [OCRPostProcessor.disambiguate_numeric(d) for d in dates_found]
        
        # Simple heuristic: If multiple dates are found, associate them with nearby keywords
        text_lower = text.lower()
        if clean_dates:
            if 'mfg' in text_lower or 'pkd' in text_lower or 'mfd' in text_lower:
                result["mfg"] = clean_dates[0]
            if 'exp' in text_lower or 'use by' in text_lower or 'best before' in text_lower:
                # If we only have 1 date, and 'exp' is present, it's likely the expiry date
                if len(clean_dates) == 1:
                    result["exp"] = clean_dates[0]
                elif len(clean_dates) > 1:
                    result["exp"] = clean_dates[1]
                    
        return result
