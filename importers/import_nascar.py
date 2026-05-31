"""
NASCAR Cup Series importer.

Uses the ESPN hidden API which returns race events with broadcast info.
No API key required.

Note: Session-level data (practice, qualifying) is not available from any
free public source. Only race events are imported. Practice/qualifying
sessions can be added manually to data/events.csv.
"""

import requests
from datetime import datetime, timezone
from utils.normalize import normalize_records

CURRENT_YEAR = datetime.now().year
SOURCE_NAME = "ESPN Racing API"
SOURCE_URL = f"https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard?limit=100&dates={CURRENT_YEAR}"
SOURCE_TYPE = "third_party_api"
SERIES_PAGE_URL = "https://www.nascar.com/nascar-cup-series/2026/schedule/"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _get_broadcast(competition: dict) -> tuple[str, str]:
    """Extract watch platform and URL from a competition object."""
    geo = competition.get("geoBroadcasts", [])
    raw = competition.get("broadcast", "")

    platforms = []
    for g in geo:
        name = g.get("media", {}).get("shortName", "")
        if name and name not in platforms:
            platforms.append(name)

    if not platforms and raw:
        platforms = [p.strip() for p in raw.split("/")]

    platform_str = " / ".join(platforms) if platforms else ""

    # Map known platforms to their watch URLs
    url_map = {
        "FOX":         "https://www.fox.com/live/",
        "FS1":         "https://www.foxsports.com/live",
        "NBC":         "https://www.nbc.com/live",
        "USA":         "https://www.usanetwork.com/live",
        "USA Network": "https://www.usanetwork.com/live",
        "TNT":         "https://www.tntdrama.com/live-tv",
        "Prime Video": "https://www.amazon.com/primevideo",
        "HBO Max":     "https://www.max.com",
        "Max":         "https://www.max.com",
        "Peacock":     "https://www.peacocktv.com",
        "ESPN":        "https://www.espn.com/watch/",
        "ESPN2":       "https://www.espn.com/watch/",
    }

    watch_url = ""
    for name, url in url_map.items():
        if name in platform_str:
            watch_url = url
            break

    return platform_str, watch_url


def run() -> tuple[list[dict], dict]:
    summary = {
        "series": "NASCAR Cup Series",
        "success": False,
        "added": 0,
        "errors": [],
    }

    try:
        resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        events = resp.json().get("events", [])
    except Exception as e:
        summary["errors"].append(f"NASCAR fetch failed: {e}")
        return [], summary

    if not events:
        summary["errors"].append("NASCAR: no events returned from ESPN API.")
        return [], summary

    records = []
    now_utc = datetime.now(timezone.utc)

    for event in events:
        name = event.get("name", "")
        date_str = event.get("date", "")
        if not date_str:
            continue

        comp = event.get("competitions", [{}])[0]
        platform, watch_url = _get_broadcast(comp)
        is_streamed = "Yes" if platform else "No"

        # Extract location from event name ("NASCAR Cup Series at Nashville" -> "Nashville")
        location = ""
        if " at " in name:
            location = name.split(" at ", 1)[-1].strip()

        records.append({
            "series_group": "NASCAR",
            "series": "NASCAR Cup Series",
            "event_name": name,
            "session_name": "Race",
            "session_type": "Race",
            "start_datetime": date_str,
            "end_datetime": "",
            "track": "",
            "location": location,
            "watch_platform": platform,
            "watch_url": watch_url,
            "is_televised_or_streamed": is_streamed,
            "official_source_url": SERIES_PAGE_URL,
            "source_name": SOURCE_NAME,
            "source_type": SOURCE_TYPE,
            "data_confidence": "high",
            "notes": "Race only — practice/qualifying times not available from free sources.",
        })

    summary["success"] = len(records) > 0
    summary["added"] = len(records)
    if summary["success"]:
        summary["errors"].append(
            "Note: practice and qualifying sessions are not available from free sources — only race events imported."
        )

    return normalize_records(records), summary
