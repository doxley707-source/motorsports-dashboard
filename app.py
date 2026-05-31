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
  @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=Barlow:wght@400;500;600;700&display=swap');

  /* ── Global ── */
  html, body, [class*="css"] {
    font-family: 'Barlow', 'Segoe UI', sans-serif;
    background-color: #0a0a0f;
  }
  .stApp { background-color: #0a0a0f; }
  .block-container { padding-top: 0 !important; max-width: 980px; }

  /*
   * COLOR SYSTEM
   * --page-bg:    #0a0a0f  (near-black neutral)
   * --card-bg:    #111117  (dark neutral, no blue cast)
   * --card-border:#1e1e26
   * --gold:       #f5a623  (primary accent — warm contrast against dark)
   * --cyan:       #00e5ff  (timing display only)
   * --text-hi:    #f0f0f0
   * --text-mid:   #6b7280  (neutral gray)
   * --text-lo:    #374151
   */

  /* ═══════════════════════════════════════════
     HERO
  ═══════════════════════════════════════════ */
  .hero {
    position: relative;
    background: #0a0a0f;
    border-bottom: 2px solid #f5a623;
    padding: 24px 16px 20px 16px;
    margin-bottom: 20px;
    overflow: hidden;
  }
  /* Diagonal speed lines */
  .hero::before {
    content: '';
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
      -62deg,
      transparent 0px, transparent 24px,
      rgba(245,166,35,0.04) 24px, rgba(245,166,35,0.04) 25px
    );
    pointer-events: none;
  }
  /* Checkered flag fade on the right */
  .hero::after {
    content: '';
    position: absolute;
    right: 0; top: 0; bottom: 0;
    width: 140px;
    background-image:
      linear-gradient(45deg, rgba(255,255,255,0.05) 25%, transparent 25%),
      linear-gradient(-45deg, rgba(255,255,255,0.05) 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, rgba(255,255,255,0.05) 75%),
      linear-gradient(-45deg, transparent 75%, rgba(255,255,255,0.05) 75%);
    background-size: 12px 12px;
    background-position: 0 0, 0 6px, 6px -6px, -6px 0;
    -webkit-mask-image: linear-gradient(to right, transparent 0%, rgba(0,0,0,0.5) 100%);
    mask-image: linear-gradient(to right, transparent 0%, rgba(0,0,0,0.5) 100%);
    pointer-events: none;
  }
  .hero-inner {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
  }
  .hero-flag {
    font-size: 2rem;
    line-height: 1;
    flex-shrink: 0;
  }
  .hero-text { flex: 1; min-width: 0; }
  .hero-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: clamp(1.6rem, 5vw, 2.2rem);
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #f0f0f0;
    line-height: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .hero-title .accent { color: #f5a623; }
  .hero-sub {
    font-family: 'Barlow', sans-serif;
    font-size: 0.75rem;
    font-weight: 500;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-top: 5px;
  }
  .hero-date {
    flex-shrink: 0;
    text-align: right;
    font-family: 'Barlow Condensed', sans-serif;
    border-left: 1px solid #1e1e26;
    padding-left: 14px;
  }
  .hero-date .day-label {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #4b5563;
    display: block;
  }
  .hero-date .date-val {
    font-size: clamp(1.3rem, 3vw, 1.7rem);
    font-weight: 800;
    color: #f5a623;
    line-height: 1.1;
    display: block;
  }

  /* ═══════════════════════════════════════════
     CARDS
  ═══════════════════════════════════════════ */
  .session-card {
    background: linear-gradient(135deg, #111117 0%, #15151c 100%);
    border: 1px solid #1e1e26;
    border-left: 4px solid var(--accent, #f5a623);
    border-radius: 0 10px 10px 0;
    padding: 14px 18px 12px 16px;
    margin-bottom: 10px;
    color: #e8e8e8;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.5);
  }
  .session-card:hover {
    transform: translateX(3px);
    box-shadow: -6px 0 20px var(--accent-glow, rgba(245,166,35,0.15)), 0 4px 16px rgba(0,0,0,0.6);
  }
  /* Series-specific accent colors */
  .card-f1      { --accent: #e53935; --accent-glow: rgba(229,57,53,0.18); }
  .card-nascar  { --accent: #1565c0; --accent-glow: rgba(21,101,192,0.18); }
  .card-indycar { --accent: #2e7d32; --accent-glow: rgba(46,125,50,0.18); }
  .card-imsa    { --accent: #7b1fa2; --accent-glow: rgba(123,31,162,0.18); }

  .card-top {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    flex-wrap: wrap;
  }

  /* ── Badges ── */
  @keyframes live-pulse { 0%,100%{opacity:1} 50%{opacity:0.65} }
  @keyframes live-ring {
    0%   { box-shadow: 0 0 0 0 rgba(229,57,53,0.7); }
    70%  { box-shadow: 0 0 0 7px rgba(229,57,53,0); }
    100% { box-shadow: 0 0 0 0 rgba(229,57,53,0); }
  }
  .badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 9px;
    border-radius: 3px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.08em; text-transform: uppercase;
    white-space: nowrap;
  }
  .badge-live {
    background: #b71c1c; color: #fff;
    animation: live-ring 1.8s ease-out infinite;
  }
  .badge-live::before {
    content: ''; width: 6px; height: 6px;
    background: #ff5252; border-radius: 50%;
    animation: live-pulse 1s ease-in-out infinite;
  }
  .badge-soon     { background: #c84b00; color: #fff; }
  .badge-today    { background: #1a5c9e; color: #fff; }
  .badge-upcoming { background: transparent; color: #4b5563; border: 1px solid #1e1e26; }
  .badge-completed{ background: transparent; color: #1f2937; border: 1px solid #111; }

  /* ── Group pills ── */
  .group-pill {
    display: inline-block; padding: 2px 8px; border-radius: 3px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.7rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase; white-space: nowrap;
  }
  .group-f1      { background: #b71c1c; color: #fff; }
  .group-nascar  { background: #0d47a1; color: #fff; }
  .group-indycar { background: #1b5e20; color: #fff; }
  .group-imsa    { background: #4a148c; color: #fff; }
  .group-default { background: #1f2937; color: #6b7280; }

  /* ── Card body ── */
  .card-series {
    font-size: 0.72rem; font-weight: 500; color: #4b5563;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 3px;
  }
  .card-event {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.3rem; font-weight: 700; color: #f0f0f0;
    text-transform: uppercase; letter-spacing: 0.02em;
    line-height: 1.1; margin-bottom: 3px;
  }
  .card-session {
    font-size: 0.8rem; color: #4b5563; font-weight: 500;
    margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
  }
  .session-icon { font-size: 0.82rem; }

  /* ── Card meta ── */
  .card-meta {
    display: flex; align-items: center; gap: 16px;
    flex-wrap: wrap; font-size: 0.85rem; margin-bottom: 10px;
  }
  .card-time {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1rem; font-weight: 700; letter-spacing: 0.04em;
    color: #00e5ff;            /* cyan = timing board */
    text-transform: uppercase;
  }
  .card-location { color: #374151; font-size: 0.8rem; }

  /* ── Watch row ── */
  .card-watch {
    padding-top: 8px; border-top: 1px solid #1a1a20;
    display: flex; align-items: center; gap: 8px;
  }
  .watch-btn {
    display: inline-flex; align-items: center; gap: 7px;
    background: rgba(245,166,35,0.08);
    border: 1px solid rgba(245,166,35,0.25);
    border-radius: 5px; padding: 5px 14px;
    font-family: 'Barlow', sans-serif;
    font-size: 0.8rem; font-weight: 600; color: #f5a623;
    text-decoration: none; letter-spacing: 0.02em;
    transition: background 0.18s, border-color 0.18s, box-shadow 0.18s;
  }
  .watch-btn:hover {
    background: rgba(245,166,35,0.16);
    border-color: rgba(245,166,35,0.5);
    box-shadow: 0 0 12px rgba(245,166,35,0.12);
    text-decoration: none;
  }
  .watch-none    { color: #1f2937; font-size: 0.8rem; font-style: italic; }
  .source-link a { color: #1f2937; font-size: 0.72rem; text-decoration: none; }
  .source-link a:hover { color: #4b5563; }

  /* ═══════════════════════════════════════════
     EVENT WEEKEND HEADER
  ═══════════════════════════════════════════ */
  .event-weekend-header {
    position: relative;
    margin: 32px 0 8px 0;
    padding: 12px 18px;
    background: #0e0e13;
    border-left: 3px solid #f5a623;
    border-radius: 0 6px 6px 0;
    overflow: hidden;
  }
  .event-weekend-header::after {
    content: '';
    position: absolute; right: 0; top: 0; bottom: 0; width: 120px;
    background-image:
      linear-gradient(45deg, rgba(245,166,35,0.04) 25%, transparent 25%),
      linear-gradient(-45deg, rgba(245,166,35,0.04) 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, rgba(245,166,35,0.04) 75%),
      linear-gradient(-45deg, transparent 75%, rgba(245,166,35,0.04) 75%);
    background-size: 10px 10px;
    background-position: 0 0, 0 5px, 5px -5px, -5px 0;
    -webkit-mask-image: linear-gradient(to right, transparent 0%, black 100%);
    mask-image: linear-gradient(to right, transparent 0%, black 100%);
  }
  .ewh-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.2rem; font-weight: 700; color: #e0e0e0;
    text-transform: uppercase; letter-spacing: 0.04em;
    position: relative; z-index: 1;
  }
  .ewh-meta {
    font-size: 0.7rem; color: #374151; margin-top: 3px;
    text-transform: uppercase; letter-spacing: 0.1em;
    position: relative; z-index: 1;
  }

  /* ═══════════════════════════════════════════
     NEXT-UP LABEL
  ═══════════════════════════════════════════ */
  .next-up-label {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.78rem; font-weight: 700; color: #f5a623;
    text-transform: uppercase; letter-spacing: 0.12em;
    margin: 24px 0 10px 0;
    padding-left: 10px; border-left: 2px solid #f5a623;
  }

  /* ═══════════════════════════════════════════
     EMPTY STATE
  ═══════════════════════════════════════════ */
  .no-sessions {
    text-align: center; color: #1f2937;
    font-family: 'Barlow', sans-serif;
    font-size: 1rem; padding: 64px 24px; line-height: 1.9;
  }
  .no-sessions strong {
    font-family: 'Barlow Condensed', sans-serif;
    color: #374151; display: block;
    font-size: 1.25rem; font-weight: 700;
    letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 8px;
  }

  /* ═══════════════════════════════════════════
     MISC
  ═══════════════════════════════════════════ */
  .refresh-ok   { color: #4ade80; }
  .refresh-fail { color: #f87171; }
  .refresh-warn { color: #fb923c; }
  .last-refreshed { font-size: 0.72rem; color: #374151; letter-spacing: 0.04em; }
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
    _refreshed_line = ("Last refreshed " + last_refreshed) if last_refreshed else "Never refreshed — click Refresh below"
    st.markdown(f"""
    <div class="hero">
      <div class="hero-inner">
        <div class="hero-flag">🏁</div>
        <div class="hero-text">
          <div class="hero-title">MOTORSPORTS <span class="accent">DASHBOARD</span></div>
          <div class="hero-sub">2026 Season &nbsp;·&nbsp; All times Eastern &nbsp;·&nbsp; {_refreshed_line}</div>
        </div>
        <div class="hero-date">
          <span class="day-label">{_now.strftime("%A")}</span>
          <span class="date-val">{_now.strftime("%b %d").replace(" 0", " ")}</span>
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
