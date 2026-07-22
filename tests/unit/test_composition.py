from creova.composition import build_container
from creova.config import Settings
from creova.domain.enums import CreativeProvider, ImageRenderer
from creova.infrastructure.fakes import FakeImageGenerationProvider, FakePromptAssistant
from creova.infrastructure.gemini import GeminiImageRenderer, GeminiPromptAssistant
from creova.infrastructure.openai import OpenAIImageRenderer, OpenAIPromptAssistant


def test_composition_wires_fakes_by_default_in_tests() -> None:
    container = build_container(
        Settings(
            env="test",
            telegram_bot_token="",
            enabled_creative_providers="nano_banana,chatgpt,claude",
            enabled_image_renderers="nano_banana,chatgpt",
        )
    )

    assert isinstance(
        container.prompt_assistants[CreativeProvider.NANO_BANANA],
        FakePromptAssistant,
    )
    assert isinstance(container.prompt_assistants[CreativeProvider.CHATGPT], FakePromptAssistant)
    assert isinstance(container.prompt_assistants[CreativeProvider.CLAUDE], FakePromptAssistant)
    assert isinstance(
        container.image_renderers[ImageRenderer.NANO_BANANA],
        FakeImageGenerationProvider,
    )
    assert isinstance(
        container.image_renderers[ImageRenderer.CHATGPT],
        FakeImageGenerationProvider,
    )
    assert container.provider_registry.require_renderer_handoff(CreativeProvider.CLAUDE)


def test_composition_does_not_wire_provider_fakes_outside_tests() -> None:
    container = build_container(
        Settings(
            env="local",
            telegram_bot_token="",
            enabled_creative_providers="nano_banana",
            enabled_image_renderers="nano_banana",
            google_api_key="",
        )
    )

    assert container.prompt_assistants == {}
    assert container.image_renderers == {}


def test_composition_wires_gemini_adapters_outside_tests_when_configured() -> None:
    container = build_container(
        Settings(
            env="local",
            telegram_bot_token="",
            enabled_creative_providers="nano_banana",
            enabled_image_renderers="nano_banana",
            google_api_key="fake-google-key",
        )
    )

    assert isinstance(
        container.prompt_assistants[CreativeProvider.NANO_BANANA],
        GeminiPromptAssistant,
    )
    assert isinstance(container.image_renderers[ImageRenderer.NANO_BANANA], GeminiImageRenderer)


def test_composition_wires_openai_adapters_outside_tests_when_configured() -> None:
    container = build_container(
        Settings(
            env="local",
            telegram_bot_token="",
            enabled_creative_providers="chatgpt",
            enabled_image_renderers="chatgpt",
            default_image_renderer="chatgpt",
            openai_api_key="fake-openai-key",
            openai_assistant_model="gpt-assistant",
            openai_image_model="gpt-image",
        )
    )

    assert isinstance(
        container.prompt_assistants[CreativeProvider.CHATGPT],
        OpenAIPromptAssistant,
    )
    assert isinstance(container.image_renderers[ImageRenderer.CHATGPT], OpenAIImageRenderer)


def test_composition_does_not_wire_openai_adapters_without_model_ids() -> None:
    container = build_container(
        Settings(
            env="local",
            telegram_bot_token="",
            enabled_creative_providers="chatgpt",
            enabled_image_renderers="chatgpt",
            default_image_renderer="chatgpt",
            openai_api_key="fake-openai-key",
            openai_assistant_model="",
            openai_image_model="",
        )
    )

    assert container.prompt_assistants == {}
    assert container.image_renderers == {}
