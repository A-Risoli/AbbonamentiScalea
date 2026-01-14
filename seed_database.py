#!/usr/bin/env python3
"""Script to seed the database with configurable subscription records."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from random import choice, random, randint

from abbonamenti.database.manager import DatabaseManager
from abbonamenti.utils.paths import get_app_data_dir, get_database_path, get_keys_dir


# Italian names for realistic data generation
FIRST_NAMES = [
    "Marco", "Giovanni", "Antonio", "Giuseppe", "Francesco", "Paolo", "Luigi",
    "Andrea", "Vincenzo", "Alessio", "Maria", "Rosa", "Anna", "Francesca",
    "Giuseppina", "Angela", "Carmela", "Lucia", "Silvia", "Valentina",
    "Claudia", "Martina", "Alessandra", "Sara", "Chiara", "Lisa", "Federica",
]

LAST_NAMES = [
    "Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Colombo", "Rizzo",
    "Marino", "Greco", "Bruno", "Gallo", "Conti", "De Luca", "Costa",
    "Giordano", "Barbieri", "Riccardo", "Lombardi", "Moretti", "Marchetti",
    "Ferrara", "Messina", "Fabbri", "Bernardi", "Gatti", "Carbone", "Grisanti",
]

EMAIL_DOMAINS = [
    "gmail.com", "outlook.com", "hotmail.com", "yahoo.it", "libero.it",
    "email.it", "virgilio.it", "tiscali.it", "tin.it", "alice.it",
]

CITIES = [
    "Roma", "Milano", "Napoli", "Torino", "Palermo", "Genova", "Bologna",
    "Firenze", "Bari", "Catania", "Venezia", "Verona", "Messina", "Padova",
    "Trieste", "Brescia", "Parma", "Pisa", "Modena", "Reggio Calabria",
]

STREETS = [
    "Via Roma", "Via Milano", "Via Verdi", "Via Dante", "Via Garibaldi",
    "Piazza Principale", "Corso Principale", "Viale Centrale", "Via Nazionale",
    "Via dei Gonzaga", "Via Manzoni", "Via Boccaccio", "Via Petrarca",
]

PAYMENT_METHODS = ["Bollettino", "POS"]


def generate_realistic_name() -> tuple[str, str]:
    """Generate a realistic Italian name."""
    return choice(FIRST_NAMES), choice(LAST_NAMES)


def generate_realistic_email(first_name: str, last_name: str) -> str:
    """Generate a realistic email address."""
    separator = choice([".", "_", ""])
    base = f"{first_name.lower()}{separator}{last_name.lower()}"
    return f"{base}@{choice(EMAIL_DOMAINS)}"


def generate_license_plate() -> str:
    """Generate an Italian-style license plate."""
    return f"{chr(65 + randint(0, 25))}{chr(65 + randint(0, 25))}" \
           f"{randint(0, 999):03d}{chr(65 + randint(0, 25))}{chr(65 + randint(0, 25))}"


def generate_address() -> str:
    """Generate a realistic Italian address."""
    street = choice(STREETS)
    number = randint(1, 150)
    city = choice(CITIES)
    return f"{street} {number}, {city}"


def generate_mobile() -> str:
    """Generate an Italian mobile phone number."""
    return f"+39 {randint(300, 399)} {randint(1000000, 9999999)}"


def get_payment_method_distribution(
    bollettino_pct: float, pos_pct: float
) -> str:
    """Select payment method based on distribution percentages."""
    total = bollettino_pct + pos_pct
    normalized = random() * 100
    
    if normalized < (bollettino_pct / total * 100):
        return "Bollettino"
    else:
        return "POS"


def generate_sample_data(
    index: int,
    start_date: datetime,
    end_date: datetime,
    bollettino_pct: float,
    pos_pct: float,
) -> dict:
    """Generate sample subscription data for a given index."""
    first_name, last_name = generate_realistic_name()
    
    # Randomize subscription dates within the specified range
    days_span = (end_date - start_date).days
    random_days = randint(0, days_span)
    sub_start = start_date + timedelta(days=random_days)
    sub_end = sub_start + timedelta(days=randint(30, 365))
    
    return {
        "owner_name": f"{first_name} {last_name}",
        "license_plate": generate_license_plate(),
        "email": generate_realistic_email(first_name, last_name),
        "address": generate_address(),
        "mobile": generate_mobile(),
        "subscription_start": sub_start,
        "subscription_end": sub_end,
        "payment_details": round(50.0 + (index % 100) + random() * 50, 2),
        "payment_method": get_payment_method_distribution(
            bollettino_pct, pos_pct
        ),
    }


def seed_database(
    count: int = 10000,
    start_date: datetime = None,
    end_date: datetime = None,
    bollettino_pct: float = 30.0,
    pos_pct: float = 50.0,
):
    """Populate database with sample subscription records."""
    if start_date is None:
        start_date = datetime(2025, 1, 1)
    if end_date is None:
        end_date = datetime(2026, 3, 31)
    
    # Normalize percentages
    total_pct = bollettino_pct + pos_pct 
    bollettino_pct = (bollettino_pct / total_pct) * 100
    pos_pct = (pos_pct / total_pct) * 100
    
    db_path = get_database_path()
    keys_dir = get_keys_dir()

    db_manager = DatabaseManager(db_path, keys_dir)

    print(f"Starting to seed database with {count} records...")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"Payment distribution: {bollettino_pct:.1f}% Bollettino, "
          f"{pos_pct:.1f}% POS")

    for i in range(1, count + 1):
        data = generate_sample_data(
            i,
            start_date,
            end_date,
            bollettino_pct,
            pos_pct,
        )
        try:
            protocol_id = db_manager.add_subscription(
                owner_name=data["owner_name"],
                license_plate=data["license_plate"],
                email=data["email"],
                address=data["address"],
                mobile=data["mobile"],
                subscription_start=data["subscription_start"],
                subscription_end=data["subscription_end"],
                payment_details=data["payment_details"],
                payment_method=data["payment_method"],
                reason=f"Bulk seed: record {i}/{count}",
            )
            if i % 500 == 0:
                print(f"✓ Inserted {i}/{count} records... (latest: {protocol_id})")
        except Exception as e:
            print(f"✗ Error inserting record {i}: {e}")
            return False

    print(f"✓ Successfully seeded database with {count} records!")
    return True


def main():
    """Parse arguments and seed database."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Seed the database with sample subscription records."
    )
    parser.add_argument(
        "--count", type=int, default=10000,
        help="Number of records to generate (default: 10000)"
    )
    parser.add_argument(
        "--start-date", type=str, default="2025-01-01",
        help="Start date for subscriptions (YYYY-MM-DD, default: 2025-01-01)"
    )
    parser.add_argument(
        "--end-date", type=str, default="2026-03-31",
        help="End date for subscriptions (YYYY-MM-DD, default: 2026-03-31)"
    )
    parser.add_argument(
        "--bollettino", type=float, default=30.0,
        help="Percentage of BOLLETTINO payments (default: 30.0)"
    )
    parser.add_argument(
        "--pos", type=float, default=50.0,
        help="Percentage of POS payments (default: 50.0)"
    )
    
    args = parser.parse_args()
    
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError as e:
        print(f"✗ Invalid date format: {e}")
        return False
    
    if start_date >= end_date:
        print("✗ Start date must be before end date")
        return False
    
    success = seed_database(
        count=args.count,
        start_date=start_date,
        end_date=end_date,
        bollettino_pct=args.bollettino,
        pos_pct=args.pos,
    )
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

