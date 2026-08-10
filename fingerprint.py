"""
Deterministic fingerprint of a reservation.

The idea: the same reservation MUST produce the same string every time.
So only stable fields are used: date + start time + court.

Location is deliberately excluded - the site may rewrite it
("Kyiv" -> "Kyiv, UA") and the fingerprint would change
even though the reservation did not.
"""
import hashlib


def fingerprint(reservation: dict) -> str:
    raw = f"{reservation['date']}|{reservation['start']}|{reservation['court']}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[:32]          # 32 characters is more than enough


if __name__ == "__main__":
    a = {"date": "2026-07-14", "start": "18:00", "court": "Court 3", "location": "Kyiv"}
    b = {"date": "2026-07-14", "start": "18:00", "court": "Court 3", "location": "Kyiv, UA"}
    c = {"date": "2026-07-14", "start": "19:00", "court": "Court 3", "location": "Kyiv"}

    print("a:", fingerprint(a))
    print("b:", fingerprint(b), "-> same, because location is not part of the fingerprint")
    print("c:", fingerprint(c), "-> different, because the start time changed")
    assert fingerprint(a) == fingerprint(b)
    assert fingerprint(a) != fingerprint(c)
    print("\nOK")
