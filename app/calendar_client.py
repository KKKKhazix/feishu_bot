from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class CalendarClient:
    def get_primary_calendar_id(self, user_access_token: str) -> str:
        if settings.feishu_calendar_id:
            return settings.feishu_calendar_id
        if not settings.feishu_calendar_primary_endpoint:
            raise RuntimeError("FEISHU_CALENDAR_PRIMARY_ENDPOINT not configured")

        headers = {"Authorization": f"Bearer {user_access_token}"}
        resp = httpx.get(settings.feishu_calendar_primary_endpoint, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Best-effort extraction; adjust to official response schema
        for key in ("data", "calendar", "primary_calendar", "items", "calendars"):
            if key in data:
                value = data[key]
                if isinstance(value, dict) and "calendar_id" in value:
                    return value["calendar_id"]
                if isinstance(value, list) and value:
                    item = value[0]
                    if isinstance(item, dict) and "calendar_id" in item:
                        return item["calendar_id"]

        raise RuntimeError("Cannot find primary calendar_id in response")

    def create_event(self, user_access_token: str, calendar_id: str, event: dict[str, Any]) -> dict[str, Any]:
        if not settings.feishu_calendar_event_create_endpoint:
            raise RuntimeError("FEISHU_CALENDAR_EVENT_CREATE_ENDPOINT not configured")

        headers = {"Authorization": f"Bearer {user_access_token}"}
        payload = {"calendar_id": calendar_id, **event}
        resp = httpx.post(
            settings.feishu_calendar_event_create_endpoint, headers=headers, json=payload, timeout=15
        )
        resp.raise_for_status()
        return resp.json()
