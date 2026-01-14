import os
from pathlib import Path


def get_app_data_dir() -> Path:
    path = ""
    app_data = os.getenv("APPDATA")

    if app_data:
        path = Path(app_data) / "AbbonamentiScalea"
    else:
        path = Path.home() / ".abbonamenti_scalea"
    return path


def get_database_path() -> Path:
    return get_app_data_dir() / "database.db"


def get_keys_dir() -> Path:
    return get_app_data_dir() / "keys"


def get_backups_dir() -> Path:
    backups_dir = get_app_data_dir() / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir
