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
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }

  /* ── Card — left accent border per series ── */
  .session-card {
    background: linear-gradient(135deg, #141428 0%, #1a1a35 100%);
    border: 1px solid #252545;
    border-left: 4px solid var(--accent, #3949ab);
    border-radius: 0 14px 14px 0;
    padding: 14px 18px 12px 18px;
    margin-bottom: 10px;
    color: #e0e0f0;
    transition: border-color 0.2s, transform 0.1s, box-shadow 0.2s;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }
  .session-card:hover {
    border-color: var(--accent, #3949ab);
    transform: translateX(2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.5);
  }

  /* Per-series accent colours */
  .card-f1      { --accent: #e53935; }
  .card-nascar  { --accent: #1565c0; }
  .card-indycar { --accent: #2e7d32; }
  .card-imsa    { --accent: #6a1b9a; }

  /* ── Top row ── */
  .card-top {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 7px;
    flex-wrap: wrap;
  }

  /* ── Live badge + pulse animation ── */
  @keyframes pulse-ring {
    0%   { box-shadow: 0 0 0 0 rgba(211,47,47,0.6); }
    70%  { box-shadow: 0 0 0 7px rgba(211,47,47,0); }
    100% { box-shadow: 0 0 0 0 rgba(211,47,47,0); }
  }
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    white-space: nowrap;
  }
  .badge-live {
    background: #c62828;
    color: #fff;
    animation: pulse-ring 1.6s ease-out infinite;
  }
  .badge-live::before {
    content: '';
    display: inline-block;
    width: 7px; height: 7px;
    background: #ff5252;
    border-radius: 50%;
  }
  .badge-soon      { background: #bf360c; color: #fff; }
  .badge-today     { background: #0d47a1; color: #fff; }
  .badge-upcoming  { background: #1a1a2e; color: #607d8b; border: 1px solid #2a2a4a; }
  .badge-completed { background: #111; color: #37474f; }

  /* ── Group pills ── */
  .group-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .group-f1      { background: #b71c1c; color: #fff; }
  .group-nascar  { background: #0d47a1; color: #fff; }
  .group-indycar { background: #1b5e20; color: #fff; }
  .group-imsa    { background: #4a148c; color: #fff; }
  .group-default { background: #37474f; color: #fff; }

  /* ── Card body ── */
  .card-series  { font-size: 0.8rem; color: #90a4ae; font-weight: 500; margin-bottom: 2px; }
  .card-event   { font-size: 1.05rem; font-weight: 700; color: #eceff1; margin-bottom: 2px; letter-spacing: -0.01em; }
  .card-session {
    font-size: 0.82rem;
    color: #607d8b;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .session-icon { font-size: 0.85rem; }

  /* ── Card meta row ── */
  .card-meta {
    display: flex;
    align-items: center;
    gap: 18px;
    flex-wrap: wrap;
    font-size: 0.86rem;
    margin-bottom: 10px;
  }
  .card-time     { color: #26c6da; font-weight: 700; letter-spacing: 0.01em; }
  .card-location { color: #546e7a; }

  /* ── Watch button ── */
  .card-watch {
    padding-top: 8px;
    border-top: 1px solid #1e1e3a;
  }
  .watch-btn {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: rgba(38,198,218,0.1);
    border: 1px solid rgba(38,198,218,0.25);
    border-radius: 8px;
    padding: 5px 14px;
    font-size: 0.82rem;
    font-weight: 600;
    color: #26c6da;
    text-decoration: none;
    transition: background 0.15s, border-color 0.15s;
  }
  .watch-btn:hover {
    background: rgba(38,198,218,0.2);
    border-color: rgba(38,198,218,0.5);
    text-decoration: none;
  }
  .watch-none    { color: #37474f; font-size: 0.82rem; font-style: italic; }
  .source-link a { color: #37474f; font-size: 0.75rem; text-decoration: none; margin-left: 10px; }
  .source-link a:hover { color: #546e7a; }

  /* ── Event weekend header ── */
  .event-weekend-header {
    margin: 36px 0 10px 0;
    padding: 12px 16px;
    background: linear-gradient(90deg, #0d0d1f 0%, #111130 100%);
    border-left: 3px solid #3949ab;
    border-radius: 0 10px 10px 0;
    box-shadow: inset 0 0 40px rgba(57,73,171,0.05);
  }
  .ewh-name { font-size: 1rem; font-weight: 700; color: #c5cae9; letter-spacing: -0.01em; }
  .ewh-meta { font-size: 0.78rem; color: #3d4a6b; margin-top: 3px; text-transform: uppercase; letter-spacing: 0.06em; }

  /* ── Next-up label ── */
  .next-up-label {
    font-size: 0.75rem;
    font-weight: 700;
    color: #3949ab;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 28px 0 10px 0;
    padding-left: 10px;
    border-left: 2px solid #3949ab;
  }

  /* ── Empty state ── */
  .no-sessions {
    text-align: center;
    color: #37474f;
    font-size: 1rem;
    padding: 64px 24px;
    line-height: 1.8;
  }
  .no-sessions strong { color: #546e7a; display: block; font-size: 1.2rem; margin-bottom: 8px; font-weight: 700; }

  /* ── Misc ── */
  .refresh-ok   { color: #66bb6a; }
  .refresh-fail { color: #ef5350; }
  .refresh-warn { color: #ffa726; }
  .last-refreshed { font-size: 0.76rem; color: #37474f; }
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

    # Header
    st.markdown("# 🏁 Motorsports Dashboard")

    meta = load_metadata()
    last_refreshed = meta.get("last_refreshed", None)

    col_refresh, col_meta = st.columns([1, 4])
    with col_refresh:
        do_refresh = st.button("🔄 Refresh All Schedules", use_container_width=True)
    with col_meta:
        if last_refreshed:
            st.markdown(f'<div class="last-refreshed">Last refreshed: {last_refreshed}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="last-refreshed">Never refreshed — click Refresh All Schedules to load data.</div>', unsafe_allow_html=True)

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
