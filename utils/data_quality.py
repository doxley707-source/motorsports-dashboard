"""
Scan events DataFrame for data quality issues and return a list of
human-readable issue strings to display in the dashboard.

Design goals:
  - Flag real problems (missing times, bad session types, duplicates).
  - Suppress noise from known source limitations so the tab stays useful.
  - Group similar issues together rather than repeating one line per row.
"""

import pandas as pd
from collections import Counter


# Series whose watch info comes from a single generic platform link —
# missing per-session URLs are expected and not flagged.
_GENERIC_WATCH_SERIES = {
    "IMSA WeatherTech SportsCar Championship",
    "IMSA Michelin Pilot Challenge",
    "Porsche Carrera Cup North America",
    "Mazda MX-5 Cup",
    "Lamborghini Super Trofeo North America",
    "Porsche Mobil 1 Supercup",
}

# Series that only provide race events — missing practice/qualifying is expected.
_RACE_ONLY_SERIES = {
    "NASCAR Cup Series",
    "NTT IndyCar Series",
}

VALID_SESSION_TYPES = {"Practice", "Qualifying", "Sprint Qualifying", "Sprint", "Warmup", "Race"}


def check_data_quality(df: pd.DataFrame, view: str = "lookahead") -> list[str]:
    """
    Returns a concise list of issue strings grouped by type.
    view: 'today', 'weekend', or 'lookahead'
    """
    if df.empty:
        return []

    watch_views = {"today", "weekend"}
    issues: list[str] = []

    missing_time:    list[str] = []
    bad_type:        list[str] = []
    missing_watch:   list[str] = []
    missing_source:  list[str] = []

    for _, row in df.iterrows():
        series       = str(row.get("series", "?")).strip()
        session_name = str(row.get("session_name", "?")).strip()
        label        = f"{series} — {session_name}"
        dt_str       = str(row.get("start_datetime", "")).strip()

        # Missing start time (date-only strings are acceptable, full blank is not)
        if not dt_str or dt_str in ("", "nan", "NaT", "None"):
            missing_time.append(label)

        # Unknown session type
        stype = str(row.get("session_type", "")).strip()
        if stype not in VALID_SESSION_TYPES:
            bad_type.append(f"'{stype}' ({label})")

        # Missing watch info — only flag for Today/Weekend, and skip known-limited series
        if view in watch_views and series not in _GENERIC_WATCH_SERIES:
            has_watch = (
                str(row.get("watch_url", "")).strip() not in ("", "nan")
                or str(row.get("watch_platform", "")).strip() not in ("", "nan")
            )
            if not has_watch:
                televised = str(row.get("is_televised_or_streamed", "")).strip().lower()
                if televised not in ("no", "false", "0", "not televised", "no stream listed"):
                    missing_watch.append(label)

        # Missing source URL — only flag if truly blank (not a known-limited series)
        src = str(row.get("official_source_url", "")).strip()
        if not src or src in ("", "nan") and series not in _GENERIC_WATCH_SERIES:
            missing_source.append(label)

    # Build grouped issue strings
    def _group(items: list[str], prefix: str, limit: int = 3) -> None:
        if not items:
            return
        if len(items) <= limit:
            for item in items:
                issues.append(f"{prefix}: {item}")
        else:
            # Show first few examples + count
            examples = ", ".join(items[:limit])
            issues.append(f"{prefix} ({len(items)} sessions): e.g. {examples} …")

    _group(missing_time,   "Missing start time")
    _group(bad_type,       "Unknown session type")
    _group(missing_watch,  "Missing watch info")
    _group(missing_source, "Missing source URL")

    # Duplicate detection (grouped)
    dup_cols = ["series", "session_name", "start_datetime"]
    if all(c in df.columns for c in dup_cols):
        dupes = df[df.duplicated(subset=dup_cols, keep=False)]
        if not dupes.empty:
            issues.append(f"{len(dupes)} possible duplicate rows detected — try refreshing to clear.")

    return issues
