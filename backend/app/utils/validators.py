"""
CUI (Cod Unic de Identificare) validation — Romanian official algorithm.
Checksum mod 11 — hard constraint #2.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.core.config import settings


def validate_cui(cui: int) -> bool:
    """
    Validate a Romanian CUI using the official checksum algorithm (mod 11).
    Returns True if valid, False otherwise.

    Algorithm:
    1. Pad to 10 digits with leading zeros
    2. Multiply each digit (except the last) by its weight [7,5,3,2,1,7,5,3,2]
    3. Sum the products
    4. (sum * 10) % 11 → if 10 then 0 → must equal last digit
    """
    if cui < 10 or cui > 9_999_999_999:
        return False

    cui_str = str(cui).zfill(10)
    weights = [7, 5, 3, 2, 1, 7, 5, 3, 2]
    total = 0

    for i in range(1, len(cui_str)):
        digit_pos = len(cui_str) - 1 - i
        total += int(cui_str[digit_pos]) * weights[i - 1]

    rest = (total * 10) % 11
    if rest == 10:
        rest = 0

    return rest == int(cui_str[-1])


def hash_cnp(cnp: str) -> str:
    """
    Hash CNP for GDPR compliance — hard constraint #7.
    Uses SHA-256 with application-level pepper.
    Only first 6 digits (birth date) are hashed for deduplication.
    """
    if not cnp or len(cnp) < 6:
        return ""
    partial = cnp[:6]
    salted = f"{settings.CNP_PEPPER}:{partial}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def mask_cnp(cnp: str) -> str:
    """Display CNP partially masked: 1900101*******"""
    if not cnp or len(cnp) < 6:
        return "***************"
    return cnp[:6] + "*" * 7


def safe_decimal(value: object) -> Optional[Decimal]:
    """
    Convert any value to Decimal safely.
    NEVER use float for monetary values — hard constraint #1 / #15.
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def utc_now() -> datetime:
    """UTC datetime — hard constraint #10: store UTC, display Europe/Bucharest."""
    return datetime.now(timezone.utc)


def calculate_company_age_years(data_infiintare: Optional[date]) -> Optional[int]:
    """Calculate company age in years from registration date."""
    if not data_infiintare:
        return None
    today = date.today()
    return today.year - data_infiintare.year - (
        (today.month, today.day) < (data_infiintare.month, data_infiintare.day)
    )
