import pytest

from creova.config import Settings, TelegramMode
from creova.domain.enums import CreativeProvider, ImageRenderer


def test_parses_bootstrap_ids() -> None:
    settings = Settings(
        telegram_bot_token="fake-token",
        bootstrap_admin_ids="1, 2",
        bootstrap_allowed_user_ids="3",
    )
    assert settings.bootstrap_admin_ids == frozenset({1, 2})
    assert settings.bootstrap_allowed_user_ids == frozenset({3})


def test_default_mode_is_polling() -> None:
    settings = Settings(telegram_bot_token="fake-token")
    assert settings.telegram_mode is TelegramMode.POLLING


def test_parses_provider_sets() -> None:
    settings = Settings(
        telegram_bot_token="fake-token",
        enabled_creative_providers="nano_banana,claude",
        enabled_image_renderers="nano_banana",
    )
    assert settings.enabled_creative_providers == frozenset(
        {CreativeProvider.NANO_BANANA, CreativeProvider.CLAUDE}
    )
    assert settings.enabled_image_renderers == frozenset({ImageRenderer.NANO_BANANA})


def test_rejects_bot_username_with_at_sign() -> None:
    with pytest.raises(ValueError, match="must not include"):
        Settings(telegram_bot_token="fake-token", telegram_bot_username="@FeloCreova_bot")


def test_provider_credential_availability() -> None:
    settings = Settings(
        telegram_bot_token="fake-token",
        google_api_key="fake-google-key",
        anthropic_api_key="fake-anthropic-key",
    )
    assert settings.provider_has_credentials(CreativeProvider.NANO_BANANA)
    assert settings.provider_has_credentials(CreativeProvider.CLAUDE)
    assert not settings.provider_has_credentials(CreativeProvider.CHATGPT)
