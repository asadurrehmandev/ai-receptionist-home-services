"""Load a per-business YAML profile."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


@dataclass(frozen=True)
class DayHours:
    open: time
    close: time


@dataclass(frozen=True)
class PriceRule:
    id: str
    label: str
    keywords: tuple[str, ...]
    low_usd: int
    high_usd: int


@dataclass(frozen=True)
class BusinessConfig:
    name: str
    agent_name: str
    trade: str
    phone_display: str
    timezone: str
    city: str
    cities: tuple[str, ...]
    zips: frozenset[str]
    hours: dict[int, DayHours | None]
    slot_minutes: int
    lead_minutes: int
    horizon_days: int
    services: tuple[str, ...]
    diagnostic_fee_usd: int
    after_hours_fee_usd: int
    emergency_dispatch_usd: int
    price_rules: tuple[PriceRule, ...]
    on_call_name: str
    on_call_phone: str
    webhook_url: str
    crm_provider_label: str
    voice_mode: str
    gather_voice: str
    phone_e164: str = "+15125550142"
    gather_language: str = "en-US"
    on_call_phone_2: str = ""

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def price_for(self, text: str) -> PriceRule | None:
        haystack = (text or "").lower()
        for rule in self.price_rules:
            if any(keyword in haystack for keyword in rule.keywords):
                return rule
        return None

    def public_dict(self) -> dict:
        hours = {}
        for index, name in enumerate(WEEKDAYS):
            block = self.hours.get(index)
            hours[name] = None if block is None else {"open": block.open.strftime("%H:%M"), "close": block.close.strftime("%H:%M")}
        return {
            "business": {
                "name": self.name,
                "agent_name": self.agent_name,
                "trade": self.trade,
                "phone_display": self.phone_display,
                "timezone": self.timezone,
                "city": self.city,
            },
            "service_area": {"cities": list(self.cities), "zips": sorted(self.zips)},
            "hours": hours,
            "scheduling": {
                "slot_minutes": self.slot_minutes,
                "lead_minutes": self.lead_minutes,
                "horizon_days": self.horizon_days,
            },
            "services": list(self.services),
            "pricing": {
                "diagnostic_fee_usd": self.diagnostic_fee_usd,
                "after_hours_fee_usd": self.after_hours_fee_usd,
                "emergency_dispatch_usd": self.emergency_dispatch_usd,
                "rules": [
                    {
                        "id": rule.id,
                        "label": rule.label,
                        "low_usd": rule.low_usd,
                        "high_usd": rule.high_usd,
                    }
                    for rule in self.price_rules
                ],
            },
            "escalation": {"on_call_name": self.on_call_name, "on_call_phone": self.on_call_phone},
            "crm": {"webhook_url": self.webhook_url, "provider_label": self.crm_provider_label},
            "voice": {"mode": self.voice_mode, "gather_voice": self.gather_voice},
        }


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def load_business(path: str | Path) -> BusinessConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    business = raw["business"]
    area = raw["service_area"]
    scheduling = raw["scheduling"]
    pricing = raw["pricing"]
    escalation = raw["escalation"]
    crm = raw.get("crm") or {}
    voice = raw.get("voice") or {}

    hours: dict[int, DayHours | None] = {}
    for index, name in enumerate(WEEKDAYS):
        block = (raw.get("hours") or {}).get(name)
        if not block:
            hours[index] = None
        else:
            hours[index] = DayHours(open=_parse_hhmm(block["open"]), close=_parse_hhmm(block["close"]))

    rules = tuple(
        PriceRule(
            id=item["id"],
            label=item["label"],
            keywords=tuple(k.lower() for k in item["keywords"]),
            low_usd=int(item["low_usd"]),
            high_usd=int(item["high_usd"]),
        )
        for item in pricing.get("rules") or []
    )
    return BusinessConfig(
        name=business["name"],
        agent_name=business["agent_name"],
        trade=business["trade"],
        phone_display=business["phone_display"],
        timezone=business["timezone"],
        city=business["city"],
        cities=tuple(area["cities"]),
        zips=frozenset(str(z) for z in area["zips"]),
        hours=hours,
        slot_minutes=int(scheduling["slot_minutes"]),
        lead_minutes=int(scheduling["lead_minutes"]),
        horizon_days=int(scheduling["horizon_days"]),
        services=tuple(raw.get("services") or []),
        diagnostic_fee_usd=int(pricing["diagnostic_fee_usd"]),
        after_hours_fee_usd=int(pricing["after_hours_fee_usd"]),
        emergency_dispatch_usd=int(pricing["emergency_dispatch_usd"]),
        price_rules=rules,
        on_call_name=escalation["on_call_name"],
        on_call_phone=escalation["on_call_phone"],
        on_call_phone_2=str(escalation.get("on_call_phone_2") or ""),
        webhook_url=(crm.get("webhook_url") or "").strip(),
        crm_provider_label=crm.get("provider_label") or "webhook",
        voice_mode=voice.get("mode") or "auto",
        gather_voice=voice.get("gather_voice") or "Polly.Joanna",
        phone_e164=str(business.get("phone") or "+15125550142"),
        gather_language=str(voice.get("language") or "en-US"),
    )
