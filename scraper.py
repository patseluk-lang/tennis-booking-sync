"""
Reads reservations from the sports complex site.
Uses plain HTTP requests (requests) - the page is static, no JS needed.
"""
import requests
from bs4 import BeautifulSoup

BASE = "http://127.0.0.1:5000"


class ScrapeError(Exception):
    """Any problem reading the site. The point is to NEVER return an empty list instead."""


def fetch_reservations(username: str, password: str) -> list[dict]:
    session = requests.Session()

    # Any network failure (site down, timeout, DNS) must also become a ScrapeError,
    # otherwise it escapes upwards as a traceback and bypasses our safeguard.
    try:
        # 1. Log in
        resp = session.post(
            f"{BASE}/login",
            data={"username": username, "password": password},
            timeout=10,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            raise ScrapeError(f"Login request failed: HTTP {resp.status_code}")
        if "Invalid credentials" in resp.text:
            raise ScrapeError("Login failed: invalid credentials")

        # 2. Reservations page
        resp = session.get(f"{BASE}/reservations", timeout=10)
        if resp.status_code != 200:
            raise ScrapeError(f"Reservations page failed: HTTP {resp.status_code}")
    except requests.RequestException as exc:
        raise ScrapeError(f"Network error: {exc}") from exc

    soup = BeautifulSoup(resp.text, "html.parser")

    # 3. INTEGRITY CHECK.
    #    A missing table is not "zero reservations" - it is a broken page.
    #    An empty table (with <thead> but no rows) really is zero reservations.
    table = soup.find("table", id="reservations")
    if table is None:
        raise ScrapeError("Reservations table not found - page structure changed or not logged in")

    rows = table.find("tbody").find_all("tr")

    reservations = []
    for row in rows:
        reservations.append({
            "date": row.find("td", class_="date").get_text(strip=True),
            "start": row.find("td", class_="start").get_text(strip=True),
            "end": row.find("td", class_="end").get_text(strip=True),
            "court": row.find("td", class_="court").get_text(strip=True),
            "location": row.find("td", class_="location").get_text(strip=True),
        })
    return reservations


if __name__ == "__main__":
    for r in fetch_reservations("player", "tennis123"):
        print(r)
