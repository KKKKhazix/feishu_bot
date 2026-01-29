from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    feishu_app_id: str
    feishu_app_secret: str
    feishu_verification_token: str
    feishu_encrypt_key: str | None = None

    feishu_oauth_redirect_uri: str | None = None
    feishu_oauth_scope: str | None = None
    feishu_oauth_authorize_url: str | None = None

    feishu_api_base: str = "https://open.feishu.cn"
    feishu_app_access_token_endpoint: str = (
        "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
    )
    feishu_message_resource_endpoint: str = (
        "https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{file_key}"
    )

    feishu_calendar_primary_endpoint: str | None = None
    feishu_calendar_event_create_endpoint: str | None = None
    feishu_calendar_id: str | None = None

    feishu_user_access_token_endpoint: str | None = None
    feishu_send_message_endpoint: str | None = None

    bot_timezone: str = "Asia/Shanghai"
    bot_default_duration_minutes: int = 60
    bot_ocr_backend: str = "tesseract"


settings = Settings()
