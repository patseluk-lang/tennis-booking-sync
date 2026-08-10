"""
Reservation synchroniser.

Run against the local fake calendar (training mode):
    python sync.py

Run against a real Google Calendar:
    python sync.py --real --calendar-id YOUR_CALENDAR_ID

The logic is three lines in essence:
    to_create = site - calendar
    to_delete = calendar - site
    the rest  = leave alone
"""
import argparse
import os
import sys

from scraper import fetch_reservations, ScrapeError
from fingerprint import fingerprint
from calendar_client import FakeCalendar, GoogleCalendar

# Safety valve: if a single run wants to delete more than this, stop and ask a human.
MAX_DELETIONS = 5


def sync(calendar, username, password, dry_run=False):
    # 1. Read the site. If that fails, exit WITHOUT deleting anything.
    try:
        reservations = fetch_reservations(username, password)
    except ScrapeError as exc:
        print(f"[ABORT] Could not read the site: {exc}")
        print("[ABORT] Calendar left untouched - this is deliberate, not a failure.")
        return 1

    print(f"[OK] Site returned {len(reservations)} reservations")

    # 2. Two sets of fingerprints
    site = {fingerprint(r): r for r in reservations}
    cal = calendar.list_synced_events()            # {fingerprint: event_id}
    print(f"[OK] Calendar holds {len(cal)} events owned by this sync")

    to_create = site.keys() - cal.keys()
    to_delete = cal.keys() - site.keys()
    unchanged = site.keys() & cal.keys()

    print(f"     create: {len(to_create)}   delete: {len(to_delete)}   unchanged: {len(unchanged)}")

    # 3. Safety valve against mass deletion
    if len(to_delete) > MAX_DELETIONS:
        print(f"[ABORT] Attempted to delete {len(to_delete)} events (limit {MAX_DELETIONS}).")
        print("[ABORT] This looks like a source failure, not real cancellations. Check manually.")
        return 1

    if dry_run:
        print("[DRY-RUN] Nothing was changed.")
        return 0

    for fp in to_create:
        calendar.create_event(site[fp], fp)
        print(f"  + created: {site[fp]['date']} {site[fp]['start']} {site[fp]['court']}")

    for fp in to_delete:
        calendar.delete_event(cal[fp])
        print(f"  - deleted event with fingerprint {fp[:8]}... (reservation gone from site)")

    print("[DONE]")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--real", action="store_true", help="use the real Google Calendar")
    p.add_argument("--calendar-id", default="primary")
    p.add_argument("--dry-run", action="store_true", help="show the plan, change nothing")
    args = p.parse_args()

    user = os.environ.get("TENNIS_USER", "player")
    pwd = os.environ.get("TENNIS_PASS", "tennis123")

    cal = GoogleCalendar(args.calendar_id) if args.real else FakeCalendar()
    sys.exit(sync(cal, user, pwd, dry_run=args.dry_run))
