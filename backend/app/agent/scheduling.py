"""Mock calendar: business hours, lead time, and spoken slot labels."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

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


@dataclass(frozen=True)
class Preference:
    day: datetime | None = None
    part: str | None = None

    @property
    def label(self) -> str:
        bits = []
        if self.day is not None:
            bits.append(self.day.strftime("%A"))
        if self.part:
            bits.append(self.part)
        return " ".join(bits) or "that window"


def parse_preference(text: str, now: datetime) -> Preference | None:
    norm = re.sub(r"\s+", " ", text.strip().lower())
    day = None
    if re.search(r"\btomorrow\b", norm):
        day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif re.search(r"\btoday\b", norm):
        day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        for name, index in WEEKDAY_NAMES.items():
            if re.search(rf"\b{name}\b", norm):
                delta = (index - now.weekday()) % 7
                day = (now + timedelta(days=delta)).replace(hour=0, minute=0, second=0, microsecond=0)
                break
    part = None
    if "morning" in norm:
        part = "morning"
    elif "afternoon" in norm:
        part = "afternoon"
    elif "evening" in norm:
        part = "evening"
    if day is None and part is None:
        return None
    return Preference(day=day, part=part)


def _part_ok(moment: datetime, part: str | None) -> bool:
    if part is None:
        return True
    hour = moment.hour
    if part == "morning":
        return hour < 12
    if part == "afternoon":
        return 12 <= hour < 16
    if part == "evening":
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
                if not _part_ok(start, pref.part):
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
    if matched:
        return matched, False
    return collect(None), True


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
