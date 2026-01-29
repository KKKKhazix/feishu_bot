from __future__ import annotations

import json
import os
import time
from typing import Any


class TokenStore:
    def __init__(self, path: str = "data/token_store.json") -> None:
        self.path = path

    def _read(self) -> dict[str, Any]:
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_user_token(self, user_id: str) -> dict[str, Any] | None:
        data = self._read()
        token = data.get(user_id)
        if not token:
            return None
        # expire_at is unix seconds
        if token.get("expire_at") and token["expire_at"] <= int(time.time()):
            return None
        return token

    def set_user_token(self, user_id: str, token: dict[str, Any]) -> None:
        data = self._read()
        data[user_id] = token
        self._write(data)
