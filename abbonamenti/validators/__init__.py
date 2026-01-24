"""Validation functions for subscription data."""

import re
from datetime import datetime, timedelta
from typing import Optional


def validate_license_plate(plate: str) -> tuple[bool, str]:
    """
    Validate license plate format.
    
    Args:
        plate: License plate string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not plate or not plate.strip():
        return False, "Targa vuota"
    
    plate = plate.strip().upper()
    
    if len(plate) > 10:
        return False, "Targa troppo lunga (massimo 10 caratteri)"
    
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    """
    Validate email format.
    
    Args:
        email: Email string to validate (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email or not email.strip():
        # Email is optional
        return True, ""
    
    if "@" not in email:
        return False, "Email non valida (manca @)"
    
    return True, ""


def validate_date(date_str: str | datetime) -> tuple[bool, str, Optional[datetime]]:
    """
    Validate and parse date with auto-detection of multiple formats.
    
    Supports:
    - DD/MM/YYYY
    - MM/DD/YYYY
    - YYYY-MM-DD (ISO)
    - Excel serial dates (numbers)
    - datetime objects (pass through)
    
    Args:
        date_str: Date string or datetime object to validate
        
    Returns:
        Tuple of (is_valid, error_message, parsed_datetime)
    """
    if isinstance(date_str, datetime):
        return True, "", date_str
    
    if not date_str or not str(date_str).strip():
        return False, "Data vuota", None
    
    date_str = str(date_str).strip()
    
    # Try Excel serial date (number)
    try:
        serial = float(date_str)
        # Excel serial date starts from 1900-01-01 (but has leap year bug)
        # Serial 1 = 1900-01-01, but Excel incorrectly treats 1900 as leap year
        if serial >= 1:
            # Adjust for Excel's leap year bug
            if serial > 60:
                serial -= 1
            base_date = datetime(1899, 12, 31)
            parsed = base_date + timedelta(days=serial)
            return True, "", parsed
    except (ValueError, OverflowError):
        pass
    
    # Try common date formats
    formats = [
        "%d/%m/%Y",  # DD/MM/YYYY (Italian format)
        "%m/%d/%Y",  # MM/DD/YYYY (US format)
        "%Y-%m-%d",  # YYYY-MM-DD (ISO format)
        "%d-%m-%Y",  # DD-MM-YYYY
        "%Y/%m/%d",  # YYYY/MM/DD
        "%d.%m.%Y",  # DD.MM.YYYY
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return True, "", parsed
        except ValueError:
            continue
    
    return False, f"Formato data non riconosciuto: {date_str}", None


def validate_payment_amount(amount: str | float) -> tuple[bool, str, Optional[float]]:
    """
    Validate payment amount.
    
    Args:
        amount: Payment amount as string or float
        
    Returns:
        Tuple of (is_valid, error_message, parsed_amount)
    """
    if amount is None or (isinstance(amount, str) and not amount.strip()):
        return False, "Importo vuoto", None
    
    try:
        # Remove currency symbols and spaces
        if isinstance(amount, str):
            amount = amount.strip().replace("€", "").replace(",", ".").strip()
        
        amount_float = float(amount)
        
        if amount_float < 0:
            return False, "Importo negativo", None
        
        if amount_float > 999999.99:
            return False, "Importo troppo alto (massimo 999.999,99)", None
        
        # Round to 2 decimal places
        amount_float = round(amount_float, 2)
        
        return True, "", amount_float
        
    except (ValueError, TypeError):
        return False, f"Importo non valido: {amount}", None


def validate_payment_method(method: str) -> tuple[bool, str]:
    """
    Validate payment method.
    
    Args:
        method: Payment method string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not method or not method.strip():
        return False, "Metodo di pagamento vuoto"
    
    method = method.strip().upper()
    
    valid_methods = ["POS", "BOLLETTINO"]
    
    if method not in valid_methods:
        return False, f"Metodo di pagamento non valido (deve essere POS o Bollettino)"
    
    return True, ""


def check_period_overlap(
    start1: datetime, end1: datetime, start2: datetime, end2: datetime
) -> bool:
    """
    Check if two date periods overlap.
    
    Args:
        start1: Start date of first period
        end1: End date of first period
        start2: Start date of second period
        end2: End date of second period
        
    Returns:
        True if periods overlap, False otherwise
    """
    # Two periods overlap if:
    # - start1 is before end2 AND end1 is after start2
    return start1 <= end2 and end1 >= start2

