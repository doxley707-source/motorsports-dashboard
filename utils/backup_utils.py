"""Create timestamped backups of events.csv before any refresh overwrites it."""

import os
import shutil
from datetime import datetime

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "events.csv")
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "backups")


def backup_events_csv() -> str | None:
    """
    Copy data/events.csv to data/backups/events_YYYYMMDD_HHMMSS.csv.
    Returns the backup path, or None if the source file did not exist.
    """
    if not os.path.exists(DATA_PATH):
        return None

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"events_{timestamp}.csv")
    shutil.copy2(DATA_PATH, dest)
    return dest


def list_backups() -> list[str]:
    """Return a sorted list of backup file paths (oldest first)."""
    if not os.path.exists(BACKUP_DIR):
        return []
    files = [
        os.path.join(BACKUP_DIR, f)
        for f in os.listdir(BACKUP_DIR)
        if f.startswith("events_") and f.endswith(".csv")
    ]
    return sorted(files)
