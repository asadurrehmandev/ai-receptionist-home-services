"""Mock calendar: business hours, lead time, and spoken slot labels."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from app.config_loader import BusinessConfig

WEEKDAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


@dataclass(frozen=True)
class Preference:
    day: datetime | None = None
    part: str | None = None
    earliest: time | None = None
    around: time | None = None

    @property
    def label(self) -> str:
        bits = []
        if self.day is not None:
            bits.append(self.day.strftime("%A"))
        if self.part:
            bits.append(self.part)
        if self.earliest is not None:
            bits.append(f"after {_clock(self.earliest)}")
        if self.around is not None:
            bits.append(f"around {_clock(self.around)}")
        return " ".join(bits) or "that window"

    def is_empty(self) -> bool:
        return self.day is None and self.part is None and self.earliest is None and self.around is None


def _midnight(moment: datetime) -> datetime:
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def _clock(value: time) -> str:
    hour = value.hour % 12 or 12
    suffix = "AM" if value.hour < 12 else "PM"
    return f"{hour}:{value.minute:02d} {suffix}"


def _hour_from_match(hour_text: str, minute_text: str | None, suffix: str | None, *, assume_pm: bool) -> time:
    hour = int(hour_text)
    minute = int(minute_text or "0")
    if suffix == "pm" and hour < 12:
        hour += 12
    elif suffix == "am" and hour == 12:
        hour = 0
    elif suffix is None and assume_pm and hour < 8:
        hour += 12
    hour = min(hour, 23)
    return time(hour, minute)


def parse_preference(text: str, now: datetime) -> Preference | None:
    norm = re.sub(r"\s+", " ", text.strip().lower())
    day = None
    month_match = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?\b",
        norm,
    )
    if month_match:
        month = MONTHS[month_match.group(1)]
        day_num = int(month_match.group(2))
        year = now.year
        try:
            candidate = datetime(year, month, day_num, tzinfo=now.tzinfo)
        except ValueError:
            candidate = None
        if candidate is not None:
            if candidate.date() < now.date():
                candidate = candidate.replace(year=year + 1)
            day = _midnight(candidate)
    elif re.search(r"\bthis weekend\b", norm):
        delta = (5 - now.weekday()) % 7
        day = _midnight(now + timedelta(days=delta))
    elif re.search(r"\btomorrow\b", norm):
        day = _midnight(now + timedelta(days=1))
    elif re.search(r"\btoday\b", norm):
        day = _midnight(now)
    else:
        for name, index in WEEKDAY_NAMES.items():
            if re.search(rf"\b{name}\b", norm):
                delta = (index - now.weekday()) % 7
                if re.search(rf"\bnext {name}\b", norm) and delta == 0:
                    delta = 7
                day = _midnight(now + timedelta(days=delta))
                break
    part = None
    if "after lunch" in norm or "afternoon" in norm:
        part = "afternoon"
    elif "morning" in norm:
        part = "morning"
    elif "evening" in norm or "tonight" in norm:
        part = "evening"
    earliest = None
    after = re.search(r"\bafter\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", norm)
    if after and "after lunch" not in norm:
        earliest = _hour_from_match(after.group(1), after.group(2), after.group(3), assume_pm=True)
    around = None
    around_match = re.search(r"\b(?:at|around)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", norm)
    if around_match:
        around = _hour_from_match(around_match.group(1), around_match.group(2), around_match.group(3), assume_pm=True)
    preference = Preference(day=day, part=part, earliest=earliest, around=around)
    if preference.is_empty():
        return None
    return preference


def _part_ok(moment: datetime, preference: Preference | None) -> bool:
    if preference is None:
        return True
    if preference.earliest is not None and moment.time() < preference.earliest:
        return False
    if preference.part is None:
        return True
    hour = moment.hour
    if preference.part == "morning":
        return hour < 12
    if preference.part == "afternoon":
        return 12 <= hour < 17
    if preference.part == "evening":
        return hour >= 16
    return True


def overlaps(start: datetime, end: datetime, busy: list[tuple[datetime, datetime]]) -> bool:
    for busy_start, busy_end in busy:
        if start < busy_end and end > busy_start:
            return True
    return False


def iter_slot_starts(config: BusinessConfig, now: datetime):
    lead = now + timedelta(minutes=config.lead_minutes)
    for offset in range(config.horizon_days + 1):
        day = (now + timedelta(days=offset)).date()
        hours = config.hours.get(day.weekday())
        if hours is None:
            continue
        cursor = datetime.combine(day, hours.open, tzinfo=config.zone)
        close = datetime.combine(day, hours.close, tzinfo=config.zone)
        step = timedelta(minutes=config.slot_minutes)
        while cursor + step <= close:
            if cursor >= lead:
                yield cursor
            cursor += step


def available_slots(
    config: BusinessConfig,
    now: datetime,
    busy: list[tuple[datetime, datetime]],
    preference: Preference | None = None,
    limit: int = 3,
) -> tuple[list[datetime], bool]:
    """Return up to `limit` slots. The bool is True when the preference was relaxed."""

    def collect(pref: Preference | None) -> list[datetime]:
        found: list[datetime] = []
        duration = timedelta(minutes=config.slot_minutes)
        for start in iter_slot_starts(config, now):
            if pref is not None:
                if pref.day is not None and start.date() != pref.day.date():
                    continue
                if not _part_ok(start, pref):
                    continue
            end = start + duration
            if overlaps(start, end, busy):
                continue
            found.append(start)
            if len(found) >= limit:
                break
        return found

    if preference is None:
        return collect(None), False
    matched = collect(preference)
    if matched and preference.around is not None:
        matched = sorted(matched, key=lambda moment: abs(_minutes(moment) - _minutes_of(preference.around)))
    if matched:
        return matched, False
    return collect(None), True


def latest_on_day(
    config: BusinessConfig,
    now: datetime,
    busy: list[tuple[datetime, datetime]],
    day: datetime,
) -> datetime | None:
    preference = Preference(day=day)
    slots, _ = available_slots(config, now, busy, preference=preference, limit=12)
    return slots[-1] if slots else None


def _minutes(moment: datetime) -> int:
    return moment.hour * 60 + moment.minute


def _minutes_of(value: time) -> int:
    return value.hour * 60 + value.minute


def format_slot(moment: datetime) -> str:
    hour = moment.strftime("%I").lstrip("0") or "0"
    return f"{moment.strftime('%A')}, {moment.strftime('%B')} {moment.day} at {hour}:{moment.strftime('%M')} {moment.strftime('%p')}"


def join_slots(moments: list[datetime]) -> str:
    labels = [format_slot(moment) for moment in moments]
    if not labels:
        return "no open visits"
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} or {labels[1]}"
    return ", ".join(labels[:-1]) + f", or {labels[-1]}"


def time_phrases(moment: datetime) -> list[str]:
    hour24 = moment.hour
    hour12 = hour24 % 12 or 12
    suffix = "am" if hour24 < 12 else "pm"
    minute = moment.strftime("%M")
    phrases = [
        f"{hour12}:{minute} {suffix}",
        f"{hour12}:{minute}{suffix}",
        f"{hour12} {suffix}",
        f"{hour12}{suffix}",
    ]
    if minute == "00":
        phrases.append(f"{hour12} o'clock")
    return phrases


def match_offered(offered: list[datetime], text: str) -> datetime | None:
    from app.agent.nlu import selection_index

    index = selection_index(text)
    if index is not None and offered:
        return offered[min(index, len(offered) - 1)]
    norm = re.sub(r"[.]", "", text.strip().lower())
    norm = norm.replace("p.m", "pm").replace("a.m", "am")
    hits = []
    for moment in offered:
        if any(phrase in norm for phrase in time_phrases(moment)):
            hits.append(moment)
    if len(hits) == 1:
        return hits[0]
    weekday_hits = []
    for name, index in WEEKDAY_NAMES.items():
        if re.search(rf"\b{name}\b", norm):
            weekday_hits = [moment for moment in offered if moment.weekday() == index]
            break
    if len(weekday_hits) == 1:
        return weekday_hits[0]
    return None
