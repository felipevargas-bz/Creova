from creova.composition import build_container
from creova.config import Settings
from creova.domain.enums import CreativeProvider, ImageRenderer
from creova.infrastructure.fakes import FakeImageGenerationProvider, FakePromptAssistant


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


def test_composition_does_not_wire_provider_fakes_outside_tests() -> None:
    container = build_container(
        Settings(
            env="local",
            telegram_bot_token="",
            enabled_creative_providers="nano_banana",
            enabled_image_renderers="nano_banana",
        )
    )

    assert container.prompt_assistants == {}
    assert container.image_renderers == {}
