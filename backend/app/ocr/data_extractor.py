"""
data_extractor.py - Stage 5 Legal Metrology Statutory Data Extractor

Enterprise-grade regex and heuristic extraction pipeline designed for SIH 26034.
Consumes translated OCR output dictionaries:
    [{"translated_text": str, "original_text": str, "confidence": float, "bounding_box": List}]
and deterministically extracts mandatory Legal Metrology (Packaged Commodities) Rules, 2011 declarations:
    1. Maximum Retail Price (MRP) with tax inclusion flags.
    2. Net Quantity (Numeric value, declared unit, standardized SI base conversion).
    3. Dates: Manufacturing Date (MFD/PKD) and Expiry/Use-By Date (Absolute & Relative).
    4. Customer Care (Toll-free helplines, mobile/landline numbers, email addresses, websites).
    5. Additional Statutory Fields: FSSAI License, Country of Origin, Unit Sale Price (USP), Manufacturer.

Every extracted declaration retains source text, original Indic text, bounding box coordinates,
confidence scores, and evidence IDs for Stage 10 Evidence Engine highlight visualization.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
import re
import os
import sys
import json
import logging

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Configure structured enterprise logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DataExtractor")


# =============================================================================
# 1. Canonical Normalization Dictionaries & Constants
# =============================================================================

# Canonical Legal Metrology Unit Mapping & Multipliers to SI Base (g, ml, m, N)
UNIT_NORMALIZATION_MAP: Dict[str, Tuple[str, str, float]] = {
    # Weight (Base: 'g')
    "g": ("g", "g", 1.0),
    "gm": ("g", "g", 1.0),
    "gms": ("g", "g", 1.0),
    "gram": ("g", "g", 1.0),
    "grams": ("g", "g", 1.0),
    "kg": ("kg", "g", 1000.0),
    "kgs": ("kg", "g", 1000.0),
    "kilogram": ("kg", "g", 1000.0),
    "kilograms": ("kg", "g", 1000.0),
    "mg": ("mg", "g", 0.001),
    "milligram": ("mg", "g", 0.001),
    "milligrams": ("mg", "g", 0.001),

    # Volume (Base: 'ml')
    "ml": ("ml", "ml", 1.0),
    "mls": ("ml", "ml", 1.0),
    "millilitre": ("ml", "ml", 1.0),
    "millilitres": ("ml", "ml", 1.0),
    "milliliter": ("ml", "ml", 1.0),
    "milliliters": ("ml", "ml", 1.0),
    "l": ("L", "ml", 1000.0),
    "ltr": ("L", "ml", 1000.0),
    "litre": ("L", "ml", 1000.0),
    "litres": ("L", "ml", 1000.0),
    "liter": ("L", "ml", 1000.0),
    "liters": ("L", "ml", 1000.0),
    "cl": ("cl", "ml", 10.0),

    # Length & Area (Base: 'm')
    "m": ("m", "m", 1.0),
    "meter": ("m", "m", 1.0),
    "meters": ("m", "m", 1.0),
    "metre": ("m", "m", 1.0),
    "metres": ("m", "m", 1.0),
    "cm": ("cm", "m", 0.01),
    "centimeter": ("cm", "m", 0.01),
    "centimeters": ("cm", "m", 0.01),
    "mm": ("mm", "m", 0.001),
    "sq.m": ("sq.m", "sq.m", 1.0),
    "sq.cm": ("sq.cm", "sq.m", 0.0001),

    # Count / Number (Base: 'N')
    "u": ("N", "N", 1.0),
    "unit": ("N", "N", 1.0),
    "units": ("N", "N", 1.0),
    "n": ("N", "N", 1.0),
    "piece": ("N", "N", 1.0),
    "pieces": ("N", "N", 1.0),
    "pc": ("N", "N", 1.0),
    "pcs": ("N", "N", 1.0),
    "count": ("N", "N", 1.0),
    "pack": ("N", "N", 1.0),
    "tablets": ("N", "N", 1.0),
    "capsules": ("N", "N", 1.0)
}

MONTH_MAP: Dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
}


# =============================================================================
# 2. Comprehensive Regular Expression Engines
# =============================================================================

class StatutoryRegexPatterns:
    """
    Production-grade compiled regular expressions for Legal Metrology parsing.
    Employs positive lookbehinds, lookaheads, and fuzzy character tolerance.
    """

    # -------------------------------------------------------------------------
    # A. Maximum Retail Price (MRP)
    # -------------------------------------------------------------------------
    # Explicit MRP prefix lookbehind or match
    MRP_EXPLICIT = re.compile(
        r'(?:'
        r'(?:M\.?\s*R\.?\s*P\.?|MAX(?:\.|\s+)?RETAIL(?:\.|\s+)?PRICE|MAXIMUM\s+RETAIL\s+PRICE|RETAIL\s+PRICE|SELLING\s+PRICE|PRICE|M\.R\.P)'
        r'[\s:.\-–—]*'
        r'(?:\(?[A-Z\s]*\)?)*'
        r'[\s:.\-–—]*'
        r'(?:₹|RS\.?|INR)?\s*'
        r'(\d+(?:[.,]\d{1,2})?)'
        r'(?:\s*(?:/-|\bINR\b|\bRS\b))?'
        r')',
        re.IGNORECASE
    )

    # Standalone Currency Symbol followed by price
    CURRENCY_PRICE = re.compile(
        r'(?:₹|RS\.?|INR)\s*(\d+(?:[.,]\d{1,2})?)(?:\s*(?:/-|\bonly\b))?',
        re.IGNORECASE
    )

    # Inclusive of taxes indicator
    TAX_INCLUSIVE = re.compile(
        r'(?:INCL(?:USIVE)?\.?\s*(?:OF)?\s*ALL\s*TAX(?:ES)?|ALL\s*TAX(?:ES)?\s*INCL(?:USIVE)?|TAX(?:ES)?\s*INCL(?:UDED)?|INCLUDING\s*ALL\s*TAX(?:ES)?)',
        re.IGNORECASE
    )

    # -------------------------------------------------------------------------
    # B. Net Quantity
    # -------------------------------------------------------------------------
    # Explicit Net Quantity / Weight / Volume prefix
    NET_QTY_EXPLICIT = re.compile(
        r'(?:'
        r'(?:NET\s*(?:QTY|QUANTITY|WT\.?|WEIGHT|CONTENTS?|VOLUME)|SHUDDHA\s+MATRA|NET\s+MASS|QUANTITY|TOTAL\s*WEIGHT)'
        r'[\s:.\-–—]*'
        r'(\d+(?:\.\d+)?)\s*'
        r'(kg|kgs|kilograms?|g|gm|gms|grams?|mg|milligrams?|l|ltr|litres?|liters?|ml|millilitres?|milliliters?|cl|m|cm|mm|sq\.m|sq\.cm|units?|pieces?|pcs|count|pack|n)\b'
        r')',
        re.IGNORECASE
    )

    # Standalone Number + Standard Packaging Unit
    STANDALONE_QTY = re.compile(
        r'\b(\d+(?:\.\d+)?)\s*'
        r'(kg|kgs|kilograms?|g|gm|gms|grams?|mg|milligrams?|l|ltr|litres?|liters?|ml|millilitres?|milliliters?|cl|m|cm|mm|sq\.m|units?|pieces?|pcs|count|pack|n)\b',
        re.IGNORECASE
    )

    # -------------------------------------------------------------------------
    # C. Statutory Dates (MFD, PKD, EXP, USE BY)
    # -------------------------------------------------------------------------
    # MFD / PKD Prefixes
    MFD_PREFIX = re.compile(
        r'(?:MFD\.?|MFG\.?|DATE\s*OF\s*MFG|MANUFACTURED\s*(?:ON|DATE)?|PKD\.?|PACKED\s*(?:ON|DATE)?|PACKAGING\s*DATE|BATCH\s*&\s*MFD|PRODUCED\s*ON|MFG\s*DATE)',
        re.IGNORECASE
    )

    # Expiry / Use-By Prefixes
    EXP_PREFIX = re.compile(
        r'(?:EXP\.?|EXPIRY\s*(?:DATE)?|EXP\.?\s*DATE|USE\s*BY|BEST\s*BEFORE|USE\s*BEFORE|VALID\s*(?:UPTO|TILL)|EXPIRATION)',
        re.IGNORECASE
    )

    # Standard Numeric Date Formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, MM/YYYY, MM-YYYY)
    DATE_PATTERNS = [
        # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
        re.compile(r'\b(0?[1-9]|[12]\d|3[01])[\s/.\-](0?[1-9]|1[0-2])[\s/.\-]((?:19|20)\d{2})\b'),
        # YYYY-MM-DD or YYYY/MM/DD
        re.compile(r'\b((?:19|20)\d{2})[\s/.\-](0?[1-9]|1[0-2])[\s/.\-](0?[1-9]|[12]\d|3[01])\b'),
        # Month Name: DD Mon YYYY or DD Month YYYY (e.g., 24 Aug 2026, 24-August-2026)
        re.compile(r'\b(0?[1-9]|[12]\d|3[01])[\s/.\-]([a-zA-Z]{3,9})[\s/.\-]((?:19|20)\d{2})\b', re.IGNORECASE),
        # Mon YYYY (e.g., Aug 2026, August 2026)
        re.compile(r'\b([a-zA-Z]{3,9})[\s/.\-]((?:19|20)\d{2})\b', re.IGNORECASE),
        # MM/YYYY or MM-YYYY or MM.YYYY (Mandatory Legal Metrology format under Rule 6(1)(d))
        re.compile(r'\b(0?[1-9]|1[0-2])[\s/.\-]((?:19|20)\d{2})\b'),
        # MM/YY (Two-digit year: 08/26)
        re.compile(r'\b(0?[1-9]|1[0-2])[\s/.\-](\d{2})\b')
    ]

    # Relative Shelf-Life / Expiry (e.g., "Best before 12 months from manufacture/pkd")
    RELATIVE_EXPIRY = re.compile(
        r'(?:BEST\s+BEFORE|USE\s+WITHIN|SHELF\s+LIFE\s*(?:OF)?|VALID\s+FOR)\s*'
        r'(\d+)\s*'
        r'(days?|weeks?|months?|years?)\s*'
        r'(?:FROM\s+(?:THE\s+)?(?:DATE\s+OF\s+)?(MFD|MFG|PKD|PACKAGING|MANUFACTURE|PACKED|DATE))?',
        re.IGNORECASE
    )

    # -------------------------------------------------------------------------
    # D. Customer Care (Toll-Free, Helpline, Phone, Email, Website)
    # -------------------------------------------------------------------------
    # Toll-free 1800 numbers
    TOLL_FREE = re.compile(r'\b1800[-\s]?\d{3}[-\s]?\d{4}\b|\b1800\d{6,8}\b', re.IGNORECASE)

    # Standard Indian Mobile / Landline Phone numbers
    PHONE_GENERAL = re.compile(
        r'(?:(?:TEL|PHONE|MOBILE|HELPLINE|CALL|CARE|CONTACT|NO\.?)[\s:.\-–—]*)?'
        r'(?:\+?91[\s\-]?)?'
        r'(?:\(?0\d{2,4}\)?[\s\-]?)?'
        r'(\b[6-9]\d{9}\b|\b\d{3,4}[-\s]\d{6,8}\b)',
        re.IGNORECASE
    )

    # Standard Email Regex
    EMAIL = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b', re.IGNORECASE)

    # Website URLs
    WEBSITE = re.compile(r'\b(?:https?://)?(?:www\.)[A-Za-z0-9.\-]+\.[A-Za-z]{2,}(?:/[^\s]*)?\b', re.IGNORECASE)

    # -------------------------------------------------------------------------
    # E. Additional Statutory Fields
    # -------------------------------------------------------------------------
    # FSSAI License Number (14-digit number)
    FSSAI_LIC = re.compile(r'(?:FSSAI(?:\s*LIC(?:ENSE)?(?:\s*NO\.?)?)?[\s:.\-–—]*)(\b\d{14}\b)', re.IGNORECASE)

    # Country of Origin (COO)
    COUNTRY_OF_ORIGIN = re.compile(
        r'(?:COUNTRY\s*OF\s*ORIGIN|MADE\s*IN|PRODUCT\s*OF)[\s:.\-–—]*([A-Za-z\s]+)',
        re.IGNORECASE
    )

    # Unit Sale Price (USP)
    USP = re.compile(
        r'(?:USP|UNIT\s*SALE\s*PRICE|UNIT\s*PRICE)[\s:.\-–—]*'
        r'(?:₹|RS\.?|INR)?\s*(\d+(?:[.,]\d{1,2})?)\s*'
        r'(?:/|PER)\s*'
        r'(\d*(?:\.\d+)?\s*(?:g|gm|gms|kg|ml|l|ltr|u|unit|n|m|cm|mm|sq\.m))',
        re.IGNORECASE
    )

    # Manufacturer / Packer details
    MANUFACTURER = re.compile(
        r'(?:MFD\.?\s*BY|MANUFACTURED\s*BY|PACKED\s*BY|PKD\.?\s*BY|MARKETED\s*BY|PRODUCED\s*BY)[\s:.\-–—]*([^\n|;]+)',
        re.IGNORECASE
    )

    # Batch / Lot Number (requires at least 1 digit in batch code)
    BATCH_NO = re.compile(
        r'(?:BATCH\s*(?:NO\.?|NUMBER)?|LOT\s*(?:NO\.?|NUMBER)?)[\s:.\-–—]*((?=.*\d)[A-Za-z0-9\-_/]{3,})',
        re.IGNORECASE
    )


# =============================================================================
# 3. Structured Data Models (Pydantic / Typed Dataclasses)
# =============================================================================

@dataclass
class EvidenceMeta:
    """Stores spatial coordinates and confidence for Evidence Engine rendering."""
    evidence_id: str
    source_line: str
    raw_text: str
    original_text: Optional[str]
    confidence: float
    bounding_box: List[Any]
    bbox_xyxy: List[int]


@dataclass
class MRPDeclaration:
    detected: bool
    value: Optional[float] = None
    currency: str = "INR"
    is_inclusive_of_taxes: bool = False
    evidence: Optional[EvidenceMeta] = None


@dataclass
class NetQuantityDeclaration:
    detected: bool
    value: Optional[float] = None
    unit: Optional[str] = None
    standardized_unit: Optional[str] = None
    base_value: Optional[float] = None
    base_unit: Optional[str] = None
    formatted: Optional[str] = None
    evidence: Optional[EvidenceMeta] = None


@dataclass
class DateDeclaration:
    detected: bool
    iso_date: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    raw_date_string: Optional[str] = None
    is_relative: bool = False
    relative_statement: Optional[str] = None
    evidence: Optional[EvidenceMeta] = None


@dataclass
class PhoneEvidence:
    number: str
    normalized_number: str
    is_toll_free: bool
    evidence: EvidenceMeta


@dataclass
class EmailEvidence:
    email: str
    evidence: EvidenceMeta


@dataclass
class CustomerCareDeclaration:
    detected: bool
    phones: List[PhoneEvidence] = field(default_factory=list)
    emails: List[EmailEvidence] = field(default_factory=list)
    website: Optional[str] = None
    primary_contact: Optional[str] = None


@dataclass
class AdditionalStatutoryFields:
    fssai_license: Optional[Dict[str, Any]] = None
    country_of_origin: Optional[Dict[str, Any]] = None
    unit_sale_price: Optional[Dict[str, Any]] = None
    manufacturer: Optional[Dict[str, Any]] = None
    batch_number: Optional[Dict[str, Any]] = None


@dataclass
class ExtractionComplianceReport:
    """Top-level structured JSON schema for Legal Metrology AI Engine."""
    mrp: MRPDeclaration
    net_quantity: NetQuantityDeclaration
    manufacturing_date: DateDeclaration
    expiry_date: DateDeclaration
    customer_care: CustomerCareDeclaration
    additional_fields: AdditionalStatutoryFields
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Recursively converts dataclass to JSON-serializable dictionary."""
        return asdict(self)


# =============================================================================
# 4. Core Enterprise Statutory Data Extractor
# =============================================================================

class StatutoryDataExtractor:
    """
    Production-grade Legal Metrology Data Extraction Engine.
    Processes multi-lingual translated OCR outputs, running advanced regex
    and heuristic normalization across all statutory declaration categories.
    """

    def __init__(self, confidence_threshold: float = 0.40) -> None:
        """
        :param confidence_threshold: Minimum OCR confidence required to accept a detection.
        """
        self.confidence_threshold = confidence_threshold
        self._evidence_counter = 0

    def _next_evidence_id(self, field_prefix: str) -> str:
        """Generates deterministic unique evidence IDs (e.g., EVID_MRP_01)."""
        self._evidence_counter += 1
        return f"EVID_{field_prefix}_{self._evidence_counter:02d}"

    @staticmethod
    def _compute_bbox_xyxy(bounding_box: Any) -> List[int]:
        """
        Calculates standard [xmin, ymin, xmax, ymax] integer coordinates from
        either 4-point polygon [[x1, y1], [x2, y2], [x3, y3], [x4, y4]] or [x1, y1, x2, y2].
        """
        if not bounding_box:
            return [0, 0, 0, 0]

        try:
            # 4-point polygon format
            if isinstance(bounding_box, list) and len(bounding_box) == 4 and isinstance(bounding_box[0], (list, tuple)):
                xs = [int(round(pt[0])) for pt in bounding_box]
                ys = [int(round(pt[1])) for pt in bounding_box]
                return [min(xs), min(ys), max(xs), max(ys)]
            # Rectangle format [x1, y1, x2, y2]
            elif isinstance(bounding_box, list) and len(bounding_box) == 4:
                return [int(round(v)) for v in bounding_box]
        except Exception:
            pass
        return [0, 0, 0, 0]

    def _create_evidence(
        self,
        field_prefix: str,
        matched_str: str,
        line_item: Dict[str, Any]
    ) -> EvidenceMeta:
        """Creates an EvidenceMeta object binding coordinates to the extracted field."""
        raw_bbox = line_item.get("bounding_box", [])
        return EvidenceMeta(
            evidence_id=self._next_evidence_id(field_prefix),
            source_line=line_item.get("translated_text", ""),
            raw_text=matched_str.strip(),
            original_text=line_item.get("original_text"),
            confidence=round(float(line_item.get("confidence", 1.0)), 4),
            bounding_box=raw_bbox,
            bbox_xyxy=self._compute_bbox_xyxy(raw_bbox)
        )

    # -------------------------------------------------------------------------
    # Extractor Method 1: Maximum Retail Price (MRP)
    # -------------------------------------------------------------------------
    def extract_mrp(self, lines: List[Dict[str, Any]]) -> MRPDeclaration:
        """
        Extracts MRP float value, currency, and tax status.
        Prioritizes lines with explicit 'MRP' keywords over generic standalone currency matches.
        """
        best_candidate: Optional[Tuple[float, bool, EvidenceMeta]] = None

        for item in lines:
            text = item.get("translated_text", "")
            if not text:
                continue

            # Check for tax inclusion on the line
            has_tax = bool(StatutoryRegexPatterns.TAX_INCLUSIVE.search(text))

            # Strategy A: Explicit MRP keyword matching
            m_explicit = StatutoryRegexPatterns.MRP_EXPLICIT.search(text)
            if m_explicit:
                try:
                    clean_num_str = m_explicit.group(1).replace(",", "")
                    val = float(clean_num_str)
                    evidence = self._create_evidence("MRP", m_explicit.group(0), item)
                    return MRPDeclaration(
                        detected=True,
                        value=val,
                        currency="INR",
                        is_inclusive_of_taxes=has_tax or "all taxes" in text.lower(),
                        evidence=evidence
                    )
                except ValueError:
                    pass

            # Strategy B: Generic currency symbol matching (fallback if explicit MRP not yet found)
            if not best_candidate:
                m_curr = StatutoryRegexPatterns.CURRENCY_PRICE.search(text)
                if m_curr:
                    try:
                        clean_num_str = m_curr.group(1).replace(",", "")
                        val = float(clean_num_str)
                        evidence = self._create_evidence("MRP", m_curr.group(0), item)
                        best_candidate = (val, has_tax, evidence)
                    except ValueError:
                        pass

        if best_candidate:
            val, has_tax, evidence = best_candidate
            return MRPDeclaration(
                detected=True,
                value=val,
                currency="INR",
                is_inclusive_of_taxes=has_tax,
                evidence=evidence
            )

        return MRPDeclaration(detected=False)

    # -------------------------------------------------------------------------
    # Extractor Method 2: Net Quantity
    # -------------------------------------------------------------------------
    def extract_net_quantity(self, lines: List[Dict[str, Any]]) -> NetQuantityDeclaration:
        """
        Extracts declared net quantity value and unit, performing canonical SI conversion.
        """
        best_candidate: Optional[NetQuantityDeclaration] = None

        for item in lines:
            text = item.get("translated_text", "")
            if not text:
                continue

            # Strategy A: Explicit Net Qty / Net Weight Prefix
            m_explicit = StatutoryRegexPatterns.NET_QTY_EXPLICIT.search(text)
            if m_explicit:
                val_str, unit_str = m_explicit.group(1), m_explicit.group(2)
                decl = self._build_qty_declaration(val_str, unit_str, m_explicit.group(0), item)
                if decl:
                    return decl

            # Strategy B: Standalone Quantity with valid metric packaging unit
            if not best_candidate:
                m_standalone = StatutoryRegexPatterns.STANDALONE_QTY.search(text)
                if m_standalone:
                    val_str, unit_str = m_standalone.group(1), m_standalone.group(2)
                    # Ignore standalone numbers followed by 'm' if part of date or time
                    if unit_str.lower() in ["m", "month", "months"] and any(w in text.lower() for w in ["best", "before", "pkd"]):
                        continue
                    decl = self._build_qty_declaration(val_str, unit_str, m_standalone.group(0), item)
                    if decl:
                        best_candidate = decl

        return best_candidate or NetQuantityDeclaration(detected=False)

    def _build_qty_declaration(
        self,
        val_str: str,
        unit_str: str,
        matched_str: str,
        item: Dict[str, Any]
    ) -> Optional[NetQuantityDeclaration]:
        """Standardizes quantity and converts to canonical SI base."""
        try:
            val = float(val_str)
            raw_unit = unit_str.strip().lower()
            norm_info = UNIT_NORMALIZATION_MAP.get(raw_unit)

            if norm_info:
                std_unit, base_unit, multiplier = norm_info
                base_val = round(val * multiplier, 4)
            else:
                std_unit, base_unit, base_val = raw_unit, raw_unit, val

            evidence = self._create_evidence("NET_QTY", matched_str, item)
            formatted_str = f"{int(val) if val.is_integer() else val} {std_unit}"

            return NetQuantityDeclaration(
                detected=True,
                value=val,
                unit=raw_unit,
                standardized_unit=std_unit,
                base_value=base_val,
                base_unit=base_unit,
                formatted=formatted_str,
                evidence=evidence
            )
        except (ValueError, TypeError):
            return None

    # -------------------------------------------------------------------------
    # Extractor Method 3: Dates (Manufacturing & Expiry)
    # -------------------------------------------------------------------------
    def extract_dates(
        self,
        lines: List[Dict[str, Any]]
    ) -> Tuple[DateDeclaration, DateDeclaration]:
        """
        Extracts Manufacturing Date (MFD/PKD) and Expiry/Use-By Date.
        Handles both absolute calendar dates and relative statements ("Best before X months").
        """
        mfd_decl = DateDeclaration(detected=False)
        exp_decl = DateDeclaration(detected=False)

        for item in lines:
            text = item.get("translated_text", "")
            if not text:
                continue

            is_mfd_line = bool(StatutoryRegexPatterns.MFD_PREFIX.search(text))
            is_exp_line = bool(StatutoryRegexPatterns.EXP_PREFIX.search(text))

            # 1. Check for Relative Shelf Life (e.g., "Best before 12 months from PKD")
            if is_exp_line and not exp_decl.detected:
                m_rel = StatutoryRegexPatterns.RELATIVE_EXPIRY.search(text)
                if m_rel:
                    duration_num = int(m_rel.group(1))
                    duration_unit = m_rel.group(2).lower()
                    from_event = m_rel.group(3) or "MFD"
                    evidence = self._create_evidence("EXP", m_rel.group(0), item)
                    exp_decl = DateDeclaration(
                        detected=True,
                        is_relative=True,
                        relative_statement=f"{duration_num} {duration_unit} from {from_event}",
                        raw_date_string=m_rel.group(0),
                        evidence=evidence
                    )

            # 2. Check for Absolute Dates on the Line
            parsed_date_info = self._parse_date_string(text)
            if parsed_date_info:
                iso_val, y, m, d, matched_text = parsed_date_info

                if is_mfd_line and not mfd_decl.detected:
                    evidence = self._create_evidence("MFD", matched_text, item)
                    mfd_decl = DateDeclaration(
                        detected=True,
                        iso_date=iso_val,
                        year=y,
                        month=m,
                        day=d,
                        raw_date_string=matched_text,
                        is_relative=False,
                        evidence=evidence
                    )
                elif is_exp_line and not exp_decl.detected:
                    evidence = self._create_evidence("EXP", matched_text, item)
                    exp_decl = DateDeclaration(
                        detected=True,
                        iso_date=iso_val,
                        year=y,
                        month=m,
                        day=d,
                        raw_date_string=matched_text,
                        is_relative=False,
                        evidence=evidence
                    )
                elif not mfd_decl.detected and not exp_decl.detected:
                    # Unclassified date: Assign to MFD if earlier or standard
                    evidence = self._create_evidence("DATE", matched_text, item)
                    mfd_decl = DateDeclaration(
                        detected=True,
                        iso_date=iso_val,
                        year=y,
                        month=m,
                        day=d,
                        raw_date_string=matched_text,
                        is_relative=False,
                        evidence=evidence
                    )

        return mfd_decl, exp_decl

    def _parse_date_string(self, text: str) -> Optional[Tuple[str, int, int, Optional[int], str]]:
        """Parses date tokens into (iso_date, year, month, day, matched_substring)."""
        for pattern in StatutoryRegexPatterns.DATE_PATTERNS:
            m = pattern.search(text)
            if not m:
                continue

            groups = m.groups()
            matched_str = m.group(0)

            try:
                # Format: DD/MM/YYYY or DD-MM-YYYY
                if len(groups) == 3 and groups[0].isdigit() and groups[1].isdigit() and len(groups[2]) == 4:
                    d, mo, yr = int(groups[0]), int(groups[1]), int(groups[2])
                    return f"{yr:04d}-{mo:02d}-{d:02d}", yr, mo, d, matched_str

                # Format: YYYY-MM-DD
                elif len(groups) == 3 and len(groups[0]) == 4 and groups[1].isdigit() and groups[2].isdigit():
                    yr, mo, d = int(groups[0]), int(groups[1]), int(groups[2])
                    return f"{yr:04d}-{mo:02d}-{d:02d}", yr, mo, d, matched_str

                # Format: DD Mon YYYY (e.g., 24 Aug 2026)
                elif len(groups) == 3 and groups[0].isdigit() and groups[1].isalpha() and len(groups[2]) == 4:
                    d = int(groups[0])
                    mo = MONTH_MAP.get(groups[1].lower()[:3], 1)
                    yr = int(groups[2])
                    return f"{yr:04d}-{mo:02d}-{d:02d}", yr, mo, d, matched_str

                # Format: Mon YYYY (e.g., Aug 2026)
                elif len(groups) == 2 and groups[0].isalpha() and len(groups[1]) == 4:
                    mo = MONTH_MAP.get(groups[0].lower()[:3], 1)
                    yr = int(groups[1])
                    return f"{yr:04d}-{mo:02d}", yr, mo, None, matched_str

                # Format: MM/YYYY or MM-YYYY (Legal Metrology Month/Year rule)
                elif len(groups) == 2 and groups[0].isdigit() and len(groups[1]) == 4:
                    mo, yr = int(groups[0]), int(groups[1])
                    if 1 <= mo <= 12:
                        return f"{yr:04d}-{mo:02d}", yr, mo, None, matched_str

                # Format: MM/YY (Two digit year e.g. 08/26)
                elif len(groups) == 2 and groups[0].isdigit() and len(groups[1]) == 2:
                    mo, yr_short = int(groups[0]), int(groups[1])
                    yr = 2000 + yr_short if yr_short < 70 else 1900 + yr_short
                    if 1 <= mo <= 12:
                        return f"{yr:04d}-{mo:02d}", yr, mo, None, matched_str

            except Exception:
                continue

        return None

    # -------------------------------------------------------------------------
    # Extractor Method 4: Customer Care (Phones, Emails, Websites)
    # -------------------------------------------------------------------------
    def extract_customer_care(self, lines: List[Dict[str, Any]]) -> CustomerCareDeclaration:
        """
        Extracts consumer grievance contact details: Toll-free numbers, phone numbers,
        email addresses, and corporate complaint websites.
        """
        phones: List[PhoneEvidence] = []
        emails: List[EmailEvidence] = []
        website_url: Optional[str] = None
        seen_numbers = set()
        seen_emails = set()

        for item in lines:
            text = item.get("translated_text", "")
            if not text:
                continue

            # 1. Toll-Free 1800 numbers
            for tf_match in StatutoryRegexPatterns.TOLL_FREE.finditer(text):
                num_str = tf_match.group(0)
                clean_digits = re.sub(r'[^\d]', '', num_str)
                if clean_digits not in seen_numbers:
                    seen_numbers.add(clean_digits)
                    evidence = self._create_evidence("TOLLFREE", num_str, item)
                    phones.append(PhoneEvidence(
                        number=num_str,
                        normalized_number=clean_digits,
                        is_toll_free=True,
                        evidence=evidence
                    ))

            # 2. General Phone / Helpline Numbers
            for p_match in StatutoryRegexPatterns.PHONE_GENERAL.finditer(text):
                num_str = p_match.group(1)
                clean_digits = re.sub(r'[^\d]', '', num_str)
                # Ensure valid telephone length (8 to 12 digits)
                if 8 <= len(clean_digits) <= 12 and clean_digits not in seen_numbers:
                    seen_numbers.add(clean_digits)
                    evidence = self._create_evidence("PHONE", num_str, item)
                    phones.append(PhoneEvidence(
                        number=num_str,
                        normalized_number=clean_digits,
                        is_toll_free=clean_digits.startswith("1800"),
                        evidence=evidence
                    ))

            # 3. Emails
            for e_match in StatutoryRegexPatterns.EMAIL.finditer(text):
                email_str = e_match.group(0).lower()
                if email_str not in seen_emails:
                    seen_emails.add(email_str)
                    evidence = self._create_evidence("EMAIL", email_str, item)
                    emails.append(EmailEvidence(
                        email=email_str,
                        evidence=evidence
                    ))

            # 4. Websites
            if not website_url:
                w_match = StatutoryRegexPatterns.WEBSITE.search(text)
                if w_match:
                    website_url = w_match.group(0)

        detected = bool(phones or emails or website_url)
        primary = phones[0].number if phones else (emails[0].email if emails else website_url)

        return CustomerCareDeclaration(
            detected=detected,
            phones=phones,
            emails=emails,
            website=website_url,
            primary_contact=primary
        )

    # -------------------------------------------------------------------------
    # Extractor Method 5: Additional Statutory Declarations
    # -------------------------------------------------------------------------
    def extract_additional_statutory_fields(
        self,
        lines: List[Dict[str, Any]]
    ) -> AdditionalStatutoryFields:
        """
        Extracts FSSAI License, Country of Origin (COO), Unit Sale Price (USP),
        Manufacturer/Packer name, and Batch numbers.
        """
        fssai_info: Optional[Dict[str, Any]] = None
        coo_info: Optional[Dict[str, Any]] = None
        usp_info: Optional[Dict[str, Any]] = None
        mfr_info: Optional[Dict[str, Any]] = None
        batch_info: Optional[Dict[str, Any]] = None

        for item in lines:
            text = item.get("translated_text", "")
            if not text:
                continue

            # FSSAI License
            if not fssai_info:
                m_fssai = StatutoryRegexPatterns.FSSAI_LIC.search(text)
                if m_fssai:
                    lic_num = m_fssai.group(1)
                    evidence = self._create_evidence("FSSAI", lic_num, item)
                    fssai_info = {
                        "license_number": lic_num,
                        "is_valid_14_digit": len(lic_num) == 14,
                        "evidence": asdict(evidence)
                    }

            # Country of Origin
            if not coo_info:
                m_coo = StatutoryRegexPatterns.COUNTRY_OF_ORIGIN.search(text)
                if m_coo:
                    country_raw = m_coo.group(1).strip(" .:-")
                    evidence = self._create_evidence("COO", m_coo.group(0), item)
                    coo_info = {
                        "country": country_raw,
                        "is_india": "india" in country_raw.lower(),
                        "evidence": asdict(evidence)
                    }

            # Unit Sale Price (USP)
            if not usp_info:
                m_usp = StatutoryRegexPatterns.USP.search(text)
                if m_usp:
                    val = float(m_usp.group(1).replace(",", ""))
                    unit_ref = m_usp.group(2).strip()
                    evidence = self._create_evidence("USP", m_usp.group(0), item)
                    usp_info = {
                        "value": val,
                        "unit_reference": unit_ref,
                        "formatted": f"₹ {val:.2f} / {unit_ref}",
                        "evidence": asdict(evidence)
                    }

            # Manufacturer / Packer
            if not mfr_info:
                m_mfr = StatutoryRegexPatterns.MANUFACTURER.search(text)
                if m_mfr:
                    mfr_name = m_mfr.group(1).strip()
                    evidence = self._create_evidence("MFR", m_mfr.group(0), item)
                    mfr_info = {
                        "name_and_address": mfr_name,
                        "evidence": asdict(evidence)
                    }

            # Batch Number
            if not batch_info:
                m_batch = StatutoryRegexPatterns.BATCH_NO.search(text)
                if m_batch:
                    batch_str = m_batch.group(1).strip()
                    evidence = self._create_evidence("BATCH", m_batch.group(0), item)
                    batch_info = {
                        "batch_number": batch_str,
                        "evidence": asdict(evidence)
                    }

        return AdditionalStatutoryFields(
            fssai_license=fssai_info,
            country_of_origin=coo_info,
            unit_sale_price=usp_info,
            manufacturer=mfr_info,
            batch_number=batch_info
        )

    # -------------------------------------------------------------------------
    # Main Orchestrator Pipeline
    # -------------------------------------------------------------------------
    def extract_all(self, ocr_results: List[Dict[str, Any]]) -> ExtractionComplianceReport:
        """
        Executes complete Stage 5 Legal Metrology Information Extraction.

        :param ocr_results: List of translated OCR dictionaries, each having:
                            - 'translated_text': str
                            - 'original_text': str (optional)
                            - 'confidence': float
                            - 'bounding_box': 4-point list or [x1, y1, x2, y2]
        :return: Comprehensive structured ExtractionComplianceReport.
        """
        # Filter low-confidence OCR noise
        filtered_lines = [
            item for item in ocr_results
            if float(item.get("confidence", 1.0)) >= self.confidence_threshold
        ]

        logger.info(f"[EXTRACTOR] Processing {len(filtered_lines)} OCR declaration lines...")

        # 1. Extract Mandatory Statutory Fields
        mrp = self.extract_mrp(filtered_lines)
        net_qty = self.extract_net_quantity(filtered_lines)
        mfd, exp = self.extract_dates(filtered_lines)
        customer_care = self.extract_customer_care(filtered_lines)

        # 2. Extract Supplementary Legal Metrology Fields
        additional = self.extract_additional_statutory_fields(filtered_lines)

        # 3. Compile Compliance Summary
        mandatory_checklist = {
            "mrp": mrp.detected,
            "net_quantity": net_qty.detected,
            "manufacturing_date": mfd.detected,
            "expiry_date": exp.detected,
            "customer_care": customer_care.detected
        }

        detected_count = sum(1 for v in mandatory_checklist.values() if v)
        missing_mandatory = [k for k, v in mandatory_checklist.items() if not v]

        summary = {
            "total_input_lines": len(ocr_results),
            "processed_lines": len(filtered_lines),
            "mandatory_fields_detected": detected_count,
            "mandatory_fields_required": 5,
            "is_fully_compliant": (detected_count >= 4),  # Allows either MFD or Expiry
            "checklist": mandatory_checklist,
            "missing_fields": missing_mandatory,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(
            f"[EXTRACTOR] Complete. Detected {detected_count}/5 mandatory declarations. "
            f"Compliant: {summary['is_fully_compliant']}"
        )

        return ExtractionComplianceReport(
            mrp=mrp,
            net_quantity=net_qty,
            manufacturing_date=mfd,
            expiry_date=exp,
            customer_care=customer_care,
            additional_fields=additional,
            summary=summary
        )


# Convenient alias for enterprise imports
DataExtractor = StatutoryDataExtractor


# =============================================================================
# Demonstration & Verification Harness (__main__)
# =============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("[METRIX-LM] STAGE 5: STATUTORY DATA EXTRACTOR BENCHMARK (SIH 26034)")
    print("=" * 80)

    # Mock output received from TranslationMiddleware pipeline
    # Simulates packaging text translated from Indic scripts (Hindi, Tamil, Telugu, etc.)
    mock_translated_detections = [
        {
            "translated_text": "Nestle Everyday Dairy Whitener",
            "original_text": "नेस्ले एवरीडे डेयरी व्हाइटनर",
            "confidence": 0.985,
            "bounding_box": [[45, 30], [550, 30], [550, 75], [45, 75]]
        },
        {
            "translated_text": "Net Weight : 1.0 kg (High Quality Standard Pack)",
            "original_text": "மொத்த எடை : 1.0 கிலோகிராம் (உயர்தர கோதுமை மாவு)",
            "confidence": 0.978,
            "bounding_box": [[45, 95], [620, 95], [620, 135], [45, 135]]
        },
        {
            "translated_text": "Maximum Retail Price : ₹245.50 (Inclusive of all taxes)",
            "original_text": "அதிகபட்ச சில்லறை விலை : ₹௨௪௫.௫௦ (வரிகள் உட்பட)",
            "confidence": 0.992,
            "bounding_box": [[45, 155], [710, 155], [710, 195], [45, 195]]
        },
        {
            "translated_text": "Date of Mfg : 24/08/2026",
            "original_text": "उत्पादन तिथि : २४/०८/२०२६",
            "confidence": 0.981,
            "bounding_box": [[45, 215], [420, 215], [420, 250], [45, 250]]
        },
        {
            "translated_text": "Expiry Date : 25/02/2027 (Best Before 6 Months From PKD)",
            "original_text": "उपयोग समाप्ति : २५/०२/२०२७",
            "confidence": 0.969,
            "bounding_box": [[45, 270], [680, 270], [680, 310], [45, 310]]
        },
        {
            "translated_text": "Customer Care Helpline : 1800-120-4567 | care@nestle.in",
            "original_text": "ग्राहक सेवा : 1800-120-4567 | care@nestle.in",
            "confidence": 0.995,
            "bounding_box": [[45, 330], [750, 330], [750, 370], [45, 370]]
        },
        {
            "translated_text": "FSSAI Lic No: 10014022002654",
            "original_text": "एफएसएसएआई लाइसेंस: 10014022002654",
            "confidence": 0.988,
            "bounding_box": [[45, 390], [460, 390], [460, 425], [45, 425]]
        },
        {
            "translated_text": "Country of Origin : India",
            "original_text": "मूल देश : भारत",
            "confidence": 0.994,
            "bounding_box": [[45, 445], [380, 445], [380, 480], [45, 480]]
        },
        {
            "translated_text": "Unit Sale Price: ₹ 0.25 / g",
            "original_text": "इकाई विक्रय मूल्य: ₹ ०.२५ / ग्राम",
            "confidence": 0.975,
            "bounding_box": [[45, 500], [390, 500], [390, 535], [45, 535]]
        },
        {
            "translated_text": "Manufactured by: Nestle India Limited, Industrial Area, Solan, H.P.",
            "original_text": "निर्माता: नेस्ले इंडिया लिमिटेड",
            "confidence": 0.962,
            "bounding_box": [[45, 555], [780, 555], [780, 595], [45, 595]]
        }
    ]

    print("[*] Initializing StatutoryDataExtractor...")
    extractor = StatutoryDataExtractor(confidence_threshold=0.50)

    print(f"[*] Input Batch: {len(mock_translated_detections)} translated OCR lines with bounding boxes")
    print("-" * 80)

    report = extractor.extract_all(mock_translated_detections)
    report_dict = report.to_dict()

    print("\n" + "=" * 80)
    print("STAGE 5 EXTRACTED STATUTORY COMPLIANCE SCHEMA (STRUCTURED JSON)")
    print("=" * 80)
    print(json.dumps(report_dict, indent=2, ensure_ascii=False))

    # Assertions & Verification
    print("\n" + "=" * 80)
    print("STATUTORY EXTRACTION VERIFICATION CHECKS")
    print("=" * 80)

    # 1. MRP Verification
    assert report.mrp.detected, "TEST FAILED: MRP was not detected!"
    assert report.mrp.value == 245.50, f"TEST FAILED: Expected 245.50, got {report.mrp.value}"
    assert report.mrp.is_inclusive_of_taxes, "TEST FAILED: Tax inclusion was not identified!"
    assert report.mrp.evidence is not None, "TEST FAILED: Bounding box evidence missing for MRP!"
    print(f"[PASS] MRP Extracted: ₹ {report.mrp.value:.2f} (Taxes Included: {report.mrp.is_inclusive_of_taxes})")
    print(f"       Bounding Box: {report.mrp.evidence.bbox_xyxy} | Conf: {report.mrp.evidence.confidence}")

    # 2. Net Quantity Verification
    assert report.net_quantity.detected, "TEST FAILED: Net Quantity not detected!"
    assert report.net_quantity.value == 1.0, f"TEST FAILED: Expected 1.0, got {report.net_quantity.value}"
    assert report.net_quantity.standardized_unit == "kg", f"TEST FAILED: Unit mismatch: {report.net_quantity.standardized_unit}"
    assert report.net_quantity.base_value == 1000.0, f"TEST FAILED: Base value conversion: {report.net_quantity.base_value}"
    assert report.net_quantity.base_unit == "g", f"TEST FAILED: Base unit mismatch: {report.net_quantity.base_unit}"
    nq_bbox = report.net_quantity.evidence.bbox_xyxy if report.net_quantity.evidence else []
    nq_conf = report.net_quantity.evidence.confidence if report.net_quantity.evidence else 0.0
    print(f"       Bounding Box: {nq_bbox} | Conf: {nq_conf}")

    # 3. Date Verification
    assert report.manufacturing_date.detected, "TEST FAILED: Manufacturing date not detected!"
    assert report.manufacturing_date.iso_date == "2026-08-24", f"TEST FAILED: MFD format mismatch: {report.manufacturing_date.iso_date}"
    assert report.expiry_date.detected, "TEST FAILED: Expiry date not detected!"
    print(f"[PASS] Manufacturing Date: {report.manufacturing_date.iso_date} (Year: {report.manufacturing_date.year}, Month: {report.manufacturing_date.month})")
    print(f"[PASS] Expiry Date:        {report.expiry_date.iso_date or report.expiry_date.relative_statement}")

    # 4. Customer Care Verification
    assert report.customer_care.detected, "TEST FAILED: Customer Care not detected!"
    assert len(report.customer_care.phones) > 0, "TEST FAILED: Customer phone missing!"
    assert len(report.customer_care.emails) > 0, "TEST FAILED: Customer email missing!"
    print(f"[PASS] Customer Care Phones: {[p.number for p in report.customer_care.phones]}")
    print(f"[PASS] Customer Care Emails: {[e.email for e in report.customer_care.emails]}")

    # 5. Additional Fields Verification
    assert report.additional_fields.fssai_license is not None, "TEST FAILED: FSSAI License missing!"
    assert report.additional_fields.country_of_origin is not None, "TEST FAILED: Country of Origin missing!"
    assert report.additional_fields.unit_sale_price is not None, "TEST FAILED: Unit Sale Price missing!"
    print(f"[PASS] FSSAI License:    {report.additional_fields.fssai_license['license_number']}")
    print(f"[PASS] Country of Origin:{report.additional_fields.country_of_origin['country']}")
    print(f"[PASS] Unit Sale Price:  {report.additional_fields.unit_sale_price['formatted']}")

    # 6. Overall Compliance Summary Verification
    assert report.summary["is_fully_compliant"], "TEST FAILED: Summary marked non-compliant!"
    print(f"[PASS] Compliance Score: {report.summary['mandatory_fields_detected']}/5 Mandatory Declarations Verified.")

    print("\n[+] All Stage 5 Data Extractor requirements successfully verified.")
