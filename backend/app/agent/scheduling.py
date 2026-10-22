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
    day_until: datetime | None = None
    part: str | None = None
    earliest: time | None = None
    around: time | None = None
    exclude_weekdays: tuple[int, ...] = ()

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
        return (
            self.day is None
            and self.day_until is None
            and self.part is None
            and self.earliest is None
            and self.around is None
            and not self.exclude_weekdays
        )


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


_WORD_HOUR = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def _upcoming(now: datetime, weekday: int, *, force_next: bool = False) -> datetime:
    delta = (weekday - now.weekday()) % 7
    if force_next and delta == 0:
        delta = 7
    return _midnight(now + timedelta(days=delta))


_ORDINALS = {
    "first": 1,
    "1st": 1,
    "second": 2,
    "2nd": 2,
    "third": 3,
    "3rd": 3,
    "fourth": 4,
    "4th": 4,
    "fifth": 5,
    "5th": 5,
}

_HOLIDAYS = {
    "halloween": (10, 31),
    "christmas eve": (12, 24),
    "christmas": (12, 25),
    "new year's day": (1, 1),
    "new years day": (1, 1),
    "independence day": (7, 4),
    "july 4th": (7, 4),
    "july 4": (7, 4),
}

_HOUR_TOKEN = r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"


def _hour_token(token: str) -> int:
    if token.isdigit():
        return int(token)
    return _WORD_HOUR[token]


def _nth_date(year: int, month: int, weekday: int, n: int, tz) -> datetime | None:
    first = datetime(year, month, 1, tzinfo=tz)
    delta = (weekday - first.weekday()) % 7
    day_num = 1 + delta + (n - 1) * 7
    try:
        return datetime(year, month, day_num, tzinfo=tz)
    except ValueError:
        return None


def _nth_in_month(norm: str, now: datetime) -> datetime | None:
    match = re.search(
        r"\b(?:the\s+)?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\s+"
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+"
        r"(?:in|of)\s+"
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\b",
        norm,
    )
    if not match:
        return None
    found = _nth_date(now.year, MONTHS[match.group(3)], WEEKDAY_NAMES[match.group(2)], _ORDINALS[match.group(1)], now.tzinfo)
    if found is None:
        return None
    if found.date() < now.date():
        found = _nth_date(now.year + 1, MONTHS[match.group(3)], WEEKDAY_NAMES[match.group(2)], _ORDINALS[match.group(1)], now.tzinfo)
    return _midnight(found) if found is not None else None


def _holiday(norm: str, now: datetime) -> datetime | None:
    for name, (month, day) in sorted(_HOLIDAYS.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{name}\b", norm):
            candidate = datetime(now.year, month, day, tzinfo=now.tzinfo)
            if candidate.date() < now.date():
                candidate = candidate.replace(year=now.year + 1)
            return _midnight(candidate)
    return None


def _on_month_day(now: datetime, month_name: str, day_num: int) -> datetime | None:
    month = MONTHS[month_name]
    try:
        candidate = datetime(now.year, month, day_num, tzinfo=now.tzinfo)
    except ValueError:
        return None
    if candidate.date() < now.date():
        candidate = candidate.replace(year=now.year + 1)
    return _midnight(candidate)


def _named_holiday(norm: str, now: datetime) -> datetime | None:
    if re.search(r"\bthanksgiving\b", norm):
        found = _nth_date(now.year, 11, 3, 4, now.tzinfo)
        if found is not None and found.date() < now.date():
            found = _nth_date(now.year + 1, 11, 3, 4, now.tzinfo)
        return _midnight(found) if found is not None else None
    return _holiday(norm, now)


_MINUTE_WORD = {
    "thirty": "30",
    "fifteen": "15",
    "forty-five": "45",
    "forty five": "45",
    "forty": "40",
    "twenty": "20",
}


def _spoken_clock(norm: str) -> time | None:
    compound = re.search(
        rf"\b{_HOUR_TOKEN}[\s-](thirty|fifteen|forty-five|forty five|forty|twenty)\b(?:\s*(am|pm))?",
        norm,
    )
    if compound:
        return _hour_from_match(
            str(_hour_token(compound.group(1))),
            _MINUTE_WORD[compound.group(2)],
            compound.group(3),
            assume_pm=True,
        )
    half = re.search(rf"\bhalf past\s+{_HOUR_TOKEN}\s*(am|pm)?\b", norm)
    if half:
        return _hour_from_match(str(_hour_token(half.group(1))), "30", half.group(2), assume_pm=True)
    quarter_past = re.search(rf"\bquarter past\s+{_HOUR_TOKEN}\s*(am|pm)?\b", norm)
    if quarter_past:
        return _hour_from_match(str(_hour_token(quarter_past.group(1))), "15", quarter_past.group(2), assume_pm=True)
    quarter_to = re.search(rf"\bquarter to\s+{_HOUR_TOKEN}\s*(am|pm)?\b", norm)
    if quarter_to:
        hour = _hour_token(quarter_to.group(1))
        hour = 12 if hour == 1 else hour - 1
        return _hour_from_match(str(hour), "45", quarter_to.group(2), assume_pm=True)
    ish = re.search(rf"\b(?:around\s+|at\s+)?{_HOUR_TOKEN}\s*(?::(\d{{2}}))?\s*(am|pm)?\s*ish\b", norm)
    if ish:
        return _hour_from_match(str(_hour_token(ish.group(1))), ish.group(2), ish.group(3), assume_pm=True)
    return None


def parse_preference(text: str, now: datetime) -> Preference | None:
    norm = re.sub(r"\s+", " ", text.strip().lower())
    day = None
    day_until = None
    month_name = r"january|february|march|april|may|june|july|august|september|october|november|december"
    month_match = re.search(
        rf"\b({month_name})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b",
        norm,
    )
    span_match = re.search(rf"\b(early|mid|middle|late)[\s-]+(?:of\s+)?({month_name})\b", norm)
    week_from = re.search(r"\ba week from (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", norm)
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
    elif span_match:
        day_num = {"early": 5, "mid": 15, "middle": 15, "late": 24}[span_match.group(1)]
        day = _on_month_day(now, span_match.group(2), day_num)
    elif week_from:
        base = _upcoming(now, WEEKDAY_NAMES[week_from.group(1)])
        if base.date() == now.date():
            base = _midnight(now)
        day = base + timedelta(days=7)
    elif re.search(r"\bend of next week\b", norm):
        days_until_monday = (7 - now.weekday()) % 7 or 7
        next_monday = _midnight(now + timedelta(days=days_until_monday))
        day = next_monday + timedelta(days=3)
        day_until = next_monday + timedelta(days=5)
    elif re.search(r"\bday after tomorrow\b", norm):
        day = _midnight(now + timedelta(days=2))
    elif re.search(r"\b(?:two weeks from today|two weeks from now|in two weeks)\b", norm):
        day = _midnight(now + timedelta(days=14))
    elif re.search(r"\bthis weekend\b", norm):
        delta = (5 - now.weekday()) % 7
        day = _midnight(now + timedelta(days=delta))
        day_until = day + timedelta(days=1)
    elif re.search(r"\btomorrow\b", norm):
        day = _midnight(now + timedelta(days=1))
    elif re.search(r"\btoday\b", norm):
        day = _midnight(now)
    elif (nth := _nth_in_month(norm, now)) is not None:
        day = nth
    elif (holiday := _named_holiday(norm, now)) is not None:
        day = holiday
    elif (after_next := re.search(
        r"\b(?:the\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+after next\b",
        norm,
    )) is not None:
        day = _upcoming(now, WEEKDAY_NAMES[after_next.group(1)], force_next=True) + timedelta(days=7)
    elif re.search(r"\bnext week\b", norm):
        days_until_monday = (7 - now.weekday()) % 7 or 7
        next_monday = _midnight(now + timedelta(days=days_until_monday))
        day = next_monday
        day_until = next_monday + timedelta(days=6)
    else:
        for name, index in WEEKDAY_NAMES.items():
            if re.search(rf"\bexcept {name}\b", norm):
                continue
            if re.search(rf"\b{name}\b", norm):
                day = _upcoming(now, index, force_next=bool(re.search(rf"\bnext {name}\b", norm)))
                break
        if day is None:
            bare_month = re.search(rf"\b({month_name})\b", norm)
            if bare_month and not re.search(r"\b\d{1,2}\b", norm):
                day = _on_month_day(now, bare_month.group(1), 15)
    excluded = tuple(
        index for name, index in WEEKDAY_NAMES.items() if re.search(rf"\bexcept {name}\b", norm)
    )
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
    around = _spoken_clock(norm)
    if around is None and re.search(r"\bnoon\b", norm):
        around = time(12, 0)
    elif around is None:
        around_match = re.search(r"\b(?:at|around)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", norm)
        if around_match:
            around = _hour_from_match(around_match.group(1), around_match.group(2), around_match.group(3), assume_pm=True)
        else:
            word_hour = re.search(
                r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b"
                r"(?:\s+o'clock)?(?:\s+in the\s+(morning|afternoon|evening))?",
                norm,
            )
            if word_hour and word_hour.group(2):
                hour = _WORD_HOUR[word_hour.group(1)]
                part_name = word_hour.group(2)
                if part_name == "afternoon" and hour < 12:
                    hour += 12
                if part_name == "evening" and hour < 12:
                    hour += 12
                around = time(hour, 0)
    preference = Preference(
        day=day,
        day_until=day_until,
        part=part,
        earliest=earliest,
        around=around,
        exclude_weekdays=excluded,
    )
    if preference.is_empty() and day_until is None:
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
        cap = 16 if pref is not None and pref.around is not None else limit
        for start in iter_slot_starts(config, now):
            if pref is not None:
                if pref.day is not None and pref.day_until is None and start.date() != pref.day.date():
                    continue
                if pref.day is not None and start.date() < pref.day.date():
                    continue
                if pref.day_until is not None and start.date() > pref.day_until.date():
                    continue
                if pref.day is None and pref.day_until is not None:
                    continue
                if pref.exclude_weekdays and start.weekday() in pref.exclude_weekdays:
                    continue
                if not _part_ok(start, pref):
                    continue
            end = start + duration
            if overlaps(start, end, busy):
                continue
            found.append(start)
            if len(found) >= cap:
                break
        return found

    if preference is None:
        return collect(None), False
    last = (now + timedelta(days=config.horizon_days)).date()
    if preference.day is not None and preference.day.date() > last:
        return [], False
    matched = collect(preference)
    if matched and preference.around is not None:
        matched = sorted(matched, key=lambda moment: abs(_minutes(moment) - _minutes_of(preference.around)))[:limit]
    if matched:
        return matched[:limit], False
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
