import pytest

from creova.application.provider_registry import (
    ASSISTANT_DESCRIPTORS,
    RENDERER_DESCRIPTORS,
    AspectRatio,
    ProviderCapabilityRegistry,
    QualityLevel,
)
from creova.config import HealthState, Settings
from creova.domain.enums import CreativeProvider, ImageRenderer


def registry_from_settings(
    settings: Settings,
    health: dict[CreativeProvider, HealthState] | None = None,
) -> ProviderCapabilityRegistry:
    return ProviderCapabilityRegistry(settings.provider_availability(provider_health=health))


def test_assistant_descriptors_are_exhaustive() -> None:
    assert set(ASSISTANT_DESCRIPTORS) == set(CreativeProvider)
    assert {descriptor.user_label for descriptor in ASSISTANT_DESCRIPTORS.values()} == {
        "Nano Banana",
        "ChatGPT",
        "Claude",
    }


def test_renderer_descriptors_are_exhaustive_and_exclude_claude() -> None:
    assert set(RENDERER_DESCRIPTORS) == set(ImageRenderer)
    assert "claude" not in {renderer.value for renderer in RENDERER_DESCRIPTORS}


def test_labels_are_separate_from_model_ids_and_sdk_names() -> None:
    for descriptor in [*ASSISTANT_DESCRIPTORS.values(), *RENDERER_DESCRIPTORS.values()]:
        assert descriptor.user_label
        assert "." not in descriptor.user_label
        assert "model" not in descriptor.user_label.lower()
        assert "sdk" not in descriptor.user_label.lower()


def test_capabilities_capture_logical_formats_and_quality() -> None:
    for descriptor in [*ASSISTANT_DESCRIPTORS.values(), *RENDERER_DESCRIPTORS.values()]:
        assert AspectRatio.SQUARE in descriptor.supported_aspect_ratios
        assert QualityLevel.STANDARD in descriptor.supported_quality_levels
        assert isinstance(descriptor.supports_reference_images, bool)


def test_assistant_menu_uses_enabled_credentials_and_health() -> None:
    settings = Settings(
        telegram_bot_token="fake-token",
        enabled_creative_providers="nano_banana,chatgpt,claude",
        enabled_image_renderers="nano_banana,chatgpt",
        google_api_key="fake-google-key",
        openai_api_key="",
        anthropic_api_key="fake-anthropic-key",
    )
    registry = registry_from_settings(settings)

    menu = {item.provider: item for item in registry.assistant_menu()}

    assert menu[CreativeProvider.NANO_BANANA].available is True
    assert menu[CreativeProvider.CHATGPT].available is False
    assert menu[CreativeProvider.CLAUDE].available is True


def test_renderer_menu_uses_enabled_credentials_and_health() -> None:
    settings = Settings(
        telegram_bot_token="fake-token",
        enabled_creative_providers="nano_banana,chatgpt,claude",
        enabled_image_renderers="nano_banana,chatgpt",
        google_api_key="fake-google-key",
        openai_api_key="fake-openai-key",
        anthropic_api_key="fake-anthropic-key",
    )
    registry = registry_from_settings(
        settings,
        health={CreativeProvider.CHATGPT: HealthState.UNHEALTHY},
    )

    menu = {item.renderer: item for item in registry.renderer_menu()}

    assert menu[ImageRenderer.NANO_BANANA].available is True
    assert menu[ImageRenderer.CHATGPT].available is False
    assert menu[ImageRenderer.CHATGPT].health is HealthState.UNHEALTHY


def test_matching_assistants_default_to_matching_renderers() -> None:
    registry = registry_from_settings(
        Settings(
            telegram_bot_token="fake-token",
            google_api_key="fake-google-key",
            openai_api_key="fake-openai-key",
            anthropic_api_key="fake-anthropic-key",
        )
    )

    assert registry.default_renderer_for(CreativeProvider.NANO_BANANA) is ImageRenderer.NANO_BANANA
    assert registry.default_renderer_for(CreativeProvider.CHATGPT) is ImageRenderer.CHATGPT
    assert registry.require_renderer_handoff(CreativeProvider.NANO_BANANA) is False
    assert registry.require_renderer_handoff(CreativeProvider.CHATGPT) is False


def test_claude_requires_renderer_handoff() -> None:
    registry = registry_from_settings(
        Settings(
            telegram_bot_token="fake-token",
            anthropic_api_key="fake-anthropic-key",
        )
    )

    assert registry.default_renderer_for(CreativeProvider.CLAUDE) is None
    assert registry.require_renderer_handoff(CreativeProvider.CLAUDE) is True
    menu = {item.provider: item for item in registry.assistant_menu()}
    assert menu[CreativeProvider.CLAUDE].requires_renderer_handoff is True


def test_claude_cannot_deserialize_as_renderer() -> None:
    registry = registry_from_settings(Settings(telegram_bot_token="fake-token"))

    with pytest.raises(ValueError):
        registry.deserialize_renderer("claude")
