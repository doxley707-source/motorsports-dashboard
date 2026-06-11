# Motorsports Dashboard

A personal motorsports schedule dashboard that runs in your web browser.
Quickly see what racing is on today, this weekend, and across the rest of the season.

---

## What It Does

- **Today** — Default landing view. Shows every racing session happening today in Eastern Time. When nothing is on, shows the next upcoming sessions automatically.
- **This Weekend** — Thursday through Sunday of the current week, grouped by event weekend.
- **Look Ahead** — All upcoming sessions for the full season, grouped by event weekend.
- **Data Issues** — Data quality warnings and last refresh summary.

Each session card shows:
- Series group and specific series name
- Event name, session name, and session type
- Start time in Eastern Time (or date-only for IMSA events)
- Track and location
- Live / Upcoming / Completed status
- Where to watch — platform name and link when available

---

## Series Coverage

| Series Group | Series | Sessions | Auto-Import |
|---|---|---|---|
| Formula 1 | Formula 1 | Practice, Qualifying, Sprint, Race | ✔ Full (Jolpica API + ESPN) |
| Formula 1 | Porsche Mobil 1 Supercup | Race | ✔ Dates (Wikipedia) |
| NASCAR | NASCAR Cup Series | Race | ✔ Full (ESPN) |
| IndyCar | NTT IndyCar Series | Race | ✔ Full (ESPN) |
| IMSA | WeatherTech SportsCar Championship | Race | ✔ Dates (Wikipedia) + race times (broadcast schedule) |
| IMSA | Michelin Pilot Challenge | Race | ✔ Dates (Wikipedia) |
| IMSA | Porsche Carrera Cup North America | Race | ✔ Dates (Wikipedia) |
| IMSA | Mazda MX-5 Cup | Race | ✔ Dates (Wikipedia) |
| IMSA | Lamborghini Super Trofeo North America | Race | ✔ Dates (Wikipedia) |

**Notes:**
- F1 and NASCAR/IndyCar races include broadcast info (Apple TV+, FOX, NBC, Prime Video, etc.)
- IMSA WeatherTech races show real start times, merged from the season's NBC/IMSA broadcast schedule (`config/imsa_race_times.json`). IMSA support series (Pilot Challenge, Carrera Cup, MX-5, Super Trofeo) remain date-only — their times aren't published in machine-readable form
- NASCAR and IndyCar show race events only — practice/qualifying times are not available from free sources
- All data uses official or reliable third-party sources. No paid APIs or API keys required.

---

## Setup (Do This Once)

You need Python installed. If you ran setup already, skip to **How to Run**.

1. Open a Command Prompt (search "Command Prompt" in the Start menu)
2. Navigate to this folder:
   ```
   cd C:\Users\doxle\Documents\motorsports-dashboard
   ```
3. Install required packages:
   ```
   pip install -r requirements.txt
   ```
4. Done. You only need to do this once.

---

## How to Run

**Option A — Double-click launcher (easiest):**
Double-click `Open_Motorsports_Dashboard.bat` in this folder.
A black command window opens and your browser should open automatically.
Keep that black window open — closing it stops the app.

**Option B — From the terminal:**
```
cd C:\Users\doxle\Documents\motorsports-dashboard
streamlit run app.py
```
Then open your browser to: http://localhost:8501

---

## How to Refresh Schedules

1. Open the dashboard in your browser
2. Click **Refresh All Schedules** at the top
3. A summary shows which series refreshed successfully

The refresh pulls from:
- **F1**: Jolpica community API (same format as the retired Ergast API) + ESPN for broadcast info
- **NASCAR**: ESPN Racing API
- **IndyCar**: ESPN Racing API
- **IMSA + support series**: Wikipedia season pages
- **Porsche Supercup**: Wikipedia season page

If one source fails, the app keeps your previously saved data for that series.

---

## What to Do If a Refresh Fails

The app retains your saved data when a source fails — nothing is deleted.
Check the **Data Issues** tab for the specific error message.

Common reasons:
- No internet connection
- Source website temporarily unavailable
- Wikipedia page structure changed (IMSA/Supercup)

---

## Where the Schedule Data Lives

All data is saved to:
```
data/events.csv
```

This is a plain spreadsheet you can open in Excel or Google Sheets.
You can view, add, or edit sessions directly.

App metadata (last refresh time, refresh results) is saved to:
```
data/metadata.json
```

---

## How Backups Work

Every time you click **Refresh All Schedules**, the app backs up your current
`data/events.csv` before making changes:
```
data/backups/events_YYYYMMDD_HHMMSS.csv
```

To restore a backup: copy the backup file to `data/events.csv` (rename it).

---

## How to Manually Add Sessions

Open `data/events.csv` in Excel or Google Sheets and add a row. Key columns:

| Column | Example |
|---|---|
| `series_group` | `Formula 1` |
| `series` | `Porsche Mobil 1 Supercup` |
| `event_name` | `Monaco Grand Prix` |
| `session_name` | `Race` |
| `session_type` | `Race` *(Practice, Qualifying, Sprint Qualifying, Sprint, Warmup, Race)* |
| `start_datetime` | `2026-06-07T13:00:00+00:00` *(UTC ISO format)* |
| `track` | `Circuit de Monaco` |
| `location` | `Monte Carlo, Monaco` |
| `watch_platform` | `Apple TV+` |
| `watch_url` | `https://tv.apple.com` |
| `is_televised_or_streamed` | `Yes` |

Save the file and refresh your browser to see the change.

---

## Troubleshooting

**The dashboard won't open:**
- Make sure the black command window is still open
- Try going directly to http://localhost:8501 in your browser
- Make sure you ran `pip install -r requirements.txt` first

**Refresh fails for all series:**
- Check your internet connection
- Look at the Data Issues tab for specific error messages

**Times look wrong:**
- All times are converted to Eastern Time automatically
- Make sure `start_datetime` in your CSV includes timezone info (e.g. `+00:00` or `Z` at the end)

**IMSA events show "Date only — time TBA":**
- WeatherTech races should show real start times after a refresh. If one doesn't, the event may have been rescheduled — update its entry in `config/imsa_race_times.json`
- Support series (Pilot Challenge, Carrera Cup, MX-5, Super Trofeo) are expected to be date-only
- For a new season, update `config/imsa_race_times.json` with the new broadcast schedule (the file's `season` must match the current year, otherwise it's ignored)

**The CSV is missing:**
- Click Refresh All Schedules to create it automatically
- Or create `data/events.csv` manually with the column headers listed above

---

## Future Deployment

This app is built with Streamlit and can be deployed to the web easily:
- **Streamlit Community Cloud** (free) — connect your GitHub repo and deploy in minutes
- **Railway / Render / Heroku** — simple paid hosting options

For a hosted version, consider moving from CSV storage to a lightweight database,
and adding a scheduled refresh (e.g. daily cron job) instead of a manual button.
