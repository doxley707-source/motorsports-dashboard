"""
Porsche Mobil 1 Supercup importer.

Parses the season schedule from the Wikipedia page for the current year.
The Supercup runs as a Formula 1 support series — one race per F1 weekend,
held on race day (Sunday). No API key required.

Note: Wikipedia provides the circuit and a date range (e.g. "4–7 June").
The race is taken as the last date in the range (Sunday of the F1 weekend).
No specific session time is available — date only.
"""

import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup
from utils.normalize import normalize_records

CURRENT_YEAR = datetime.now().year
SOURCE_URL = f"https://en.wikipedia.org/wiki/{CURRENT_YEAR}_Porsche_Supercup"
SOURCE_NAME = f"Wikipedia — {CURRENT_YEAR} Porsche Supercup"
SOURCE_TYPE = "third_party_reference"

WATCH_PLATFORM = "Apple TV+"
WATCH_URL = "https://tv.apple.com"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _parse_last_date(date_str: str, year: int) -> str:
    """
    Extract the last date from a range like '4–7 June' → '2026-06-07'.
    Falls back to the only date if no range.
    """
    clean = re.sub(r"[^\x20-\x7E]", " ", date_str).strip()

    # Look for patterns like "4-7 June" or "June 4-7"
    # Try: last number + month
    m = re.search(r"(\d+)\s+([A-Za-z]+)\s*$", clean)
    if m:
        day, month = m.group(1), m.group(2)
        for fmt in ("%d %B", "%d %b"):
            try:
                dt = datetime.strptime(f"{day} {month}", fmt)
                return f"{year}-{dt.month:02d}-{dt.day:02d}"
            except ValueError:
                continue

    # Try: month + last number  e.g. "June 4-7"
    m2 = re.search(r"([A-Za-z]+)\s+\d+\D+(\d+)", clean)
    if m2:
        month, day = m2.group(1), m2.group(2)
        for fmt in ("%B %d", "%b %d"):
            try:
                dt = datetime.strptime(f"{month} {day}", fmt)
                return f"{year}-{dt.month:02d}-{dt.day:02d}"
            except ValueError:
                continue

    # Try single date
    m3 = re.search(r"(\d+)\s+([A-Za-z]+)", clean)
    if m3:
        day, month = m3.group(1), m3.group(2)
        for fmt in ("%d %B", "%d %b"):
            try:
                dt = datetime.strptime(f"{day} {month}", fmt)
                return f"{year}-{dt.month:02d}-{dt.day:02d}"
            except ValueError:
                continue

    return ""


def _split_circuit_location(merged: str) -> tuple[str, str]:
    parts = merged.split(",", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return merged.strip(), ""


def run() -> tuple[list[dict], dict]:
    summary = {
        "series": "Formula 1 Group",
        "success": False,
        "added": 0,
        "errors": [],
    }

    try:
        resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        summary["errors"].append(f"Porsche Supercup fetch failed: {e}")
        return [], summary

    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table", class_="wikitable")

    # Find the schedule table (has Round, Circuit, Date columns)
    schedule_table = None
    for t in tables:
        hdrs = [th.get_text(strip=True).lower() for th in t.find("tr").find_all(["th", "td"])]
        if "round" in hdrs and "circuit" in hdrs:
            schedule_table = t
            break

    if schedule_table is None:
        summary["errors"].append("Porsche Supercup: no schedule table found on Wikipedia page.")
        return [], summary

    records = []
    for row in schedule_table.find_all("tr")[1:]:
        cells = [td.get_text(separator=" ", strip=True) for td in row.find_all(["td", "th"])]
        if len(cells) < 3:
            continue
        if cells[0].lower() in ("round", "rnd", "rnd.", "#"):
            continue

        # Columns: Round | Circuit+Location | Date [| Pole | FL | Winner | Team]
        circuit_raw = cells[1] if len(cells) > 1 else ""
        date_raw    = cells[2] if len(cells) > 2 else ""

        if not date_raw:
            continue

        circuit, location = _split_circuit_location(circuit_raw)
        date_iso = _parse_last_date(date_raw, CURRENT_YEAR)
        if not date_iso:
            continue

        round_num = cells[0].strip()
        event_name = f"Porsche Supercup Round {round_num}" if round_num.isdigit() else f"Porsche Supercup {circuit}"

        records.append({
            "series_group": "Formula 1",
            "series": "Porsche Mobil 1 Supercup",
            "event_name": event_name,
            "session_name": "Race",
            "session_type": "Race",
            "start_datetime": date_iso,
            "end_datetime": "",
            "estimated_duration_minutes": 60,
            "track": circuit,
            "location": location,
            "watch_platform": WATCH_PLATFORM,
            "watch_url": WATCH_URL,
            "is_televised_or_streamed": "Yes",
            "official_source_url": SOURCE_URL,
            "source_name": SOURCE_NAME,
            "source_type": SOURCE_TYPE,
            "data_confidence": "medium",
            "notes": "Race only — date only, no specific start time. Runs as F1 support series.",
        })

    if not records:
        summary["errors"].append("Porsche Supercup: parsed Wikipedia but found no race rows.")
        return [], summary

    summary["success"] = True
    summary["added"] = len(records)
    summary["errors"].append(
        "Note: Porsche Supercup race dates only — no start times available."
    )

    return normalize_records(records), summary
