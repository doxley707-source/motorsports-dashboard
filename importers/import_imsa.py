"""
IMSA importer — all five series from Wikipedia schedule tables.

Series covered:
  - IMSA WeatherTech SportsCar Championship
  - IMSA Michelin Pilot Challenge
  - Porsche Carrera Cup North America
  - Mazda MX-5 Cup
  - Lamborghini Super Trofeo North America

Wikipedia is used as a reliable third-party source because the official
IMSA website blocks automated requests. No API key required.

Note: Wikipedia provides race names and dates only — no session times,
no practice/qualifying. Only the main race event per round is imported.
"""

import requests
import re
import os
import json
import zoneinfo
from datetime import datetime, date, timezone
from bs4 import BeautifulSoup
from utils.normalize import normalize_records

CURRENT_YEAR = datetime.now().year
EASTERN = zoneinfo.ZoneInfo("America/New_York")
RACE_TIMES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "imsa_race_times.json"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

WATCH_PLATFORM = "Peacock / NBC / USA Network"
WATCH_URL = "https://www.peacocktv.com"

# Each entry: (series name, Wikipedia page slug, table index, column map)
# column map keys: race_name, circuit, location, date, duration (all are column indices, -1 = not present)
SERIES_CONFIG = [
    {
        "series": "IMSA WeatherTech SportsCar Championship",
        "wiki_slug": f"{CURRENT_YEAR}_IMSA_WeatherTech_SportsCar_Championship",
        "table_index": 0,
        "cols": {"race_name": 1, "length": 2, "circuit": 4, "location": 5, "date": 6},
    },
    {
        "series": "IMSA Michelin Pilot Challenge",
        "wiki_slug": f"{CURRENT_YEAR}_Michelin_Pilot_Challenge",
        "table_index": 0,
        "cols": {"race_name": 1, "circuit": 2, "location": 3, "date": 4, "length": 5},
    },
    {
        "series": "Porsche Carrera Cup North America",
        "wiki_slug": f"{CURRENT_YEAR}_Porsche_Carrera_Cup_North_America",
        "table_index": 0,
        # Headers: Round | Circuit+Location merged | Date
        "cols": {"race_name": -1, "circuit_location": 1, "date": 2},
    },
    {
        "series": "Mazda MX-5 Cup",
        "wiki_slug": f"{CURRENT_YEAR}_Mazda_MX-5_Cup",
        "table_index": 0,
        # Headers: Round | Round label | Circuit | Location | Dates | Supporting
        "cols": {"race_name": -1, "circuit": 2, "location": 3, "date": 4},
    },
    {
        "series": "Lamborghini Super Trofeo North America",
        "wiki_slug": f"{CURRENT_YEAR}_Lamborghini_Super_Trofeo_North_America",
        "table_index": 0,
        # Headers: Rnd | Circuit+Location merged | Date | Supporting
        "cols": {"race_name": -1, "circuit_location": 1, "date": 2},
    },
]

DURATION_MAP = {
    "24 hours": 1440, "12 hours": 720, "10 hours": 600,
    "8 hours": 480,   "6 hours": 360,  "4 hours": 240,
    "3 hours": 180,   "2 hours": 120,  "100 minutes": 100,
    "160 minutes": 160, "120 minutes": 120,
}


def _parse_duration(length_str: str) -> int:
    s = length_str.lower().strip()
    for key, val in DURATION_MAP.items():
        if key in s:
            return val
    m = re.search(r"(\d+)\s*min", s)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*hour", s)
    if m:
        return int(m.group(1)) * 60
    return 120


def _parse_date(date_str: str, year: int) -> str:
    """Convert 'January 24' or 'January 24-25' to '2026-01-24'."""
    clean = re.split(r"[–—\-]", date_str)[0].strip()
    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", clean).strip()
    clean = re.sub(r"[^\x20-\x7E]", "", clean).strip()
    for fmt in ("%B %d", "%d %B", "%b %d", "%d %b"):
        try:
            dt = datetime.strptime(clean, fmt)
            return f"{year}-{dt.month:02d}-{dt.day:02d}"
        except ValueError:
            continue
    return ""


def _load_race_times() -> dict:
    """Load curated race start times. Returns {} if missing or wrong season."""
    try:
        with open(RACE_TIMES_PATH) as f:
            data = json.load(f)
        if data.get("season") != CURRENT_YEAR:
            return {}
        return data
    except Exception:
        return {}


def _apply_race_time(record: dict, overlay: dict) -> bool:
    """If a curated race time matches this record, upgrade its date-only
    start_datetime to a full UTC datetime. Returns True if applied.

    A match requires BOTH a track/event keyword hit AND the curated date
    within 3 days of the Wikipedia date — so a rescheduled event falls back
    to date-only rather than showing a stale wrong time."""
    if overlay.get("series") != record.get("series"):
        return False
    if record.get("session_type") != "Race":
        return False

    haystack = " ".join([
        record.get("event_name", ""),
        record.get("track", ""),
        record.get("location", ""),
    ]).lower()

    try:
        wiki_date = date.fromisoformat(record["start_datetime"])
    except (ValueError, KeyError):
        return False

    for race in overlay.get("races", []):
        if not any(kw in haystack for kw in race.get("match", [])):
            continue
        try:
            curated_date = date.fromisoformat(race["date"])
            hour, minute = map(int, race["time_et"].split(":"))
        except (ValueError, KeyError):
            continue
        if abs((curated_date - wiki_date).days) > 3:
            continue

        start_et = datetime(curated_date.year, curated_date.month,
                            curated_date.day, hour, minute, tzinfo=EASTERN)
        record["start_datetime"] = start_et.astimezone(timezone.utc).isoformat()
        if race.get("platform"):
            record["watch_platform"] = race["platform"]
        record["data_confidence"] = "high"
        record["notes"] = (
            f"Race start time from {overlay.get('source', 'broadcast schedule')}."
            + (f" {race['note']}." if race.get("note") else "")
        )
        return True
    return False


def _split_circuit_location(merged: str) -> tuple[str, str]:
    """Split 'Sebring International Raceway,Sebring, Florida' into (circuit, location)."""
    parts = merged.split(",", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return merged.strip(), ""


def _fetch_series(config: dict) -> tuple[list[dict], list[str]]:
    series = config["series"]
    url = f"https://en.wikipedia.org/wiki/{config['wiki_slug']}"
    cols = config["cols"]
    errors = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        errors.append(f"{series}: fetch failed — {e}")
        return [], errors

    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table", class_="wikitable")

    idx = config.get("table_index", 0)
    if not tables or idx >= len(tables):
        errors.append(f"{series}: no schedule table found on Wikipedia page.")
        return [], errors

    rows = tables[idx].find_all("tr")[1:]
    records = []

    for row in rows:
        cells = [td.get_text(separator=" ", strip=True) for td in row.find_all(["td", "th"])]
        if len(cells) < 2:
            continue

        # Skip repeat header rows
        if cells[0].lower() in ("round", "rnd", "rnd.", "#"):
            continue

        try:
            # Race / event name
            if cols.get("race_name", -1) >= 0 and cols["race_name"] < len(cells):
                race_name = cells[cols["race_name"]]
            else:
                race_name = f"{series} Round {cells[0]}"

            # Circuit and location
            if "circuit_location" in cols and cols["circuit_location"] < len(cells):
                circuit, location = _split_circuit_location(cells[cols["circuit_location"]])
            else:
                circuit  = cells[cols["circuit"]]  if cols.get("circuit",  -1) >= 0 and cols.get("circuit",  -1) < len(cells) else ""
                location = cells[cols["location"]] if cols.get("location", -1) >= 0 and cols.get("location", -1) < len(cells) else ""

            # Date
            date_raw = cells[cols["date"]] if cols.get("date", -1) >= 0 and cols["date"] < len(cells) else ""
            date_iso = _parse_date(date_raw, CURRENT_YEAR) if date_raw else ""

            # Duration
            length_raw = cells[cols["length"]] if cols.get("length", -1) >= 0 and cols.get("length", -1) < len(cells) else ""
            duration = _parse_duration(length_raw) if length_raw else 120

        except (IndexError, KeyError):
            continue

        if not race_name or not date_iso:
            continue

        records.append({
            "series_group": "IMSA",
            "series": series,
            "event_name": race_name,
            "session_name": "Race",
            "session_type": "Race",
            "start_datetime": date_iso,
            "end_datetime": "",
            "estimated_duration_minutes": duration,
            "track": circuit,
            "location": location,
            "watch_platform": WATCH_PLATFORM,
            "watch_url": WATCH_URL,
            "is_televised_or_streamed": "Yes",
            "official_source_url": url,
            "source_name": f"Wikipedia — {CURRENT_YEAR} {series}",
            "source_type": "third_party_reference",
            "data_confidence": "medium",
            "notes": "Race only — no session times available. Date only (no start time).",
        })

    if not records:
        errors.append(f"{series}: parsed Wikipedia but found no race rows — table structure may have changed.")

    return records, errors


def run() -> tuple[list[dict], dict]:
    summary = {
        "series": "IMSA Group",
        "success": False,
        "added": 0,
        "errors": [],
    }

    all_records = []

    for config in SERIES_CONFIG:
        records, errors = _fetch_series(config)
        all_records.extend(records)
        summary["errors"].extend(errors)

    overlay = _load_race_times()
    timed = sum(_apply_race_time(r, overlay) for r in all_records) if overlay else 0

    summary["success"] = len(all_records) > 0
    summary["added"] = len(all_records)

    if summary["success"]:
        if timed:
            summary["errors"].append(
                f"Note: {timed} WeatherTech race start times applied from the "
                f"{CURRENT_YEAR} broadcast schedule. Other IMSA series remain date-only."
            )
        else:
            summary["errors"].append(
                "Note: IMSA data from Wikipedia — race dates only, no session times."
            )

    return normalize_records(all_records), summary
