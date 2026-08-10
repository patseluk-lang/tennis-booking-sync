# Booking Scraper -> Google Calendar Sync

A scraper that logs into a sports-centre booking site, reads the reservations table, and mirrors it into Google Calendar. Runs unattended on a schedule and stays idempotent: repeated runs create no duplicates.

The point of this project is not the scraping. It is what happens when the source misbehaves.

## Files

| File | Purpose |
|------|---------|
| `fake_site.py` | Mock booking site (Flask): login + reservations page. Lets the whole pipeline run offline |
| `reservations.json` | The mock site's data. Edit it by hand to simulate cancellations |
| `scraper.py` | Logs in, parses the reservations table |
| `fingerprint.py` | Deterministic fingerprint of a reservation |
| `calendar_client.py` | Two clients: `FakeCalendar` (JSON file) and `GoogleCalendar` (real API) |
| `sync.py` | The synchroniser |
| `test_offline.py` | Runs six scenarios with no network and no Google account |

## Install

```bash
pip install flask requests beautifulsoup4
```

## Step 1. Run the logic with nothing attached

```bash
python test_offline.py
```

Six scenarios, including site failure and session loss. No network, no Google account required.

## Step 2. Run against the mock site

**Terminal 1:**

```bash
python fake_site.py
```

Open http://127.0.0.1:5000 with credentials `player` / `tennis123`.

**Terminal 2:**

```bash
python sync.py              # first run: creates 3 events
python sync.py              # second run: creates 0, no duplicates
python sync.py --dry-run    # show the plan, change nothing
```

Now open `reservations.json`, delete one reservation and save.

```bash
python sync.py              # deletes the matching event
```

Check `fake_calendar.json` to see what happened.

### Break the site on purpose

Set `BROKEN = True` in `fake_site.py`, restart it, run `sync.py`.
The script prints `[ABORT]` and leaves the calendar untouched.

## Step 3. Real Google Calendar

1. https://console.cloud.google.com, create a new project
2. APIs & Services -> Library -> enable **Google Calendar API**
3. APIs & Services -> Credentials -> Create Credentials -> **OAuth client ID** -> type **Desktop app**
4. Download the JSON and place it next to the scripts as `credentials.json`
5. In Google Calendar create a **separate test calendar** and copy its Calendar ID from its settings
6. Then:

```bash
pip install google-api-python-client google-auth-oauthlib
python sync.py --real --calendar-id YOUR_CALENDAR_ID
```

The first run opens a browser for consent and writes `token.json`. After that it runs unattended.

> **Do not point this at your primary calendar.** The script deletes events. It only deletes its own, but practising on a live calendar is a bad habit.

## Step 4. Schedule it

**Linux/macOS**, via `crontab -e`:

```
*/15 * * * * cd /path/to/tennis-sync && /usr/bin/python3 sync.py --real --calendar-id YOUR_ID >> sync.log 2>&1
```

**Windows**: Task Scheduler, trigger every 15 minutes. See `run_sync.bat.example`.

## Credentials

No passwords in the code. The script reads them from the environment:

```bash
export TENNIS_USER=player
export TENNIS_PASS=tennis123
```

For production use `.env` with `python-dotenv`, or the OS keyring (`keyring`).
`credentials.json` and `token.json` must never be committed.

## Design notes: what actually matters here

1. **The fingerprint** is built from stable fields only: date + start time + court. `location` is deliberately excluded, because a site can rewrite it (`Kyiv` becomes `Kyiv, UA`) and the fingerprint would change while the reservation did not. The script keeps no memory between runs. It recomputes everything each time, and identical input yields identical fingerprints.

2. **The `tennis-sync-v1` marker** in `extendedProperties.private` is what makes an event "ours". The Google query filters on it, so the script never even sees unrelated events. It cannot delete what it cannot see.

3. **An empty list is not a valid result.** This is the dangerous failure in this task: the site goes down, the script reads zero reservations, and the calendar gets wiped. So any read problem raises `ScrapeError` instead of returning `[]`. HTTP 200 is not sufficient evidence of success. The structure is checked too.

4. **The deletion cap** (`MAX_DELETIONS`) is the last line of defence for the case where the site returns a technically valid but empty page. Beyond the cap the run aborts and changes nothing.
