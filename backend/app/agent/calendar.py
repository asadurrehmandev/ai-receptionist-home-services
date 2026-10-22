"""In-memory and SQLite-backed calendars sharing one booking shape."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Protocol
from uuid import uuid4


def new_booking_id() -> str:
    return "bk_" + uuid4().hex[:10]


def _digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _name_matches(candidate: str, query: str) -> bool:
    left = candidate.casefold().split()
    right = query.casefold().split()
    if not right:
        return False
    if candidate.casefold() == query.casefold():
        return True
    if len(right) == 1:
        return right[0] in left
    return all(token in left for token in right)


class Calendar(Protocol):
    def busy(self) -> list[tuple[datetime, datetime]]: ...

    def find(self, name: str | None, phone: str | None) -> dict | None: ...

    def book(self, draft: dict) -> dict: ...

    def cancel(self, booking_id: str) -> dict: ...

    def reschedule(self, booking_id: str, start: datetime, end: datetime) -> dict: ...


class MemoryCalendar:
    def __init__(self) -> None:
        self.bookings: list[dict] = []

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

    def book(self, draft: dict) -> dict:
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
        for booking in self.bookings:
            if booking["id"] == booking_id:
                booking["status"] = "cancelled"
                return booking
        raise KeyError(booking_id)

    def reschedule(self, booking_id: str, start: datetime, end: datetime) -> dict:
        for booking in self.bookings:
            if booking["id"] == booking_id:
                booking["start"] = start.isoformat()
                booking["end"] = end.isoformat()
                booking["status"] = "booked"
                return booking
        raise KeyError(booking_id)
