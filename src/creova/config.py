from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from creova.domain.enums import CreativeProvider, ImageRenderer


class TelegramMode(StrEnum):
    POLLING = "polling"
    WEBHOOK = "webhook"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CREOVA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"

    telegram_bot_username: str = "FeloCreova_bot"
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_mode: TelegramMode = TelegramMode.POLLING
    telegram_webhook_base_url: str = ""
    telegram_webhook_path: str = "/telegram/webhook"
    telegram_webhook_secret: SecretStr = SecretStr("")

    bootstrap_admin_ids: frozenset[int] = Field(default_factory=frozenset)
    bootstrap_allowed_user_ids: frozenset[int] = Field(default_factory=frozenset)

    conversation_ttl_minutes: int = Field(default=60, ge=5, le=1440)
    max_clarification_questions: int = Field(default=6, ge=0, le=12)
    enabled_creative_providers: frozenset[CreativeProvider] = Field(
        default_factory=lambda: frozenset(CreativeProvider)
    )
    enabled_image_renderers: frozenset[ImageRenderer] = Field(
        default_factory=lambda: frozenset(ImageRenderer)
    )
    default_image_renderer: ImageRenderer = ImageRenderer.NANO_BANANA

    google_api_key: SecretStr = SecretStr("")
    google_image_model: str = "gemini-3.1-flash-image"
    google_assistant_model: str = ""

    openai_api_key: SecretStr = SecretStr("")
    openai_image_model: str = ""
    openai_assistant_model: str = ""

    anthropic_api_key: SecretStr = SecretStr("")
    anthropic_assistant_model: str = ""

    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://creova:creova@localhost:5432/creova"
    )
    s3_endpoint_url: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "creova-assets"
    s3_access_key_id: SecretStr = SecretStr("")
    s3_secret_access_key: SecretStr = SecretStr("")

    worker_poll_seconds: float = Field(default=2.0, gt=0)
    job_lease_seconds: int = Field(default=120, ge=30)
    signed_url_ttl_seconds: int = Field(default=900, ge=60, le=86400)
    asset_retention_days: int = Field(default=30, ge=1)
    metadata_retention_days: int = Field(default=90, ge=1)
    audit_retention_days: int = Field(default=180, ge=1)
    default_image_jobs_per_hour: int = Field(default=10, ge=0)
    default_daily_budget_usd: float = Field(default=10.0, ge=0)
    global_daily_budget_usd: float = Field(default=100.0, ge=0)

    @field_validator("bootstrap_admin_ids", "bootstrap_allowed_user_ids", mode="before")
    @classmethod
    def parse_id_set(cls, value: Any) -> frozenset[int]:
        if value in (None, ""):
            return frozenset()
        if isinstance(value, (set, frozenset, list, tuple)):
            return frozenset(int(item) for item in value)
        if isinstance(value, str):
            return frozenset(int(item.strip()) for item in value.split(",") if item.strip())
        raise TypeError("Expected a comma-separated string or a collection of Telegram IDs")

    @field_validator("enabled_creative_providers", mode="before")
    @classmethod
    def parse_creative_providers(cls, value: Any) -> frozenset[CreativeProvider]:
        return cls._parse_enum_set(value, CreativeProvider)

    @field_validator("enabled_image_renderers", mode="before")
    @classmethod
    def parse_image_renderers(cls, value: Any) -> frozenset[ImageRenderer]:
        return cls._parse_enum_set(value, ImageRenderer)

    @staticmethod
    def _parse_enum_set(value: Any, enum_type: type[StrEnum]) -> frozenset[Any]:
        if value in (None, ""):
            return frozenset()
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",") if item.strip()]
        elif isinstance(value, (set, frozenset, list, tuple)):
            items = list(value)
        else:
            raise TypeError("Expected a comma-separated string or a collection")
        return frozenset(enum_type(item) for item in items)

    @model_validator(mode="after")
    def validate_runtime(self) -> Settings:
        if self.telegram_bot_username.startswith("@"):
            raise ValueError("Telegram bot username must not include @")
        if self.telegram_mode is TelegramMode.WEBHOOK:
            if not self.telegram_webhook_base_url.startswith("https://"):
                raise ValueError("Webhook mode requires an HTTPS base URL")
            if not self.telegram_webhook_secret.get_secret_value():
                raise ValueError("Webhook mode requires a webhook secret")
        if self.default_image_renderer not in self.enabled_image_renderers:
            raise ValueError("Default image renderer must be enabled")
        return self

    @property
    def webhook_url(self) -> str:
        base = self.telegram_webhook_base_url.rstrip("/")
        path = self.telegram_webhook_path.lstrip("/")
        return f"{base}/{path}"

    def require_bot_token(self) -> str:
        token = self.telegram_bot_token.get_secret_value()
        if not token:
            raise RuntimeError("CREOVA_TELEGRAM_BOT_TOKEN is required")
        return token

    def provider_has_credentials(self, provider: CreativeProvider) -> bool:
        if provider is CreativeProvider.NANO_BANANA:
            return bool(self.google_api_key.get_secret_value())
        if provider is CreativeProvider.CHATGPT:
            return bool(self.openai_api_key.get_secret_value())
        return bool(self.anthropic_api_key.get_secret_value())

    def renderer_has_credentials(self, renderer: ImageRenderer) -> bool:
        if renderer is ImageRenderer.NANO_BANANA:
            return bool(self.google_api_key.get_secret_value())
        return bool(self.openai_api_key.get_secret_value())
