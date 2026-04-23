import csv
import os
import sys
from pathlib import Path

import django

# =========================
# DJANGO SETUP
# =========================
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "contraceptive_chatbot.settings")
django.setup()

from chatbot.models import HealthFacility  # noqa: E402


CSV_FILE = BASE_DIR / "health_facilities.csv"


def parse_bool(value: str) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def parse_float(value: str, field_name: str, row_number: int) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid {field_name} at row {row_number}: {value!r}"
        )


def clean_text(value: str) -> str:
    return str(value).strip() if value is not None else ""


def validate_row(row: dict, row_number: int) -> dict:
    required_fields = [
        "name",
        "location",
        "latitude",
        "longitude",
        "facility_type",
        "offers_free_services",
        "services",
    ]

    missing = [field for field in required_fields if field not in row]
    if missing:
        raise ValueError(
            f"Missing required columns in CSV: {', '.join(missing)}"
        )

    facility_type = clean_text(row["facility_type"]).lower()
    allowed_types = {"hospital", "health_center", "private"}

    if facility_type not in allowed_types:
        raise ValueError(
            f"Invalid facility_type at row {row_number}: {facility_type!r}. "
            f"Allowed: {', '.join(sorted(allowed_types))}"
        )

    cleaned = {
        "name": clean_text(row["name"]),
        "location": clean_text(row["location"]),
        "latitude": parse_float(row["latitude"], "latitude", row_number),
        "longitude": parse_float(row["longitude"], "longitude", row_number),
        "facility_type": facility_type,
        "offers_free_services": parse_bool(row["offers_free_services"]),
        "services": clean_text(row["services"]),
    }

    if not cleaned["name"]:
        raise ValueError(f"Empty name at row {row_number}")

    if not cleaned["location"]:
        raise ValueError(f"Empty location at row {row_number}")

    if not cleaned["services"]:
        raise ValueError(f"Empty services at row {row_number}")

    return cleaned


def import_health_facilities() -> None:
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"CSV file not found: {CSV_FILE}")

    rows_to_create = []

    with open(CSV_FILE, mode="r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row.")

        for row_number, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue  # skip blank rows

            cleaned = validate_row(row, row_number)
            rows_to_create.append(HealthFacility(**cleaned))

    print(f"Validated {len(rows_to_create)} facility rows.")

    # Clear old rows first
    deleted_count, _ = HealthFacility.objects.all().delete()
    print(f"Deleted {deleted_count} existing facility rows.")

    # Bulk insert new rows
    HealthFacility.objects.bulk_create(rows_to_create, batch_size=100)
    print(f"Imported {len(rows_to_create)} new facility rows successfully.")


if __name__ == "__main__":
    try:
        import_health_facilities()
    except Exception as exc:
        print(f"Import failed: {exc}")
        raise