"""
Normalize raw imported records into the standard events.csv schema.
Each importer returns a list of dicts; this module ensures every dict
has all required fields with consistent types.
"""

import uuid
from datetime import datetime

REQUIRED_FIELDS = [
    "event_id",
    "series_group",
    "series",
    "event_name",
    "session_name",
    "session_type",
    "start_datetime",
    "end_datetime",
    "timezone",
    "estimated_duration_minutes",
    "track",
    "location",
    "watch_platform",
    "watch_url",
    "is_televised_or_streamed",
    "official_source_url",
    "source_name",
    "source_type",
    "data_confidence",
    "notes",
    "last_updated",
]

DEFAULTS = {
    "event_id": "",
    "series_group": "",
    "series": "",
    "event_name": "",
    "session_name": "",
    "session_type": "",
    "start_datetime": "",
    "end_datetime": "",
    "timezone": "America/New_York",
    "estimated_duration_minutes": "",
    "track": "",
    "location": "",
    "watch_platform": "",
    "watch_url": "",
    "is_televised_or_streamed": "Unknown",
    "official_source_url": "",
    "source_name": "",
    "source_type": "",
    "data_confidence": "medium",
    "notes": "",
    "last_updated": "",
}


def normalize_record(raw: dict) -> dict:
    """Fill missing fields with defaults and assign a UUID if event_id is blank."""
    record = {field: raw.get(field, DEFAULTS[field]) for field in REQUIRED_FIELDS}
    if not record["event_id"]:
        record["event_id"] = str(uuid.uuid4())
    if not record["last_updated"]:
        record["last_updated"] = datetime.utcnow().isoformat()
    return record


def normalize_records(records: list[dict]) -> list[dict]:
    return [normalize_record(r) for r in records]
