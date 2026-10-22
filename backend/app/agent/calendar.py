"""In-memory and SQLite-backed calendars sharing one booking shape."""

from __future__ import annotations

import re
import threading
from datetime import datetime, timedelta
from typing import Protocol
from uuid import uuid4


class SlotTaken(Exception):
    """The requested window overlaps a booking that is already committed."""

    def __init__(self, start: str) -> None:
        super().__init__(start)
        self.start = start


def new_booking_id() -> str:
    return "bk_" + uuid4().hex[:10]


def _digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _name_matches(candidate: str, query: str) -> bool:
    """Full-name match only. A single first name is not enough to act on a booking."""
    left = candidate.casefold().split()
    right = [token for token in query.casefold().split() if token]
    if len(right) < 2 or not left:
        return False
    if candidate.casefold() == query.casefold():
        return True
    return all(token in left for token in right)


class Calendar(Protocol):
    def busy(self) -> list[tuple[datetime, datetime]]: ...

    def find(self, name: str | None, phone: str | None) -> dict | None: ...

    def match_visit(self, last4: str, day: str) -> list[dict]: ...

    def bookings_with_last4(self, last4: str) -> list[dict]: ...

    def verify_status(self, booking_id: str, now: datetime) -> dict: ...

    def record_verify_failure(self, booking_id: str, phone: str, now: datetime) -> dict: ...

    def book(self, draft: dict) -> dict: ...

    def cancel(self, booking_id: str) -> dict: ...

    def reschedule(self, booking_id: str, start: datetime, end: datetime) -> dict: ...


class MemoryCalendar:
    def __init__(self) -> None:
        self.bookings: list[dict] = []
        self.locks: dict[str, dict] = {}
        self._lock = threading.Lock()

    def busy(self) -> list[tuple[datetime, datetime]]:
        spans = []
        for booking in self.bookings:
            if booking.get("status") != "booked":
                continue
            spans.append((datetime.fromisoformat(booking["start"]), datetime.fromisoformat(booking["end"])))
        return spans

    def find(self, name: str | None, phone: str | None) -> dict | None:
        active = [booking for booking in self.bookings if booking.get("status") == "booked"]
        if phone:
            target = _digits(phone)[-10:]
            for booking in active:
                if _digits(booking.get("phone"))[-10:] == target:
                    return booking
        if name:
            matches = [booking for booking in active if _name_matches(booking.get("name") or "", name)]
            if len(matches) == 1:
                return matches[0]
        return None

    def match_visit(self, last4: str, day: str) -> list[dict]:
        found = []
        for booking in self.bookings:
            if booking.get("status") != "booked":
                continue
            phone = _digits(booking.get("phone"))
            if len(phone) < 4 or phone[-4:] != last4:
                continue
            if datetime.fromisoformat(booking["start"]).date().isoformat() != day:
                continue
            found.append(booking)
        return found

    def bookings_with_last4(self, last4: str) -> list[dict]:
        found = []
        for booking in self.bookings:
            if booking.get("status") != "booked":
                continue
            phone = _digits(booking.get("phone"))
            if len(phone) >= 4 and phone[-4:] == str(last4):
                found.append(booking)
        return found

    def verify_status(self, booking_id: str, now: datetime) -> dict:
        row = self.locks.get(booking_id) or {}
        failures = int(row.get("failures") or 0)
        locked = datetime.fromisoformat(row["locked_until"]) if row.get("locked_until") else None
        active = bool(locked and now < locked)
        return {
            "failures": failures,
            "locked_until": locked,
            "hard_lock": active and failures >= 3,
            "delayed": active and failures == 2,
        }

    def record_verify_failure(self, booking_id: str, phone: str, now: datetime) -> dict:
        with self._lock:
            row = self.locks.get(booking_id) or {"failures": 0, "locked_until": None}
            failures = int(row.get("failures") or 0) + 1
            locked_until = None
            if failures == 2:
                locked_until = (now + timedelta(minutes=10)).isoformat()
            elif failures >= 3:
                locked_until = (now + timedelta(hours=24)).isoformat()
            self.locks[booking_id] = {"phone": phone, "failures": failures, "locked_until": locked_until}
        return {"failures": failures, "alert": failures >= 3, "phone": phone}

    def book(self, draft: dict) -> dict:
        with self._lock:
            start = datetime.fromisoformat(draft["start"])
            end = datetime.fromisoformat(draft["end"])
            existing = self._for_call(draft.get("call_id"))
            if existing and draft.get("call_id"):
                return existing
            if self._overlaps(start, end, ignore_id=None):
                raise SlotTaken(draft["start"])
            record = {
                "id": draft.get("id") or new_booking_id(),
                "call_id": draft.get("call_id"),
                "name": draft.get("name"),
                "phone": draft.get("phone"),
                "address": draft.get("address"),
                "issue": draft.get("issue"),
                "start": draft["start"],
                "end": draft["end"],
                "status": "booked",
            }
            self.bookings.append(record)
            return record

    def cancel(self, booking_id: str) -> dict:
        with self._lock:
            for booking in self.bookings:
                if booking["id"] == booking_id:
                    booking["status"] = "cancelled"
                    return booking
        raise KeyError(booking_id)

    def reschedule(self, booking_id: str, start: datetime, end: datetime) -> dict:
        with self._lock:
            if self._overlaps(start, end, ignore_id=booking_id):
                raise SlotTaken(start.isoformat())
            for booking in self.bookings:
                if booking["id"] == booking_id:
                    booking["start"] = start.isoformat()
                    booking["end"] = end.isoformat()
                    booking["status"] = "booked"
                    return booking
        raise KeyError(booking_id)

    def _for_call(self, call_id: str | None) -> dict | None:
        if not call_id:
            return None
        for booking in self.bookings:
            if booking.get("call_id") == call_id and booking.get("status") == "booked":
                return booking
        return None

    def _overlaps(self, start: datetime, end: datetime, ignore_id: str | None) -> bool:
        for booking in self.bookings:
            if booking.get("status") != "booked" or booking.get("id") == ignore_id:
                continue
            busy_start = datetime.fromisoformat(booking["start"])
            busy_end = datetime.fromisoformat(booking["end"])
            if start < busy_end and end > busy_start:
                return True
        return False
