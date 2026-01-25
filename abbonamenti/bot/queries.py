"""License plate validation queries for the bot."""

import re
from datetime import date, timedelta

from abbonamenti.database.manager import DatabaseManager


def check_plate_validity(
    db_manager: DatabaseManager, plate: str, threshold_days: int = 7
) -> tuple[str, str, date | None]:
    """
    Check license plate validity across all subscriptions.

    Args:
        db_manager: Database manager instance
        plate: License plate to check (will be sanitized)
        threshold_days: Days before expiry to consider "expiring" (default: 7)

    Returns:
        Tuple of (status_code, message, expiry_date):
        - status_code: "valid", "expiring", or "not_found"
        - message: Formatted message for user
        - expiry_date: Nearest expiry date if valid, None otherwise
    """
    # Sanitize input
    plate_clean = sanitize_plate(plate)

    if not plate_clean:
        return ("not_found", "❌ Targa non valida", None)

    # Get all subscriptions for this plate
    try:
        subscriptions = db_manager.get_subscriptions_by_plate(plate_clean)
    except Exception as e:
        import logging
        logging.error(f"Errore query DB per targa {plate_clean}: {e}", exc_info=True)
        return ("not_found", "❌ Errore durante la ricerca", None)

    if not subscriptions:
        return ("not_found", "❌ NON VALIDO o SCADUTO", None)

    # Filter for currently valid subscriptions 
    # (subscription_start <= today <= subscription_end)
    today = date.today()
    valid_subscriptions = []
    
    for sub in subscriptions:
        try:
            # Handle both string and datetime formats
            start = sub["subscription_start"]
            end = sub["subscription_end"]
            
            # Convert to date if datetime
            if hasattr(start, "date"):
                start = start.date()
            else:
                # Try to parse if string
                from datetime import datetime
                if isinstance(start, str):
                    start = datetime.fromisoformat(start).date()
                    
            if hasattr(end, "date"):
                end = end.date()
            else:
                if isinstance(end, str):
                    from datetime import datetime
                    end = datetime.fromisoformat(end).date()
            
            if start <= today <= end:
                valid_subscriptions.append(sub)
        except (ValueError, TypeError):
            continue

    if not valid_subscriptions:
        return ("not_found", "❌ NON VALIDO o SCADUTO", None)

    # Find nearest expiry date (sort by subscription_end ascending)
    def get_end_date(sub):
        end = sub["subscription_end"]
        if hasattr(end, "date"):
            return end.date()
        elif isinstance(end, str):
            from datetime import datetime
            return datetime.fromisoformat(end).date()
        return end

    valid_subscriptions.sort(key=get_end_date)
    nearest_expiry = get_end_date(valid_subscriptions[0])

    # Format expiry date as DD/MM/YYYY
    expiry_formatted = nearest_expiry.strftime("%d/%m/%Y")

    # Check if expiring soon
    days_until_expiry = (nearest_expiry - today).days

    if days_until_expiry <= threshold_days:
        return (
            "expiring",
            f"⏰ IN SCADENZA (entro {threshold_days} giorni)! Scade: {expiry_formatted}",
            nearest_expiry,
        )

    return ("valid", f"✅ VALIDO! Scade: {expiry_formatted}", nearest_expiry)


def sanitize_plate(plate: str) -> str:
    """
    Sanitize license plate input.

    Removes special characters, normalizes to uppercase, limits length.

    Args:
        plate: Raw plate input

    Returns:
        Sanitized plate string
    """
    # Strip whitespace
    plate = plate.strip()

    # Remove special characters, keep only alphanumeric
    plate = re.sub(r"[^A-Za-z0-9]", "", plate)

    # Normalize to uppercase
    plate = plate.upper()

    # Limit to 20 characters
    plate = plate[:20]

    return plate
