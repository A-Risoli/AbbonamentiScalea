"""Excel file parser and validator for subscription imports."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

from abbonamenti.validators import (
    check_period_overlap,
    validate_date,
    validate_email,
    validate_license_plate,
    validate_payment_amount,
)


def read_excel_file(
    file_path: str | Path,
    column_mapping: dict[str, str],
) -> tuple[bool, str, list[dict]]:
    """
    Read Excel file and extract data according to column mapping.

    Args:
        file_path: Path to Excel file
        column_mapping: Dict mapping field names to Excel column names
            Required keys: owner_name, license_plate, subscription_start,
            subscription_end, payment_details, payment_method
            Optional keys: email, address, mobile

    Returns:
        Tuple of (success, error_message, data_rows)
        where data_rows is a list of dicts with subscription data
    """
    try:
        # Load workbook and select first sheet
        workbook = openpyxl.load_workbook(file_path, data_only=True)
        sheet: Worksheet = workbook.active

        if sheet is None:
            return False, "Nessun foglio trovato nel file Excel", []

        # Get header row (assume first row is header)
        headers = []
        for cell in sheet[1]:
            headers.append(str(cell.value).strip() if cell.value else "")

        if not headers:
            return False, "Riga di intestazione vuota", []

        # Find column indices based on mapping
        column_indices = {}
        missing_columns = []

        for field_name, excel_col_name in column_mapping.items():
            if not excel_col_name:
                # Column not mapped
                continue

            try:
                idx = headers.index(excel_col_name)
                column_indices[field_name] = idx
            except ValueError:
                missing_columns.append(excel_col_name)

        if missing_columns:
            return (
                False,
                f"Colonne non trovate nel file: {', '.join(missing_columns)}",
                [],
            )

        # Check required fields are mapped
        required_fields = [
            "owner_name",
            "license_plate",
            "subscription_start",
            "payment_details",
        ]

        unmapped_required = [
            field for field in required_fields if field not in column_indices
        ]

        if unmapped_required:
            return (
                False,
                f"Campi obbligatori non mappati: {', '.join(unmapped_required)}",
                [],
            )

        # Extract data rows (skip header row)
        data_rows = []
        last_start_date = None  # Track last valid start date for carry-forward

        for row_num, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            # Skip empty rows
            if all(cell.value is None or str(cell.value).strip() == "" for cell in row):
                continue

            row_data = {"_row_number": row_num}

            for field_name, col_idx in column_indices.items():
                if col_idx < len(row):
                    cell_value = row[col_idx].value
                    row_data[field_name] = cell_value
                else:
                    row_data[field_name] = None

            # Handle subscription_start carry-forward logic
            current_start = row_data.get("subscription_start")
            if current_start is None or str(current_start).strip() == "":
                # No date in this row - use last valid date
                if last_start_date is None:
                    # First row with no date - store error marker
                    row_data["_missing_start_date"] = True
                else:
                    # Carry forward previous date
                    row_data["subscription_start"] = last_start_date
            else:
                # Valid date found - update last_start_date
                last_start_date = current_start

            data_rows.append(row_data)

        workbook.close()

        if not data_rows:
            return False, "Nessuna riga di dati trovata nel file", []

        return True, "", data_rows

    except FileNotFoundError:
        return False, f"File non trovato: {file_path}", []
    except PermissionError:
        return False, f"Permesso negato per leggere il file: {file_path}", []
    except Exception as e:
        return False, f"Errore nella lettura del file Excel: {str(e)}", []


def validate_all_rows(
    data_rows: list[dict],
    db_manager,
    progress_callback: Optional[callable] = None,
) -> tuple[bool, list[tuple[int, str, str]], list[dict]]:
    """
    Validate all data rows for import.

    Checks:
    - Field validation (license plate, email, dates, payment amount, payment method)
    - Date logic (end date after start date)
    - Duplicate license plates within file with overlapping periods
    - Duplicate license plates in database with overlapping periods

    Args:
        data_rows: List of dicts from read_excel_file()
        db_manager: DatabaseManager instance for duplicate checking
        progress_callback: Optional callback(current, total) for progress

    Returns:
        Tuple of (is_valid, errors, validated_rows)
        where errors is list of (row_number, field_name, error_message)
        and validated_rows is list of dicts with parsed/validated data
    """
    errors = []
    validated_rows = []
    total = len(data_rows)

    # Track plates within file for duplicate detection
    file_plates: dict[str, list[tuple[int, object, object]]] = {}

    for idx, row in enumerate(data_rows):
        row_num = row.get("_row_number", idx + 2)
        validated = {}
        row_has_errors = False

        # Check for missing start date on first row
        if row.get("_missing_start_date"):
            errors.append(
                (
                    row_num,
                    "subscription_start",
                    f"Data non disponibile per riga {row_num}",
                )
            )
            row_has_errors = True

        # Validate owner_name
        owner_name = row.get("owner_name", "")
        if not owner_name or not str(owner_name).strip():
            errors.append((row_num, "owner_name", "Nome proprietario vuoto"))
            row_has_errors = True
        else:
            validated["owner_name"] = str(owner_name).strip()

        # Validate license_plate
        license_plate = row.get("license_plate", "")
        is_valid, error_msg = validate_license_plate(str(license_plate))
        if not is_valid:
            errors.append((row_num, "license_plate", error_msg))
            row_has_errors = True
        else:
            validated["license_plate"] = str(license_plate).strip().upper()

        # Validate email (optional)
        email = row.get("email", "")
        is_valid, error_msg = validate_email(str(email) if email else "")
        if not is_valid:
            errors.append((row_num, "email", error_msg))
            row_has_errors = True
        else:
            validated["email"] = str(email).strip() if email else ""

        # Validate address (optional)
        address = row.get("address", "")
        validated["address"] = str(address).strip() if address else ""

        # Validate mobile (optional)
        mobile = row.get("mobile", "")
        validated["mobile"] = str(mobile).strip() if mobile else ""

        # Validate subscription_start
        start_date = row.get("subscription_start")
        is_valid, error_msg, parsed_start = validate_date(start_date)
        if not is_valid and not row.get("_missing_start_date"):
            errors.append((row_num, "subscription_start", error_msg))
            row_has_errors = True
        elif is_valid:
            validated["subscription_start"] = parsed_start

        # Validate or auto-set subscription_end
        end_date = row.get("subscription_end")
        if end_date is None or str(end_date).strip() == "":
            # Auto-set to Dec 31 of the start year
            if "subscription_start" in validated:
                start_year = validated["subscription_start"].year
                validated["subscription_end"] = datetime(start_year, 12, 31)
        else:
            is_valid, error_msg, parsed_end = validate_date(end_date)
            if not is_valid:
                errors.append((row_num, "subscription_end", error_msg))
                row_has_errors = True
            else:
                validated["subscription_end"] = parsed_end

        # Check date logic (end after start)
        if "subscription_start" in validated and "subscription_end" in validated:
            if validated["subscription_end"] < validated["subscription_start"]:
                errors.append(
                    (
                        row_num,
                        "subscription_end",
                        "Data fine deve essere successiva a data inizio",
                    )
                )
                row_has_errors = True

        # Validate payment_details
        payment = row.get("payment_details")
        is_valid, error_msg, parsed_amount = validate_payment_amount(payment)
        if not is_valid:
            errors.append((row_num, "payment_details", error_msg))
            row_has_errors = True
        else:
            validated["payment_details"] = parsed_amount

        # Validate payment_method from POS/Bollettino columns
        pos_value = row.get("pos", "")
        bollettino_value = row.get("bollettino", "")

        # Check if values are present (treat any non-empty value as marked)
        pos_marked = pos_value is not None and str(pos_value).strip() != ""
        bollettino_marked = (
            bollettino_value is not None and str(bollettino_value).strip() != ""
        )

        if pos_marked and bollettino_marked:
            errors.append(
                (
                    row_num,
                    "payment_method",
                    "Sia POS che Bollettino sono marcati (deve essere solo uno)",
                )
            )
            row_has_errors = True
        elif not pos_marked and not bollettino_marked:
            errors.append(
                (
                    row_num,
                    "payment_method",
                    "Né POS né Bollettino sono marcati (deve essere uno dei due)",
                )
            )
            row_has_errors = True
        elif pos_marked:
            validated["payment_method"] = "POS"
        else:
            validated["payment_method"] = "BOLLETTINO"

        # Track for duplicate checking within file
        if not row_has_errors and "license_plate" in validated:
            plate = validated["license_plate"]
            if plate not in file_plates:
                file_plates[plate] = []
            file_plates[plate].append(
                (
                    row_num,
                    validated["subscription_start"],
                    validated["subscription_end"],
                )
            )

        if not row_has_errors:
            validated_rows.append(validated)

        # Update progress
        if progress_callback:
            progress_callback(idx + 1, total)

    # Check for duplicates within file
    for plate, occurrences in file_plates.items():
        if len(occurrences) > 1:
            # Check for overlapping periods
            for i in range(len(occurrences)):
                for j in range(i + 1, len(occurrences)):
                    row_num_i, start_i, end_i = occurrences[i]
                    row_num_j, start_j, end_j = occurrences[j]

                    if check_period_overlap(start_i, end_i, start_j, end_j):
                        errors.append(
                            (
                                row_num_j,
                                "license_plate",
                                f"Targa duplicata con periodo sovrapposto "
                                f"(vedi riga {row_num_i})",
                            )
                        )

    # Check for duplicates in database
    for validated in validated_rows:
        plate = validated["license_plate"]
        existing_subs = db_manager.get_subscriptions_by_plate(plate)

        for existing in existing_subs:
            if check_period_overlap(
                validated["subscription_start"],
                validated["subscription_end"],
                existing["subscription_start"],
                existing["subscription_end"],
            ):
                # Find row number from original data
                row_num = None
                for row in data_rows:
                    if row.get(
                        "license_plate", ""
                    ).strip().upper() == plate and row.get("_row_number"):
                        row_num = row["_row_number"]
                        break

                if row_num:
                    start_str = existing["subscription_start"].strftime("%d/%m/%Y")
                    end_str = existing["subscription_end"].strftime("%d/%m/%Y")
                    errors.append(
                        (
                            row_num,
                            "license_plate",
                            f"Targa già esistente nel database con periodo sovrapposto "
                            f"(Protocollo: {existing['protocol_id']}, "
                            f"Periodo: {start_str} - {end_str})",
                        )
                    )

    is_valid = len(errors) == 0

    return is_valid, errors, validated_rows if is_valid else []
