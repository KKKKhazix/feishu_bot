from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from app.calendar_client import CalendarClient
from app.config import settings
from app.feishu_client import FeishuClient
from app.ocr import OcrError, ocr_image
from app.parser import extract_event
from app.storage import TokenStore

app = FastAPI()

feishu = FeishuClient()
calendar = CalendarClient()
tokens = TokenStore()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/feishu/oauth/callback")
async def oauth_callback(request: Request) -> dict[str, Any]:
    params = dict(request.query_params)
    code = params.get("code")
    user_id = params.get("state")  # use state to pass user_id
    if not code or not user_id:
        raise HTTPException(status_code=400, detail="missing code/state")

    token_data = feishu.exchange_code_for_user_token(code)
    # try to map to standard fields
    access_token = token_data.get("access_token") or token_data.get("data", {}).get("access_token")
    refresh_token = token_data.get("refresh_token") or token_data.get("data", {}).get("refresh_token")
    expires_in = token_data.get("expires_in") or token_data.get("data", {}).get("expires_in", 0)
    if not access_token:
        raise HTTPException(status_code=400, detail="access_token not found in response")

    tokens.set_user_token(
        user_id,
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expire_at": int(__import__("time").time()) + int(expires_in) - 60,
        },
    )
    return {"ok": True}


@app.post("/feishu/event")
async def feishu_event(request: Request) -> dict[str, Any]:
    body = await request.json()

    # URL verification
    if body.get("type") == "url_verification":
        if body.get("token") != settings.feishu_verification_token:
            raise HTTPException(status_code=403, detail="invalid verification token")
        return {"challenge": body.get("challenge")}

    # basic token check
    if body.get("token") and body.get("token") != settings.feishu_verification_token:
        raise HTTPException(status_code=403, detail="invalid verification token")

    event = body.get("event", {})
    message = event.get("message", {})
    sender = event.get("sender", {})

    user_id = (
        sender.get("sender_id", {}).get("user_id")
        or sender.get("sender_id", {}).get("open_id")
        or sender.get("sender_id", {}).get("union_id")
    )
    if not user_id:
        return {"ok": True}

    content = _parse_content(message.get("content"))
    message_type = message.get("message_type")
    message_id = message.get("message_id")

    text = ""
    if message_type == "text" and isinstance(content, dict):
        text = content.get("text", "")
    elif message_type == "image":
        file_key = _extract_file_key(content)
        if file_key and message_id:
            data = feishu.download_message_resource(message_id, file_key)
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / "image"
                path.write_bytes(data)
                try:
                    text = ocr_image(str(path), backend=settings.bot_ocr_backend)
                except OcrError as exc:
                    feishu.send_message(user_id, "text", {"text": f"OCR 失败: {exc}"})
                    return {"ok": True}
    else:
        return {"ok": True}

    event_info = extract_event(
        text=text, timezone=settings.bot_timezone, default_duration_minutes=settings.bot_default_duration_minutes
    )
    if not event_info:
        feishu.send_message(user_id, "text", {"text": "未能识别时间信息，无法创建日程。"})
        return {"ok": True}

    user_token = tokens.get_user_token(user_id)
    if not user_token:
        auth_url = _build_oauth_url(user_id)
        feishu.send_message(
            user_id,
            "text",
            {"text": f"请先授权日历访问权限：{auth_url}"},
        )
        return {"ok": True}

    calendar_id = calendar.get_primary_calendar_id(user_token["access_token"])
    payload = {
        "summary": event_info.title,
        "description": event_info.description,
        "start_time": {
            "date_time": event_info.start.isoformat(),
            "time_zone": settings.bot_timezone,
        },
        "end_time": {
            "date_time": event_info.end.isoformat(),
            "time_zone": settings.bot_timezone,
        },
    }
    if event_info.location:
        payload["location"] = {"name": event_info.location}

    result = calendar.create_event(user_token["access_token"], calendar_id, payload)
    feishu.send_message(user_id, "text", {"text": f"已创建日程：{event_info.title}"})
    return {"ok": True, "data": result}


def _parse_content(content: Any) -> dict[str, Any] | str | None:
    if content is None:
        return None
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content
    return None


def _extract_file_key(content: Any) -> str | None:
    if not isinstance(content, dict):
        return None
    return content.get("image_key") or content.get("file_key") or content.get("file_key")


def _build_oauth_url(user_id: str) -> str:
    if not settings.feishu_oauth_authorize_url:
        return "未配置 FEISHU_OAUTH_AUTHORIZE_URL"
    if not settings.feishu_oauth_redirect_uri or not settings.feishu_oauth_scope:
        return "未配置 OAuth 回调或 scope"
    return (
        f"{settings.feishu_oauth_authorize_url}"
        f"?app_id={settings.feishu_app_id}"
        f"&redirect_uri={settings.feishu_oauth_redirect_uri}"
        f"&state={user_id}"
        f"&scope={settings.feishu_oauth_scope}"
    )
