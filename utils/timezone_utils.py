"""Timezone conversion helpers — all display times are Eastern."""

from datetime import datetime, timezone
import zoneinfo

EASTERN = zoneinfo.ZoneInfo("America/New_York")
UTC = timezone.utc


def to_eastern(dt: datetime) -> datetime:
    """Convert a timezone-aware datetime to Eastern Time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(EASTERN)


def now_eastern() -> datetime:
    """Return current time in Eastern Time."""
    return datetime.now(EASTERN)


def parse_iso(value: str) -> datetime | None:
    """Parse an ISO 8601 string and return an Eastern-time datetime, or None."""
    if not value or str(value).strip() in ("", "nan", "NaT", "None"):
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip())
        return to_eastern(dt)
    except (ValueError, TypeError):
        return None


def format_time(dt: datetime | None) -> str:
    """Return a human-readable time string like '2:30 PM ET'."""
    if dt is None:
        return "Time TBD"
    return dt.strftime("%I:%M %p ET").lstrip("0")


def format_date(dt: datetime | None) -> str:
    """Return a human-readable date string like 'Saturday, June 7'."""
    if dt is None:
        return "Date TBD"
    return dt.strftime("%A, %B %d").replace(" 0", " ")
