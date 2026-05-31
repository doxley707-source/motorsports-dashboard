"""Session status labels based on current Eastern Time."""

from datetime import datetime, timedelta
from utils.timezone_utils import now_eastern, parse_iso, EASTERN
import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "series_config.json")

def _load_durations() -> dict:
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f).get("estimated_durations_minutes", {})
    except Exception:
        return {}


def get_session_status(row) -> str:
    """
    Returns one of:
      LIVE NOW | Starts in X min | Starts today at HH:MM | Upcoming | Completed
    """
    now = now_eastern()
    start = parse_iso(row.get("start_datetime", ""))
    end = parse_iso(row.get("end_datetime", ""))

    if start is None:
        return "Upcoming"

    # Estimate end time if not set
    if end is None:
        durations = _load_durations()
        session_type = str(row.get("session_type", "")).strip()
        duration_min = durations.get(session_type, 120)
        end = start + timedelta(minutes=duration_min)

    if now >= end:
        return "Completed"

    if now >= start:
        return "Live Now"

    diff = start - now
    total_minutes = int(diff.total_seconds() / 60)

    if total_minutes <= 60:
        return f"Starts in {total_minutes} min"

    # Same calendar day in Eastern
    if start.date() == now.date():
        return f"Starts today at {start.strftime('%I:%M %p').lstrip('0')}"  # no %-I on Windows

    return "Upcoming"


def status_sort_key(status: str) -> int:
    """Lower number = higher priority in sort order."""
    if status == "Live Now":
        return 0
    if status.startswith("Starts in"):
        return 1
    if status.startswith("Starts today"):
        return 2
    if status == "Upcoming":
        return 3
    return 4  # Completed
