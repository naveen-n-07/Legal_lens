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

    @staticmethod
    def extract_mrp(text: str) -> Optional[float]:
        """
        Extracts Maximum Retail Price, coercing noisy currency symbols into numbers.
        """
        if not text:
            return None
            
        # Standardize currency symbols (₹, RS., Rs, R., etc.)
        text = re.sub(r'(?i)(rs\.?|₹|\?|rupees|inr)\s*', 'Rs.', text)
        
        # 1. Look for explicit Rs. followed by digits (allowing for comma separators and decimals)
        match = re.search(r'Rs\.\s*([\d,]+\.?\d*)', text)
        if match:
            val_str = match.group(1).replace(',', '')
            # Try to catch optical confusions in decimals if necessary, but float conversion handles the rest
            try:
                return float(val_str)
            except ValueError:
                pass
                
        # 2. Fallback: If MRP is found, grab the next logical numeric string
        if re.search(r'(?i)\bmrp\b', text):
            # Disambiguate common errors (e.g., MRP 2S0.00 -> 250.00)
            words = text.split()
            for word in words:
                if re.match(r'^[\dOISB,]+\.?\d*$', word):
                    fixed_word = OCRPostProcessor.disambiguate_numeric(word).replace(',', '')
                    try:
                        return float(fixed_word)
                    except ValueError:
                        continue
        return None

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
