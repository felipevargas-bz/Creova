from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from creova.domain.enums import CreativeProvider, ImageRenderer

EXPECTED_TELEGRAM_BOT_USERNAME = "FeloCreova_bot"


class TelegramMode(StrEnum):
    POLLING = "polling"
    WEBHOOK = "webhook"


class HealthState(StrEnum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True, slots=True)
class ProviderAvailability:
    provider: CreativeProvider
    assistant_enabled: bool
    renderer_enabled: bool
    assistant_available: bool
    renderer_available: bool
    has_credentials: bool
    health: HealthState
    missing_variable_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StartupDiagnostics:
    missing_required_variable_names: tuple[str, ...]
    missing_optional_variable_names: tuple[str, ...]
    provider_availability: tuple[ProviderAvailability, ...]


_PROVIDER_SECRET_VARIABLES: dict[CreativeProvider, str] = {
    CreativeProvider.NANO_BANANA: "CREOVA_GOOGLE_API_KEY",
    CreativeProvider.CHATGPT: "CREOVA_OPENAI_API_KEY",
    CreativeProvider.CLAUDE: "CREOVA_ANTHROPIC_API_KEY",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CREOVA_",
        env_file=".env",
        env_file_encoding="utf-8",
        enable_decoding=False,
        extra="ignore",
    )

    env: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"

    telegram_bot_username: str = EXPECTED_TELEGRAM_BOT_USERNAME
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
        if self.telegram_bot_username != EXPECTED_TELEGRAM_BOT_USERNAME:
            raise ValueError(f"Telegram bot username must be {EXPECTED_TELEGRAM_BOT_USERNAME}")
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

    def startup_diagnostics(
        self,
        *,
        require_bot_token: bool = False,
        provider_health: dict[CreativeProvider, HealthState] | None = None,
    ) -> StartupDiagnostics:
        availability = self.provider_availability(provider_health=provider_health)
        return StartupDiagnostics(
            missing_required_variable_names=self.missing_required_variable_names(
                require_bot_token=require_bot_token
            ),
            missing_optional_variable_names=tuple(
                variable
                for item in availability
                for variable in item.missing_variable_names
                if item.assistant_enabled or item.renderer_enabled
            ),
            provider_availability=availability,
        )

    def missing_required_variable_names(self, *, require_bot_token: bool) -> tuple[str, ...]:
        if require_bot_token and not self.telegram_bot_token.get_secret_value():
            return ("CREOVA_TELEGRAM_BOT_TOKEN",)
        return ()

    def provider_availability(
        self,
        *,
        provider_health: dict[CreativeProvider, HealthState] | None = None,
    ) -> tuple[ProviderAvailability, ...]:
        health_by_provider = provider_health or {}
        return tuple(
            self._provider_availability(
                provider,
                health_by_provider.get(provider, HealthState.HEALTHY),
            )
            for provider in CreativeProvider
        )

    def _provider_availability(
        self, provider: CreativeProvider, health: HealthState
    ) -> ProviderAvailability:
        assistant_enabled = provider in self.enabled_creative_providers
        renderer = _renderer_for_provider(provider)
        renderer_enabled = (
            renderer in self.enabled_image_renderers if renderer is not None else False
        )
        has_credentials = self.provider_has_credentials(provider)
        missing_variable_names = (
            () if has_credentials else (_PROVIDER_SECRET_VARIABLES[provider],)
        )
        is_healthy = health is HealthState.HEALTHY
        return ProviderAvailability(
            provider=provider,
            assistant_enabled=assistant_enabled,
            renderer_enabled=renderer_enabled,
            assistant_available=assistant_enabled and has_credentials and is_healthy,
            renderer_available=renderer_enabled and has_credentials and is_healthy,
            has_credentials=has_credentials,
            health=health,
            missing_variable_names=missing_variable_names,
        )

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


def _renderer_for_provider(provider: CreativeProvider) -> ImageRenderer | None:
    if provider is CreativeProvider.NANO_BANANA:
        return ImageRenderer.NANO_BANANA
    if provider is CreativeProvider.CHATGPT:
        return ImageRenderer.CHATGPT
    return None
