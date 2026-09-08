"""
normalization.py - Generic Declarative Data Normalization Utilities for Label Fields
Normalizes whitespace, currency symbols (₹ / Rs / INR), numeric quantities, standard units,
and dates (into datetime.date objects) without altering original raw OCR text.
"""

import re
from datetime import datetime, date
from typing import Any, Dict, Optional, Tuple

class DataNormalizer:

    @staticmethod
    def normalize_whitespace(text: Optional[str]) -> str:
        """Trims whitespace and collapses multiple spaces/tabs/newlines."""
        if not text:
            return ""
        t = re.sub(r'[\r\t\n]', ' ', str(text))
        t = re.sub(r'\s+', ' ', t)
        return t.strip()

    @staticmethod
    def normalize_currency(text: Optional[str]) -> Tuple[Optional[str], Optional[float]]:
        """
        Normalizes currency expressions like 'MRP Rs. 55.00', '₹55.00', 'Rs 55', '55.00/-'
        Returns formatted currency string (e.g., '₹55.00') and float value (55.0).
        """
        if not text:
            return None, None
        
        t = DataNormalizer.normalize_whitespace(text)
        # Extract numeric float part
        m = re.search(r'(\d+(?:\.\d{1,2})?)', t)
        if m:
            num_val = float(m.group(1))
            return f"₹{num_val:.2f}" if num_val % 1 != 0 else f"₹{int(num_val)}", num_val
        return t, None

    @staticmethod
    def normalize_unit(unit: Optional[str]) -> str:
        """
        Normalizes metric and count units to standard canonical symbols (g, kg, mg, ml, l, count, n).
        """
        if not unit:
            return ""
        u = unit.strip().lower()
        mapping = {
            "gm": "g",
            "gms": "g",
            "gram": "g",
            "grams": "g",
            "g": "g",
            "kg": "kg",
            "kgs": "kg",
            "kilogram": "kg",
            "kilograms": "kg",
            "mg": "mg",
            "milligram": "mg",
            "milligrams": "mg",
            "ml": "ml",
            "millilitre": "ml",
            "millilitres": "ml",
            "milliliter": "ml",
            "milliliters": "ml",
            "l": "l",
            "ltr": "l",
            "litre": "l",
            "litres": "l",
            "liter": "l",
            "liters": "l",
            "n": "n",
            "count": "count",
            "units": "u",
            "unit": "u",
            "u": "u",
            "tablets": "tablets",
            "tablet": "tablets",
            "capsules": "capsules",
            "capsule": "capsules",
            "piece": "piece",
            "pieces": "piece",
            "pc": "piece",
            "pcs": "piece"
        }
        return mapping.get(u, u)

    @staticmethod
    def parse_quantity(text: Optional[str]) -> Tuple[Optional[str], Optional[float], Optional[str]]:
        """
        Parses declared quantity like '500 g', '1 kg', '200ml', '54g + 9g = 63g'.
        Returns formatted representation, numeric value, and normalized unit.
        """
        if not text:
            return None, None, None
        
        t = DataNormalizer.normalize_whitespace(text)
        # Match standard numeric + unit pattern
        m = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)', t)
        if m:
            num = float(m.group(1))
            unit = DataNormalizer.normalize_unit(m.group(2))
            formatted = f"{int(num) if num.is_integer() else num} {unit}"
            return formatted, num, unit
        
        # If numeric only
        num_m = re.search(r'(\d+(?:\.\d+)?)', t)
        if num_m:
            num = float(num_m.group(1))
            return str(num), num, ""
            
        return t, None, None

    @staticmethod
    def parse_date_to_object(date_val: Any) -> Optional[date]:
        """
        Parses various standard date formats (DD/MM/YYYY, MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, Mon YYYY)
        into a real datetime.date object.
        """
        if isinstance(date_val, date):
            return date_val
        if isinstance(date_val, datetime):
            return date_val.date()
        if not date_val or not isinstance(date_val, str):
            return None
            
        s = date_val.strip()
        # Clean extra characters
        s = re.sub(r'^[^\d\w]+|[^\d\w]+$', '', s)
        
        # Format 1: DD/MM/YYYY or DD-MM-YYYY
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"]:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass

        # Format 2: MM/YYYY or MM-YYYY
        for fmt in ["%m/%Y", "%m-%Y", "%m.%Y"]:
            try:
                dt = datetime.strptime(s, fmt)
                # First day of month
                return date(dt.year, dt.month, 1)
            except ValueError:
                pass

        # Format 3: DD/MM/YY or MM/YY
        for fmt in ["%d/%m/%y", "%d-%m-%y", "%m/%y", "%m-%y"]:
            try:
                dt = datetime.strptime(s, fmt)
                return dt.date()
            except ValueError:
                pass

        # Format 4: Month name + Year (e.g., 'JAN 2026', 'October 2025', 'MAR2024', '15 JUL 2023')
        for fmt in ["%b %Y", "%B %Y", "%b-%Y", "%b/%Y", "%b '%y", "%b %y", "%b%Y", "%b%y", "%d %b %Y", "%d-%b-%Y", "%d/%b/%Y"]:
            try:
                dt = datetime.strptime(s, fmt)
                return dt.date() if "%d" in fmt else date(dt.year, dt.month, 1)
            except ValueError:
                pass

        # Substring extraction search
        m_ddmmyyyy = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', s)
        if m_ddmmyyyy:
            d_p, m_p, y_p = int(m_ddmmyyyy.group(1)), int(m_ddmmyyyy.group(2)), int(m_ddmmyyyy.group(3))
            if y_p < 100: y_p += 2000
            try:
                return date(y_p, m_p, d_p)
            except ValueError:
                pass

        m_mmyyyy = re.search(r'(\d{1,2})[\/\-\.](\d{4})', s)
        if m_mmyyyy:
            m_p, y_p = int(m_mmyyyy.group(1)), int(m_mmyyyy.group(2))
            if 1 <= m_p <= 12:
                try:
                    return date(y_p, m_p, 1)
                except ValueError:
                    pass

        return None

    @staticmethod
    def normalize_field(field_name: str, raw_value: Any) -> Dict[str, Any]:
        """
        Generic field normalizer preserving raw value and returning structured normalized data.
        """
        if raw_value is None:
            return {
                "raw_value": None,
                "normalized_value": None,
                "numeric_value": None,
                "unit": None,
                "date_obj": None
            }

        raw_str = str(raw_value).strip()
        norm_whitespace = DataNormalizer.normalize_whitespace(raw_str)

        f_lower = field_name.lower()
        
        # Currency / MRP
        if "mrp" in f_lower or "price" in f_lower:
            formatted_curr, num_val = DataNormalizer.normalize_currency(norm_whitespace)
            return {
                "raw_value": raw_str,
                "normalized_value": formatted_curr or norm_whitespace,
                "numeric_value": num_val,
                "unit": "INR",
                "date_obj": None
            }

        # Quantity
        if "quantity" in f_lower or "qty" in f_lower or "weight" in f_lower:
            formatted_qty, num_val, unit_val = DataNormalizer.parse_quantity(norm_whitespace)
            return {
                "raw_value": raw_str,
                "normalized_value": formatted_qty or norm_whitespace,
                "numeric_value": num_val,
                "unit": unit_val,
                "date_obj": None
            }

        # Unit of measurement
        if "unit" in f_lower and "price" not in f_lower:
            u_norm = DataNormalizer.normalize_unit(norm_whitespace)
            return {
                "raw_value": raw_str,
                "normalized_value": u_norm,
                "numeric_value": None,
                "unit": u_norm,
                "date_obj": None
            }

        # Dates
        if "date" in f_lower or "mfg" in f_lower or "exp" in f_lower or "pkd" in f_lower or "use_by" in f_lower or "best_before" in f_lower:
            d_obj = DataNormalizer.parse_date_to_object(norm_whitespace)
            return {
                "raw_value": raw_str,
                "normalized_value": d_obj.strftime("%d/%m/%Y") if d_obj else norm_whitespace,
                "numeric_value": None,
                "unit": None,
                "date_obj": d_obj
            }

        # FSSAI License (14 digits)
        if "fssai" in f_lower or "license" in f_lower:
            digits_only = re.sub(r'\D', '', norm_whitespace)
            return {
                "raw_value": raw_str,
                "normalized_value": digits_only if len(digits_only) == 14 else norm_whitespace,
                "numeric_value": None,
                "unit": None,
                "date_obj": None
            }

        # General text fields
        return {
            "raw_value": raw_str,
            "normalized_value": norm_whitespace,
            "numeric_value": None,
            "unit": None,
            "date_obj": None
        }
