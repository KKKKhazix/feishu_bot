from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import dateparser
from dateparser.search import search_dates


@dataclass
class EventInfo:
    title: str
    start: datetime
    end: datetime
    description: str | None = None
    location: str | None = None


_DURATION_PATTERN = re.compile(r"(\\d+)\\s*(小时|h|H|hour|hours|分钟|min|m)", re.IGNORECASE)
_LOCATION_PATTERN = re.compile(r"(地点|位置|地址)[:：]\\s*(.+)")


def extract_event(text: str, timezone: str, default_duration_minutes: int) -> Optional[EventInfo]:
    if not text.strip():
        return None

    found = search_dates(
        text,
        languages=["zh", "en"],
        settings={
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": timezone,
        },
    )
    if not found:
        return None

    # take first detected datetime
    _, dt = found[0]

    duration = _extract_duration_minutes(text, default_duration_minutes)
    end = dt + timedelta(minutes=duration)

    location = None
    loc_match = _LOCATION_PATTERN.search(text)
    if loc_match:
        location = loc_match.group(2).strip()

    title = _infer_title(text, dt)

    return EventInfo(title=title, start=dt, end=end, description=text.strip(), location=location)


def _extract_duration_minutes(text: str, default_minutes: int) -> int:
    match = _DURATION_PATTERN.search(text)
    if not match:
        return default_minutes
    value = int(match.group(1))
    unit = match.group(2).lower()
    if unit in ("小时", "h", "hour", "hours"):
        return value * 60
    return value


def _infer_title(text: str, dt: datetime) -> str:
    # heuristic: take first line without datetime string
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "日程"
    candidate = lines[0]
    # remove common datetime tokens
    candidate = re.sub(r"\\d{1,2}:\\d{2}", "", candidate)
    candidate = re.sub(r"\\d{4}[年\\-/]\\d{1,2}[月\\-/]\\d{1,2}[日号]?", "", candidate)
    candidate = candidate.strip(" -|，,")
    return candidate or "日程"
