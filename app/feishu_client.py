from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import settings


class FeishuClient:
    def __init__(self) -> None:
        self._token_cache: dict[str, Any] | None = None

    def get_app_access_token(self) -> str:
        if self._token_cache and self._token_cache["expire_at"] > int(time.time()):
            return self._token_cache["app_access_token"]

        payload = {"app_id": settings.feishu_app_id, "app_secret": settings.feishu_app_secret}
        resp = httpx.post(settings.feishu_app_access_token_endpoint, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"app_access_token error: {data}")

        app_token = data["app_access_token"]
        tenant_token = data.get("tenant_access_token") or app_token
        expire = int(time.time()) + int(data.get("expire", 0)) - 60
        self._token_cache = {
            "app_access_token": app_token,
            "tenant_access_token": tenant_token,
            "expire_at": expire,
        }
        return app_token

    def get_tenant_access_token(self) -> str:
        if self._token_cache and self._token_cache["expire_at"] > int(time.time()):
            return self._token_cache["tenant_access_token"]
        # refresh cache
        self.get_app_access_token()
        assert self._token_cache is not None
        return self._token_cache["tenant_access_token"]

    def download_message_resource(self, message_id: str, file_key: str) -> bytes:
        token = self.get_tenant_access_token()
        url = settings.feishu_message_resource_endpoint.format(
            message_id=message_id, file_key=file_key
        )
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content

    def send_message(self, receive_id: str, msg_type: str, content: dict[str, Any]) -> None:
        if not settings.feishu_send_message_endpoint:
            return
        token = self.get_tenant_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "receive_id_type": "user_id",
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content,
        }
        resp = httpx.post(settings.feishu_send_message_endpoint, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()

    def exchange_code_for_user_token(self, code: str) -> dict[str, Any]:
        if not settings.feishu_user_access_token_endpoint:
            raise RuntimeError("FEISHU_USER_ACCESS_TOKEN_ENDPOINT not configured")
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.feishu_app_id,
            "client_secret": settings.feishu_app_secret,
            "redirect_uri": settings.feishu_oauth_redirect_uri,
        }
        resp = httpx.post(settings.feishu_user_access_token_endpoint, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
