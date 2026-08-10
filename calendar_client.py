"""
Calendar client.

Two implementations with an IDENTICAL interface:
  - FakeCalendar   - writes to fake_calendar.json. Works offline, no Google account needed.
  - GoogleCalendar - the real Google Calendar API.

Both do exactly three things:
  list_synced_events() -> {fingerprint: event_id}
  create_event(reservation, fingerprint)
  delete_event(event_id)

SYNC_MARKER is what separates "our" events from everything else.
No event without this marker is ever deleted.
"""
import json
from pathlib import Path

SYNC_MARKER = "tennis-sync-v1"


# ─────────────────────────────────────────────────────────────
#  FAKE CALENDAR - for offline development and testing
# ─────────────────────────────────────────────────────────────
class FakeCalendar:
    def __init__(self, path="fake_calendar.json"):
        self.path = Path(__file__).parent / path
        if not self.path.exists():
            self._write([])

    def _read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, events):
        self.path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")

    def list_synced_events(self) -> dict:
        return {
            e["fingerprint"]: e["id"]
            for e in self._read()
            if e.get("marker") == SYNC_MARKER      # foreign events never enter the selection
        }

    def create_event(self, reservation, fp):
        events = self._read()
        events.append({
            "id": f"evt_{fp[:8]}",
            "marker": SYNC_MARKER,
            "fingerprint": fp,
            "summary": f"Tennis - {reservation['court']}",
            "location": reservation["location"],
            "start": f"{reservation['date']}T{reservation['start']}:00",
            "end": f"{reservation['date']}T{reservation['end']}:00",
        })
        self._write(events)

    def delete_event(self, event_id):
        events = [e for e in self._read() if e["id"] != event_id]
        self._write(events)


# ─────────────────────────────────────────────────────────────
#  REAL GOOGLE CALENDAR
# ─────────────────────────────────────────────────────────────
class GoogleCalendar:
    """
    Requires:  pip install google-api-python-client google-auth-oauthlib
    And a credentials.json from Google Cloud Console (OAuth, "Desktop app" type).

    calendar_id: better to create a SEPARATE test calendar and take its ID
                 from the settings, rather than writing to "primary".
    """
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    TIMEZONE = "Europe/Kyiv"

    def __init__(self, calendar_id):
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        self.calendar_id = calendar_id
        here = Path(__file__).parent
        token_path = here / "token.json"

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(here / "credentials.json"), self.SCOPES)
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json())

        self.service = build("calendar", "v3", credentials=creds)

    def list_synced_events(self) -> dict:
        result = {}
        page_token = None
        while True:
            resp = self.service.events().list(
                calendarId=self.calendar_id,
                # THIS is the filter: Google returns only our own events.
                privateExtendedProperty=f"marker={SYNC_MARKER}",
                singleEvents=True,
                pageToken=page_token,
            ).execute()
            for e in resp.get("items", []):
                fp = e["extendedProperties"]["private"]["fingerprint"]
                result[fp] = e["id"]
            page_token = resp.get("nextPageToken")
            if not page_token:
                return result

    def create_event(self, reservation, fp):
        body = {
            "summary": f"Tennis - {reservation['court']}",
            "location": reservation["location"],
            "start": {"dateTime": f"{reservation['date']}T{reservation['start']}:00", "timeZone": self.TIMEZONE},
            "end":   {"dateTime": f"{reservation['date']}T{reservation['end']}:00",   "timeZone": self.TIMEZONE},
            "extendedProperties": {"private": {"marker": SYNC_MARKER, "fingerprint": fp}},
        }
        self.service.events().insert(calendarId=self.calendar_id, body=body).execute()

    def delete_event(self, event_id):
        self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
