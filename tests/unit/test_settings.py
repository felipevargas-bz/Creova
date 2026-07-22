import pytest

from creova.config import HealthState, Settings, TelegramMode
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
    with pytest.raises(ValueError, match="must be FeloCreova_bot"):
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


def test_does_not_require_bot_token_when_settings_load() -> None:
    settings = Settings(telegram_bot_token="")
    assert settings.telegram_bot_token.get_secret_value() == ""


def test_requires_bot_token_only_when_requested() -> None:
    settings = Settings(telegram_bot_token="")
    assert settings.missing_required_variable_names(require_bot_token=False) == ()
    assert settings.missing_required_variable_names(require_bot_token=True) == (
        "CREOVA_TELEGRAM_BOT_TOKEN",
    )
    with pytest.raises(RuntimeError, match="CREOVA_TELEGRAM_BOT_TOKEN"):
        settings.require_bot_token()


def test_rejects_disabled_default_renderer() -> None:
    with pytest.raises(ValueError, match="Default image renderer"):
        Settings(
            telegram_bot_token="fake-token",
            enabled_image_renderers="chatgpt",
            default_image_renderer="nano_banana",
        )


def test_provider_availability_uses_enabled_credentials_and_health() -> None:
    settings = Settings(
        telegram_bot_token="fake-token",
        enabled_creative_providers="nano_banana,chatgpt,claude",
        enabled_image_renderers="nano_banana,chatgpt",
        google_api_key="fake-google-key",
        openai_api_key="",
        anthropic_api_key="fake-anthropic-key",
    )

    availability = {item.provider: item for item in settings.provider_availability()}

    assert availability[CreativeProvider.NANO_BANANA].assistant_available is True
    assert availability[CreativeProvider.NANO_BANANA].renderer_available is True
    assert availability[CreativeProvider.CHATGPT].assistant_available is False
    assert availability[CreativeProvider.CHATGPT].renderer_available is False
    assert availability[CreativeProvider.CHATGPT].missing_variable_names == (
        "CREOVA_OPENAI_API_KEY",
    )
    assert availability[CreativeProvider.CLAUDE].assistant_available is True
    assert availability[CreativeProvider.CLAUDE].renderer_available is False


def test_provider_availability_respects_health() -> None:
    settings = Settings(
        telegram_bot_token="fake-token",
        google_api_key="fake-google-key",
    )

    availability = {
        item.provider: item
        for item in settings.provider_availability(
            provider_health={CreativeProvider.NANO_BANANA: HealthState.UNHEALTHY}
        )
    }

    assert availability[CreativeProvider.NANO_BANANA].has_credentials is True
    assert availability[CreativeProvider.NANO_BANANA].assistant_available is False
    assert availability[CreativeProvider.NANO_BANANA].renderer_available is False


def test_startup_diagnostics_names_variables_without_values() -> None:
    settings = Settings(
        telegram_bot_token="",
        google_api_key="fake-google-key",
        openai_api_key="",
        anthropic_api_key="",
    )

    diagnostics = settings.startup_diagnostics(require_bot_token=True)

    assert diagnostics.missing_required_variable_names == ("CREOVA_TELEGRAM_BOT_TOKEN",)
    assert "CREOVA_OPENAI_API_KEY" in diagnostics.missing_optional_variable_names
    assert "CREOVA_ANTHROPIC_API_KEY" in diagnostics.missing_optional_variable_names
    assert "fake-google-key" not in repr(diagnostics)
