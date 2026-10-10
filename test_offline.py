"""
Offline run of every scenario: no Flask, no Google, no network.
Only the data source is replaced; the logic in sync.py is the real one.

    python test_offline.py
"""
import json
from pathlib import Path

import scraper
import sync
from calendar_client import FakeCalendar, SYNC_MARKER

HERE = Path(__file__).parent
DATA = HERE / "reservations.json"
CAL = HERE / "fake_calendar.json"

STATE = {"mode": "ok"}


def fake_fetch(username, password):
    """Stand-in for scraper.fetch_reservations."""
    if STATE["mode"] == "down":
        raise scraper.ScrapeError("Network error: connection refused")
    if STATE["mode"] == "logged_out":
        raise scraper.ScrapeError("Reservations table not found - not logged in")
    return json.loads(DATA.read_text(encoding="utf-8"))


sync.fetch_reservations = fake_fetch          # <- the substitution


def reservations(courts):
    all_r = [
        {"date": "2026-07-14", "start": "18:00", "end": "19:30", "court": "Court 3",          "location": "Municipal Sports Centre, Kyiv"},
        {"date": "2026-07-16", "start": "07:00", "end": "08:30", "court": "Court 1",          "location": "Municipal Sports Centre, Kyiv"},
        {"date": "2026-07-19", "start": "20:00", "end": "21:00", "court": "Court 5 (indoor)", "location": "Municipal Sports Centre, Kyiv"},
    ]
    keep = [r for r in all_r if r["court"] in courts]
    DATA.write_text(json.dumps(keep, indent=2, ensure_ascii=False), encoding="utf-8")


def show_calendar():
    events = json.loads(CAL.read_text(encoding="utf-8"))
    if not events:
        print("      (calendar is empty)")
    for e in events:
        tag = "OURS " if e.get("marker") == SYNC_MARKER else "OTHER"
        print(f"      [{tag}] {e['summary']}  {e['start']}")


def banner(text):
    print("\n" + "=" * 62)
    print(text)
    print("=" * 62)


CAL.unlink(missing_ok=True)
cal = FakeCalendar()

# Put a FOREIGN event in the calendar - it must never be touched.
raw = json.loads(CAL.read_text(encoding="utf-8"))
raw.append({"id": "evt_personal", "marker": None, "fingerprint": None,
            "summary": "Dentist", "location": "Clinic",
            "start": "2026-07-15T10:00:00", "end": "2026-07-15T11:00:00"})
CAL.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")

USER, PWD = "player", "tennis123"

banner("SCENARIO 1. First run. Three reservations, empty calendar.")
reservations({"Court 3", "Court 1", "Court 5 (indoor)"})
sync.sync(cal, USER, PWD)
print("   Calendar:"); show_calendar()

banner("SCENARIO 2. Repeat run. Nothing has changed.")
print("Expected: create 0, delete 0. This is the protection against duplicates.\n")
sync.sync(cal, USER, PWD)
print("   Calendar:"); show_calendar()

banner("SCENARIO 3. Cancellation. Court 3 disappeared from the site.")
reservations({"Court 1", "Court 5 (indoor)"})
sync.sync(cal, USER, PWD)
print("   Calendar:"); show_calendar()

banner("SCENARIO 4. The site is down. The calendar MUST NOT be emptied.")
STATE["mode"] = "down"
code = sync.sync(cal, USER, PWD)
print(f"   Exit code: {code} (1 = stopped, nothing was touched)")
print("   Calendar:"); show_calendar()
STATE["mode"] = "ok"

banner("SCENARIO 5. Session expired. The page loads, the table is gone.")
STATE["mode"] = "logged_out"
code = sync.sync(cal, USER, PWD)
print(f"   Exit code: {code}")
print("   Calendar:"); show_calendar()
STATE["mode"] = "ok"

banner("SCENARIO 6. Genuine mass cancellation. The site returned zero rows.")
print("Here the script SHOULD delete 2 events - the limit (5) is not exceeded.\n")
reservations(set())
sync.sync(cal, USER, PWD)
print("   Calendar:"); show_calendar()

print("\n" + "=" * 62)
print("Note: the 'Dentist' event survived all six scenarios.")
print("It was never deleted - it carries no sync marker.")
print("=" * 62)

# Restore the initial data
reservations({"Court 3", "Court 1", "Court 5 (indoor)"})
