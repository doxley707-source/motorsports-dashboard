"""
Formula 1 importer.

Session schedule: Jolpica API (free, no key) — named sessions with UTC times.
Broadcast info:  ESPN F1 API (free, no key) — per-session platform/channel.

The two sources are merged by matching session UTC times within a 45-minute
window, so each card gets the correct broadcast info for that session.

Jolpica docs: https://github.com/jolpica/jolpica-f1
"""

import requests
from datetime import datetime, timezone, timedelta
from utils.normalize import normalize_records

CURRENT_YEAR = datetime.now().year

JOLPICA_URL  = f"https://api.jolpi.ca/ergast/f1/{CURRENT_YEAR}/races/?limit=100"
ESPN_URL     = f"https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard?limit=100&dates={CURRENT_YEAR}"

SOURCE_NAME  = "Jolpica F1 API + ESPN F1"
SOURCE_TYPE  = "community_api"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Fallback watch info if ESPN has no broadcast listed for a session
FALLBACK_PLATFORM = "Apple TV+"
FALLBACK_URL      = "https://tv.apple.com"

SESSION_MAP = {
    "fp1":              ("Practice 1",       "Practice"),
    "fp2":              ("Practice 2",       "Practice"),
    "fp3":              ("Practice 3",       "Practice"),
    "qualifying":       ("Qualifying",       "Qualifying"),
    "sprint_qualifying":("Sprint Qualifying","Sprint Qualifying"),
    "sprint":           ("Sprint",           "Sprint"),
    "race":             ("Race",             "Race"),
}

# Known platform → watch URL
PLATFORM_URLS = {
    "Apple TV":    "https://tv.apple.com",
    "Apple TV+":   "https://tv.apple.com",
    "ESPN":        "https://www.espn.com/watch/",
    "ESPN2":       "https://www.espn.com/watch/",
    "ESPN+":       "https://www.espn.com/watch/",
    "ABC":         "https://abc.com/watch-live-tv",
    "FOX":         "https://www.fox.com/live/",
    "Sky Sports":  "https://www.skysports.com/watch",
}


def _to_utc(dt_str: str) -> datetime | None:
    """Parse an ISO string to a UTC-aware datetime."""
    if not dt_str:
        return None
    try:
        s = str(dt_str).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        elif "T" in s and "+" not in s and not s.endswith("Z"):
            s += "+00:00"  # assume UTC if no tz given
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None


def _parse_jolpica_dt(date_str: str, time_str: str) -> str:
    """Combine Jolpica date + time into an ISO string."""
    if not date_str:
        return ""
    time_str = (time_str or "00:00:00Z").replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(f"{date_str}T{time_str}").isoformat()
    except ValueError:
        return f"{date_str}T{time_str}"


def _fetch_espn_broadcast_index() -> dict[str, list[dict]]:
    """
    Fetch the ESPN F1 scoreboard and build a lookup:
      { "YYYY-MM-DD": [ { "dt": datetime, "platform": str, "url": str }, ... ] }
    Keyed by calendar date (UTC) so we can quickly find matches for a session.
    """
    index: dict[str, list[dict]] = {}
    try:
        resp = requests.get(ESPN_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        events = resp.json().get("events", [])
    except Exception:
        return index

    for event in events:
        for comp in event.get("competitions", []):
            dt = _to_utc(comp.get("date", ""))
            if dt is None:
                continue
            geo = comp.get("geoBroadcasts", [])
            raw = comp.get("broadcast", "")
            platforms = [g.get("media", {}).get("shortName", "") for g in geo if g.get("media", {}).get("shortName")]
            if not platforms and raw:
                platforms = [p.strip() for p in raw.split("/") if p.strip()]
            platform_str = " / ".join(platforms) if platforms else FALLBACK_PLATFORM

            watch_url = FALLBACK_URL
            for name, url in PLATFORM_URLS.items():
                if name in platform_str:
                    watch_url = url
                    break

            date_key = dt.strftime("%Y-%m-%d")
            index.setdefault(date_key, []).append({
                "dt": dt,
                "platform": platform_str,
                "url": watch_url,
            })

    return index


def _match_broadcast(session_dt: datetime | None, espn_index: dict) -> tuple[str, str]:
    """
    Find the ESPN entry closest to session_dt (within 45 min).
    Returns (platform, watch_url).
    """
    if session_dt is None:
        return FALLBACK_PLATFORM, FALLBACK_URL

    date_key = session_dt.strftime("%Y-%m-%d")
    candidates = espn_index.get(date_key, [])

    best = None
    best_delta = timedelta(minutes=45)
    for entry in candidates:
        delta = abs(session_dt - entry["dt"])
        if delta < best_delta:
            best_delta = delta
            best = entry

    if best:
        return best["platform"], best["url"]
    return FALLBACK_PLATFORM, FALLBACK_URL


def fetch_f1() -> tuple[list[dict], list[str]]:
    errors = []

    # Fetch session schedule from Jolpica
    try:
        resp = requests.get(JOLPICA_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        races = resp.json()["MRData"]["RaceTable"]["Races"]
    except Exception as e:
        errors.append(f"F1 fetch failed: {e}")
        return [], errors

    # Fetch broadcast info from ESPN (best-effort — don't fail if ESPN is down)
    espn_index = _fetch_espn_broadcast_index()
    if not espn_index:
        errors.append("F1: ESPN broadcast data unavailable — using Apple TV+ as fallback for all sessions.")

    records = []
    for race in races:
        event_name = race.get("raceName", "")
        track      = race.get("Circuit", {}).get("circuitName", "")
        loc_info   = race.get("Circuit", {}).get("Location", {})
        location   = f"{loc_info.get('locality','')}, {loc_info.get('country','')}".strip(", ")

        sessions = {
            "fp1":               race.get("FirstPractice",    {}),
            "fp2":               race.get("SecondPractice",   {}),
            "fp3":               race.get("ThirdPractice",    {}),
            "qualifying":        race.get("Qualifying",       {}),
            "sprint_qualifying": race.get("SprintQualifying", {}),
            "sprint":            race.get("Sprint",           {}),
            "race":              {"date": race.get("date"), "time": race.get("time")},
        }

        for key, session_data in sessions.items():
            if not session_data or not session_data.get("date"):
                continue

            session_name, session_type = SESSION_MAP[key]
            start_iso = _parse_jolpica_dt(session_data.get("date", ""), session_data.get("time", ""))
            session_dt = _to_utc(start_iso)
            platform, watch_url = _match_broadcast(session_dt, espn_index)

            records.append({
                "series_group":    "Formula 1",
                "series":          "Formula 1",
                "event_name":      event_name,
                "session_name":    session_name,
                "session_type":    session_type,
                "start_datetime":  start_iso,
                "end_datetime":    "",
                "track":           track,
                "location":        location,
                "watch_platform":  platform,
                "watch_url":       watch_url,
                "is_televised_or_streamed": "Yes",
                "official_source_url": JOLPICA_URL,
                "source_name":     SOURCE_NAME,
                "source_type":     SOURCE_TYPE,
                "data_confidence": "high",
                "notes":           "",
            })

    return normalize_records(records), errors


def run() -> tuple[list[dict], dict]:
    from importers.import_supercup import run as supercup_run

    summary = {"series": "Formula 1 Group", "success": False, "added": 0, "errors": []}

    f1_records, f1_errors             = fetch_f1()
    supercup_records, supercup_summary = supercup_run()
    sc_errors = supercup_summary.get("errors", [])

    all_records       = f1_records + supercup_records
    summary["errors"] = f1_errors + sc_errors
    summary["added"]  = len(all_records)
    summary["success"] = len(f1_records) > 0

    return all_records, summary
