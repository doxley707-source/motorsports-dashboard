"""
Motorsports Dashboard — main Streamlit app.
Run with:  streamlit run app.py
"""

import os
import json
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from utils.timezone_utils import now_eastern, parse_iso, format_time, format_date, EASTERN
from utils.status_utils import get_session_status, status_sort_key
from utils.backup_utils import backup_events_csv
from utils.data_quality import check_data_quality

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "data", "events.csv")
META_PATH = os.path.join(BASE_DIR, "data", "metadata.json")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Motorsports Dashboard",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=Barlow:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

  /* ── Global reset ── */
  html, body, [class*="css"] {
    font-family: 'Barlow', 'Segoe UI', sans-serif;
    background-color: #07071a;
  }
  .stApp { background-color: #07071a; }
  .block-container { padding-top: 0 !important; max-width: 960px; }

  /* ═══════════════════════════════════════════
     HERO HEADER
  ═══════════════════════════════════════════ */
  .hero {
    position: relative;
    background: linear-gradient(135deg, #0a001f 0%, #07071a 55%, #0c0028 100%);
    border-bottom: 1px solid #1a1040;
    padding: 28px 4px 20px 4px;
    margin-bottom: 20px;
    overflow: hidden;
  }
  /* Speed lines */
  .hero::before {
    content: '';
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
      -62deg,
      transparent 0px, transparent 22px,
      rgba(255,255,255,0.018) 22px, rgba(255,255,255,0.018) 23px
    );
    pointer-events: none;
  }
  /* Checkered corner */
  .hero::after {
    content: '';
    position: absolute;
    right: 0; top: 0; bottom: 0;
    width: 180px;
    background-image:
      linear-gradient(45deg, rgba(255,255,255,0.04) 25%, transparent 25%),
      linear-gradient(-45deg, rgba(255,255,255,0.04) 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, rgba(255,255,255,0.04) 75%),
      linear-gradient(-45deg, transparent 75%, rgba(255,255,255,0.04) 75%);
    background-size: 14px 14px;
    background-position: 0 0, 0 7px, 7px -7px, -7px 0px;
    -webkit-mask-image: linear-gradient(to right, transparent 0%, rgba(0,0,0,0.6) 100%);
    mask-image: linear-gradient(to right, transparent 0%, rgba(0,0,0,0.6) 100%);
    pointer-events: none;
  }
  .hero-inner {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .hero-flag {
    font-size: 2.4rem;
    line-height: 1;
    filter: drop-shadow(0 0 12px rgba(255,255,255,0.3));
  }
  .hero-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #ffffff;
    line-height: 1;
    text-shadow: 0 0 40px rgba(100,100,255,0.3);
  }
  .hero-title .accent { color: #00e5ff; }
  .hero-sub {
    font-family: 'Barlow', sans-serif;
    font-size: 0.8rem;
    font-weight: 500;
    color: #3d4a6b;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-top: 5px;
  }
  .hero-date-pill {
    margin-left: auto;
    text-align: right;
    font-family: 'Barlow Condensed', sans-serif;
  }
  .hero-date-pill .day {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #3d4a6b;
  }
  .hero-date-pill .date-num {
    font-size: 1.8rem;
    font-weight: 800;
    color: #1e1e4a;
    line-height: 1;
  }

  /* ═══════════════════════════════════════════
     CARDS
  ═══════════════════════════════════════════ */
  .session-card {
    background: linear-gradient(135deg, #0d0d22 0%, #111130 100%);
    border: 1px solid #1c1c3c;
    border-left: 4px solid var(--accent, #3949ab);
    border-radius: 0 12px 12px 0;
    padding: 14px 18px 12px 18px;
    margin-bottom: 10px;
    color: #e0e0f0;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
    box-shadow: 0 2px 10px rgba(0,0,0,0.5);
  }
  .session-card:hover {
    transform: translateX(3px);
    border-color: var(--accent, #3949ab);
    box-shadow: -6px 0 24px var(--accent-glow, rgba(57,73,171,0.2)), 0 4px 20px rgba(0,0,0,0.6);
  }
  .card-f1      { --accent: #e53935; --accent-glow: rgba(229,57,53,0.2); }
  .card-nascar  { --accent: #1565c0; --accent-glow: rgba(21,101,192,0.2); }
  .card-indycar { --accent: #2e7d32; --accent-glow: rgba(46,125,50,0.2); }
  .card-imsa    { --accent: #7b1fa2; --accent-glow: rgba(123,31,162,0.2); }

  .card-top {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    flex-wrap: wrap;
  }

  /* ── Status badges ── */
  @keyframes live-pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.7; }
  }
  @keyframes live-ring {
    0%   { box-shadow: 0 0 0 0 rgba(229,57,53,0.7); }
    70%  { box-shadow: 0 0 0 8px rgba(229,57,53,0); }
    100% { box-shadow: 0 0 0 0 rgba(229,57,53,0); }
  }
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 4px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .badge-live {
    background: #b71c1c;
    color: #fff;
    animation: live-ring 1.8s ease-out infinite;
  }
  .badge-live::before {
    content: '';
    width: 6px; height: 6px;
    background: #ff5252;
    border-radius: 50%;
    animation: live-pulse 1s ease-in-out infinite;
  }
  .badge-soon      { background: #e65100; color: #fff; border-radius: 4px; }
  .badge-today     { background: #1565c0; color: #fff; border-radius: 4px; }
  .badge-upcoming  { background: transparent; color: #455a64; border: 1px solid #1e1e3c; border-radius: 4px; }
  .badge-completed { background: transparent; color: #263238; border: 1px solid #131313; border-radius: 4px; }

  /* ── Group pills ── */
  .group-pill {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 4px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .group-f1      { background: #b71c1c; color: #fff; }
  .group-nascar  { background: #0d47a1; color: #fff; }
  .group-indycar { background: #1b5e20; color: #fff; }
  .group-imsa    { background: #4a148c; color: #fff; }
  .group-default { background: #263238; color: #90a4ae; }

  /* ── Card body ── */
  .card-series {
    font-family: 'Barlow', sans-serif;
    font-size: 0.75rem;
    color: #3d4a6b;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 3px;
  }
  .card-event {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    color: #eceff1;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    line-height: 1.1;
    margin-bottom: 3px;
  }
  .card-session {
    font-family: 'Barlow', sans-serif;
    font-size: 0.82rem;
    color: #455a64;
    font-weight: 500;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .session-icon { font-size: 0.85rem; }

  /* ── Card meta ── */
  .card-meta {
    display: flex;
    align-items: center;
    gap: 18px;
    flex-wrap: wrap;
    font-family: 'Barlow', sans-serif;
    font-size: 0.86rem;
    margin-bottom: 10px;
  }
  .card-time {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #00e5ff;
    text-transform: uppercase;
  }
  .card-location { color: #2a3a4a; font-size: 0.82rem; }

  /* ── Watch button ── */
  .card-watch {
    padding-top: 8px;
    border-top: 1px solid #12122a;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .watch-btn {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: rgba(0,229,255,0.06);
    border: 1px solid rgba(0,229,255,0.18);
    border-radius: 6px;
    padding: 5px 14px;
    font-family: 'Barlow', sans-serif;
    font-size: 0.8rem;
    font-weight: 600;
    color: #00e5ff;
    text-decoration: none;
    letter-spacing: 0.02em;
    transition: background 0.2s, border-color 0.2s, box-shadow 0.2s;
  }
  .watch-btn:hover {
    background: rgba(0,229,255,0.14);
    border-color: rgba(0,229,255,0.4);
    box-shadow: 0 0 12px rgba(0,229,255,0.15);
    text-decoration: none;
  }
  .watch-none    { color: #1e2a30; font-size: 0.8rem; font-style: italic; }
  .source-link a { color: #1e2a30; font-size: 0.72rem; text-decoration: none; }
  .source-link a:hover { color: #37474f; }

  /* ═══════════════════════════════════════════
     EVENT WEEKEND HEADER
  ═══════════════════════════════════════════ */
  .event-weekend-header {
    position: relative;
    margin: 36px 0 10px 0;
    padding: 14px 20px;
    background: linear-gradient(90deg, #090920 0%, #0b0b22 70%, #09091e 100%);
    border-left: 3px solid #00e5ff;
    border-radius: 0 8px 8px 0;
    overflow: hidden;
  }
  .event-weekend-header::after {
    content: '';
    position: absolute;
    right: 0; top: 0; bottom: 0;
    width: 160px;
    background-image:
      linear-gradient(45deg, rgba(255,255,255,0.025) 25%, transparent 25%),
      linear-gradient(-45deg, rgba(255,255,255,0.025) 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, rgba(255,255,255,0.025) 75%),
      linear-gradient(-45deg, transparent 75%, rgba(255,255,255,0.025) 75%);
    background-size: 12px 12px;
    background-position: 0 0, 0 6px, 6px -6px, -6px 0;
    -webkit-mask-image: linear-gradient(to right, transparent 0%, black 100%);
    mask-image: linear-gradient(to right, transparent 0%, black 100%);
  }
  .ewh-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: #d0d8f0;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    position: relative;
    z-index: 1;
  }
  .ewh-meta {
    font-family: 'Barlow', sans-serif;
    font-size: 0.72rem;
    color: #2a3550;
    margin-top: 3px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    position: relative;
    z-index: 1;
  }

  /* ═══════════════════════════════════════════
     NEXT-UP / SECTION LABELS
  ═══════════════════════════════════════════ */
  .next-up-label {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.8rem;
    font-weight: 700;
    color: #00e5ff;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin: 28px 0 10px 0;
    padding-left: 10px;
    border-left: 2px solid #00e5ff;
  }

  /* ═══════════════════════════════════════════
     EMPTY STATE
  ═══════════════════════════════════════════ */
  .no-sessions {
    text-align: center;
    color: #1e2a30;
    font-family: 'Barlow', sans-serif;
    font-size: 1rem;
    padding: 72px 24px;
    line-height: 1.9;
  }
  .no-sessions strong {
    font-family: 'Barlow Condensed', sans-serif;
    color: #2a3a4a;
    display: block;
    font-size: 1.3rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  /* ═══════════════════════════════════════════
     MISC
  ═══════════════════════════════════════════ */
  .refresh-ok   { color: #66bb6a; }
  .refresh-fail { color: #ef5350; }
  .refresh-warn { color: #ffa726; }
  .last-refreshed {
    font-family: 'Barlow', sans-serif;
    font-size: 0.72rem;
    color: #1e2a30;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_events() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        return pd.DataFrame()
    try:
        df = pd.read_csv(DATA_PATH, dtype=str)
        df = df.fillna("")
        return df
    except Exception:
        return pd.DataFrame()


def load_metadata() -> dict:
    if not os.path.exists(META_PATH):
        return {}
    try:
        with open(META_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_metadata(meta: dict):
    os.makedirs(os.path.dirname(META_PATH), exist_ok=True)
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)


def group_pill_html(group: str) -> str:
    cls = {
        "Formula 1": "group-f1",
        "NASCAR": "group-nascar",
        "IndyCar": "group-indycar",
        "IMSA": "group-imsa",
    }.get(group, "group-default")
    return f'<span class="group-pill {cls}">{group}</span>'


def badge_html(status: str) -> str:
    cls = "badge-upcoming"
    if status == "Live Now":
        cls = "badge-live"
    elif status.startswith("Starts in"):
        cls = "badge-soon"
    elif status.startswith("Starts today"):
        cls = "badge-today"
    elif status == "Completed":
        cls = "badge-completed"
    # Live Now gets no text prefix — the pulsing dot CSS handles it
    label = status
    return f'<span class="badge {cls}">{label}</span>'


def is_date_only(dt_str: str) -> bool:
    """True if the stored datetime is a date with no time (e.g. IMSA Wikipedia rows)."""
    s = str(dt_str).strip()
    return bool(s) and "T" not in s and s not in ("", "nan", "NaT", "None") and len(s) == 10


def watch_html(row, view: str = "lookahead") -> str:
    url        = str(row.get("watch_url", "")).strip()
    platform   = str(row.get("watch_platform", "")).strip()
    is_stream  = str(row.get("is_televised_or_streamed", "")).strip().lower()
    source_url = str(row.get("official_source_url", "")).strip()

    source_part = f'<span class="source-link"><a href="{source_url}" target="_blank">↗ Source</a></span>' if source_url else ""

    if is_stream in ("no", "false", "0", "not televised"):
        return f'<span class="watch-none">Not televised</span> {source_part}'
    if not url and not platform:
        msg = "No stream listed yet" if view in ("today", "weekend") else "Watch info TBA"
        return f'<span class="watch-none">{msg}</span> {source_part}'
    if url:
        label = platform if platform else "Watch"
        return f'<a class="watch-btn" href="{url}" target="_blank">📺 {label}</a> {source_part}'
    return f'<span class="watch-btn" style="cursor:default;">📺 {platform}</span> {source_part}'


def render_card(row, view: str = "lookahead"):
    dt_str = str(row.get("start_datetime", "")).strip()
    date_only = is_date_only(dt_str)

    if date_only:
        # For date-only events, derive status purely from date comparison
        from utils.timezone_utils import now_eastern
        import datetime as _dt
        try:
            event_date = _dt.date.fromisoformat(dt_str)
            today = now_eastern().date()
            if event_date < today:
                status = "Completed"
            elif event_date == today:
                status = "Today"
            else:
                status = "Upcoming"
        except ValueError:
            status = "Upcoming"
        time_display = f'📅 Date only — time TBA'
        time_color = "#546e7a"
    else:
        status = get_session_status(row.to_dict())
        start = parse_iso(dt_str)
        time_val = format_time(start)
        time_display = f'🕐 {time_val}'
        time_color = "#4dd0e1"

    track = str(row.get("track", "")).strip()
    location = str(row.get("location", "")).strip()
    place = " · ".join(filter(None, [track, location]))
    place_html = f'<span class="card-location">📍 {place}</span>' if place else ""

    series = str(row.get("series", "")).strip()
    group = str(row.get("series_group", "")).strip()
    event_name = str(row.get("event_name", "")).strip()
    session_name = str(row.get("session_name", "")).strip()

    # Per-series accent CSS class
    accent_cls = {
        "Formula 1": "card-f1",
        "NASCAR":    "card-nascar",
        "IndyCar":   "card-indycar",
        "IMSA":      "card-imsa",
    }.get(group, "")

    # Session type icon
    session_type = str(row.get("session_type", "")).strip()
    icon = {
        "Practice":          "🔧",
        "Qualifying":        "⏱️",
        "Sprint Qualifying": "⚡",
        "Sprint":            "⚡",
        "Warmup":            "🔄",
        "Race":              "🏁",
    }.get(session_type, "🏎️")

    series_line = ""
    if series and series.lower() != group.lower():
        series_line = f'<div class="card-series">{series}</div>'

    html = f"""
    <div class="session-card {accent_cls}">
      <div class="card-top">{badge_html(status)}{group_pill_html(group)}</div>
      {series_line}
      <div class="card-event">{event_name}</div>
      <div class="card-session"><span class="session-icon">{icon}</span>{session_name}</div>
      <div class="card-meta">
        <span class="card-time">{time_display}</span>
        {place_html}
      </div>
      <div class="card-watch">{watch_html(row, view)}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def filter_by_group(df: pd.DataFrame, selected: str) -> pd.DataFrame:
    if not selected or selected == "All":
        return df
    return df[df["series_group"] == selected]


def get_weekend_range():
    now = now_eastern()
    # Thursday = weekday 3
    days_since_thu = (now.weekday() - 3) % 7
    thursday = now.date() - timedelta(days=days_since_thu)
    sunday = thursday + timedelta(days=3)
    return thursday, sunday


# ── Refresh logic ─────────────────────────────────────────────────────────────

def run_refresh() -> list[dict]:
    from importers import import_f1, import_nascar, import_indycar, import_imsa

    results = []
    all_new_records = []

    importers = [
        ("Formula 1 Group", import_f1),
        ("NASCAR Cup Series", import_nascar),
        ("NTT IndyCar Series", import_indycar),
        ("IMSA Group", import_imsa),
    ]

    for label, module in importers:
        try:
            records, summary = module.run()
            all_new_records.extend(records)
            results.append(summary)
        except Exception as e:
            results.append({
                "series": label,
                "success": False,
                "added": 0,
                "errors": [f"Unexpected error: {e}"],
            })

    if all_new_records:
        # Back up existing CSV first
        backup_path = backup_events_csv()

        # Load existing data
        existing_df = load_events()
        new_df = pd.DataFrame(all_new_records)

        if existing_df.empty:
            merged = new_df
        else:
            # Drop old rows only for series_groups that actually returned new data.
            # Derive the groups to replace from the new records themselves — always exact.
            refreshed_groups = set(new_df["series_group"].dropna().unique())
            retained = existing_df[~existing_df["series_group"].isin(refreshed_groups)]
            merged = pd.concat([retained, new_df], ignore_index=True)

        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        merged.to_csv(DATA_PATH, index=False)

        # Save metadata
        meta = load_metadata()
        meta["last_refreshed"] = now_eastern().strftime("%Y-%m-%d %I:%M %p ET")
        meta["last_refresh_results"] = results
        save_metadata(meta)
    else:
        # No new data — save metadata noting the attempt
        meta = load_metadata()
        meta["last_refresh_attempted"] = now_eastern().strftime("%Y-%m-%d %I:%M %p ET")
        meta["last_refresh_results"] = results
        save_metadata(meta)

    return results


# ── Auto-refresh on startup (cloud deployments) ───────────────────────────────

def _needs_startup_refresh() -> bool:
    """True if the data file is missing or older than 23 hours."""
    if not os.path.exists(DATA_PATH):
        return True
    try:
        age_hours = (datetime.now().timestamp() - os.path.getmtime(DATA_PATH)) / 3600
        return age_hours > 23
    except Exception:
        return True


# ── Main UI ───────────────────────────────────────────────────────────────────

def main():
    # Auto-refresh on cloud: run once per session if data is missing or stale
    if "startup_refresh_done" not in st.session_state:
        st.session_state.startup_refresh_done = True
        if _needs_startup_refresh():
            with st.spinner("Loading schedule data…"):
                run_refresh()
            st.rerun()

    meta = load_metadata()
    last_refreshed = meta.get("last_refreshed", None)
    _now = now_eastern()

    # ── Hero header ──
    st.markdown(f"""
    <div class="hero">
      <div class="hero-inner">
        <div class="hero-flag">🏁</div>
        <div>
          <div class="hero-title">MOTORSPORTS <span class="accent">DASHBOARD</span></div>
          <div class="hero-sub">2026 Season &nbsp;·&nbsp; All times Eastern
            {"&nbsp;·&nbsp; Last refreshed " + last_refreshed if last_refreshed else "&nbsp;·&nbsp; Data not loaded yet"}
          </div>
        </div>
        <div class="hero-date-pill">
          <div class="day">{_now.strftime("%A")}</div>
          <div class="date-num">{_now.strftime("%b %d").replace(" 0"," ")}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_refresh, col_spacer = st.columns([1, 5])
    with col_refresh:
        do_refresh = st.button("🔄 Refresh All Schedules", use_container_width=True)

    if do_refresh:
        with st.spinner("Refreshing all schedules..."):
            results = run_refresh()
        st.success("Refresh complete.")
        for r in results:
            if r.get("success"):
                st.markdown(f'<span class="refresh-ok">✔ {r["series"]}: {r["added"]} sessions loaded.</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="refresh-fail">✘ {r["series"]}: refresh failed.</span>', unsafe_allow_html=True)
            for err in r.get("errors", []):
                if str(err).startswith("Note:"):
                    st.markdown(f'<span style="color:#546e7a;font-size:0.85rem;">&nbsp;&nbsp;ℹ {err}</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span class="refresh-warn">&nbsp;&nbsp;→ {err}</span>', unsafe_allow_html=True)
        st.rerun()

    # Load data
    df = load_events()

    # Series filter — pill buttons
    selected_group = st.pills(
        "Series:",
        options=["All", "Formula 1", "NASCAR", "IndyCar", "IMSA"],
        default="All",
        key="group_filter",
    )
    if not selected_group:
        selected_group = "All"

    df_filtered = filter_by_group(df, selected_group)

    # Tabs
    tab_today, tab_weekend, tab_lookahead, tab_issues = st.tabs([
        "Today", "This Weekend", "Look Ahead", "Data Issues"
    ])

    now = now_eastern()
    today = now.date()
    thu, sun = get_weekend_range()

    # ── Tab: Today ────────────────────────────────────────────────────────────
    with tab_today:
        st.caption(f"Sessions for {now.strftime('%A, %B %d').replace(' 0',' ')} · All times Eastern")
        today_rows = []
        for _, row in df_filtered.iterrows():
            start = parse_iso(row.get("start_datetime", ""))
            if start and start.date() == today:
                today_rows.append(row)

        if not today_rows:
            st.markdown('<div class="no-sessions"><strong>No racing today.</strong></div>', unsafe_allow_html=True)

            # Show the next day(s) that have sessions
            preview_rows = []
            for _, row in df_filtered.iterrows():
                start = parse_iso(row.get("start_datetime", ""))
                if start and start.date() > today:
                    preview_rows.append(row)
            preview_rows.sort(key=lambda r: str(r.get("start_datetime", "")))

            if preview_rows:
                next_start = parse_iso(preview_rows[0].get("start_datetime", ""))
                next_date  = next_start.date()
                days_away  = (next_date - today).days
                day_label  = "Tomorrow" if days_away == 1 else f"In {days_away} days"
                next_day_rows = [r for r in preview_rows
                                 if parse_iso(r.get("start_datetime","")) and
                                 parse_iso(r.get("start_datetime","")).date() == next_date]
                st.markdown(
                    f'<div class="next-up-label">Next up · {day_label} · {format_date(next_start)}</div>',
                    unsafe_allow_html=True,
                )
                for row in next_day_rows:
                    render_card(row, view="today")
        else:
            today_rows.sort(key=lambda r: (
                status_sort_key(get_session_status(r.to_dict())),
                str(r.get("start_datetime", ""))
            ))
            issues = check_data_quality(pd.DataFrame([r.to_dict() for r in today_rows]), view="today")
            if issues:
                with st.expander(f"⚠️ {len(issues)} data issue(s) in today's sessions"):
                    for i in issues:
                        st.markdown(f"- {i}")
            for row in today_rows:
                render_card(row, view="today")

    # ── Tab: This Weekend ─────────────────────────────────────────────────────
    with tab_weekend:
        thu_str = thu.strftime("%b %d").replace(" 0", " ")
        sun_str = sun.strftime("%b %d").replace(" 0", " ")
        st.caption(f"Thu {thu_str} – Sun {sun_str} · All times Eastern")
        weekend_rows = []
        for _, row in df_filtered.iterrows():
            start = parse_iso(row.get("start_datetime", ""))
            if start and thu <= start.date() <= sun:
                weekend_rows.append(row)

        if not weekend_rows:
            st.markdown(
                '<div class="no-sessions"><strong>No sessions this weekend.</strong>'
                'Check Look Ahead for the next race weekend.</div>',
                unsafe_allow_html=True,
            )
        else:
            weekend_rows.sort(key=lambda r: str(r.get("start_datetime", "")))
            issues = check_data_quality(pd.DataFrame([r.to_dict() for r in weekend_rows]), view="weekend")
            if issues:
                with st.expander(f"⚠️ {len(issues)} data issue(s) this weekend"):
                    for i in issues:
                        st.markdown(f"- {i}")

            # Group by event weekend (same logic as Look Ahead)
            from collections import defaultdict
            event_groups_wknd: dict[tuple, list] = defaultdict(list)
            for row in weekend_rows:
                key = (str(row.get("event_name", "")).strip(),
                       str(row.get("series_group", "")).strip())
                event_groups_wknd[key].append(row)

            sorted_wknd = sorted(
                event_groups_wknd.items(),
                key=lambda x: min(str(r.get("start_datetime", "")) for r in x[1])
            )

            for (event_name, series_group), rows in sorted_wknd:
                rows.sort(key=lambda r: str(r.get("start_datetime", "")))
                starts = [parse_iso(r.get("start_datetime", "")) for r in rows if parse_iso(r.get("start_datetime", ""))]
                if starts:
                    first, last = min(starts), max(starts)
                    date_range = format_date(first) if first.date() == last.date() else (
                        f"{first.strftime('%b %d').replace(' 0',' ')} – {last.strftime('%b %d').replace(' 0',' ')}"
                    )
                else:
                    date_range = "Date TBD"

                st.markdown(f"""
                <div class="event-weekend-header">
                  <div class="ewh-name">{event_name or "Event TBD"}</div>
                  <div class="ewh-meta">{series_group or "Racing"} &nbsp;·&nbsp; {date_range}</div>
                </div>""", unsafe_allow_html=True)
                for row in rows:
                    render_card(row, view="weekend")

    # ── Tab: Look Ahead ───────────────────────────────────────────────────────
    with tab_lookahead:
        st.caption("All upcoming sessions · All times Eastern · Watch info may not be available for distant events")
        future_rows = []
        for _, row in df_filtered.iterrows():
            start = parse_iso(row.get("start_datetime", ""))
            if start and start.date() >= today:
                future_rows.append(row)

        if not future_rows:
            st.markdown(
                '<div class="no-sessions"><strong>No upcoming sessions found.</strong>'
                'Click Refresh All Schedules to load the latest schedule data.</div>',
                unsafe_allow_html=True,
            )
        else:
            future_rows.sort(key=lambda r: str(r.get("start_datetime", "")))

            # Group by (event_name, series_group) so all sessions of a race weekend
            # are shown together rather than split across date headers.
            from collections import defaultdict
            event_groups: dict[tuple, list] = defaultdict(list)
            for row in future_rows:
                key = (str(row.get("event_name", "")).strip(),
                       str(row.get("series_group", "")).strip())
                event_groups[key].append(row)

            # Sort groups by their earliest session
            sorted_groups = sorted(
                event_groups.items(),
                key=lambda x: min(str(r.get("start_datetime", "")) for r in x[1])
            )

            for (event_name, series_group), rows in sorted_groups:
                rows.sort(key=lambda r: str(r.get("start_datetime", "")))
                starts = [parse_iso(r.get("start_datetime", "")) for r in rows]
                starts = [s for s in starts if s]

                if starts:
                    first, last = min(starts), max(starts)
                    if first.date() == last.date():
                        date_range = format_date(first)
                    else:
                        d1 = first.strftime("%b %d").replace(" 0", " ")
                        d2 = last.strftime("%b %d").replace(" 0", " ")
                        date_range = f"{d1} – {d2}"
                else:
                    date_range = "Date TBD"

                series_group_display = series_group or "Racing"
                header_html = f"""
                <div class="event-weekend-header">
                  <div class="ewh-name">{event_name or "Event TBD"}</div>
                  <div class="ewh-meta">{series_group_display} &nbsp;·&nbsp; {date_range}</div>
                </div>"""
                st.markdown(header_html, unsafe_allow_html=True)
                for row in rows:
                    render_card(row, view="lookahead")

    # ── Tab: Data Issues ──────────────────────────────────────────────────────
    with tab_issues:
        st.markdown("### Data Quality & Issues")
        if df_filtered.empty:
            st.info("No data loaded yet. Click 'Refresh All Schedules' to import schedule data.")
        else:
            all_issues = check_data_quality(df_filtered, view="lookahead")
            last_results = meta.get("last_refresh_results", [])

            if last_results:
                st.markdown("**Last refresh summary:**")
                for r in last_results:
                    icon  = "✔" if r.get("success") else "✘"
                    color = "#66bb6a" if r.get("success") else "#ef5350"
                    st.markdown(f'<span style="color:{color}">{icon} {r["series"]}: {r["added"]} sessions</span>', unsafe_allow_html=True)
                    for err in r.get("errors", []):
                        if str(err).startswith("Note:"):
                            st.markdown(f'<span style="color:#455a64;font-size:0.82rem;">&nbsp;&nbsp;ℹ {err}</span>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<span style="color:#ffa726;font-size:0.82rem;">&nbsp;&nbsp;→ {err}</span>', unsafe_allow_html=True)

            st.markdown("---")
            if all_issues:
                st.markdown(f"**{len(all_issues)} data issue(s) found:**")
                for i in all_issues:
                    st.markdown(f"- {i}")
            else:
                st.success("No data quality issues detected.")

            if meta.get("last_refreshed"):
                st.caption(f"Last refreshed: {meta['last_refreshed']}")
            elif meta.get("last_refresh_attempted"):
                st.caption(f"Last refresh attempted: {meta['last_refresh_attempted']}")


if __name__ == "__main__":
    main()
