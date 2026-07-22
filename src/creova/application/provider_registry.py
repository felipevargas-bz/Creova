from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from creova.config import HealthState, ProviderAvailability
from creova.domain.enums import CreativeProvider, ImageRenderer


class AspectRatio(StrEnum):
    SQUARE = "1:1"
    PORTRAIT = "4:5"
    STORY = "9:16"
    LANDSCAPE = "16:9"


class QualityLevel(StrEnum):
    STANDARD = "standard"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class CreativeAssistantDescriptor:
    provider: CreativeProvider
    user_label: str
    default_renderer: ImageRenderer | None
    supports_reference_images: bool
    supported_aspect_ratios: tuple[AspectRatio, ...]
    supported_quality_levels: tuple[QualityLevel, ...]


@dataclass(frozen=True, slots=True)
class ImageRendererDescriptor:
    renderer: ImageRenderer
    user_label: str
    supports_reference_images: bool
    supported_aspect_ratios: tuple[AspectRatio, ...]
    supported_quality_levels: tuple[QualityLevel, ...]


@dataclass(frozen=True, slots=True)
class AssistantMenuItem:
    provider: CreativeProvider
    user_label: str
    available: bool
    health: HealthState
    default_renderer: ImageRenderer | None
    requires_renderer_handoff: bool


@dataclass(frozen=True, slots=True)
class RendererMenuItem:
    renderer: ImageRenderer
    user_label: str
    available: bool
    health: HealthState


ASSISTANT_DESCRIPTORS: dict[CreativeProvider, CreativeAssistantDescriptor] = {
    CreativeProvider.NANO_BANANA: CreativeAssistantDescriptor(
        provider=CreativeProvider.NANO_BANANA,
        user_label="Nano Banana",
        default_renderer=ImageRenderer.NANO_BANANA,
        supports_reference_images=True,
        supported_aspect_ratios=(
            AspectRatio.SQUARE,
            AspectRatio.PORTRAIT,
            AspectRatio.STORY,
            AspectRatio.LANDSCAPE,
        ),
        supported_quality_levels=(QualityLevel.STANDARD, QualityLevel.HIGH),
    ),
    CreativeProvider.CHATGPT: CreativeAssistantDescriptor(
        provider=CreativeProvider.CHATGPT,
        user_label="ChatGPT",
        default_renderer=ImageRenderer.CHATGPT,
        supports_reference_images=True,
        supported_aspect_ratios=(
            AspectRatio.SQUARE,
            AspectRatio.PORTRAIT,
            AspectRatio.STORY,
            AspectRatio.LANDSCAPE,
        ),
        supported_quality_levels=(QualityLevel.STANDARD, QualityLevel.HIGH),
    ),
    CreativeProvider.CLAUDE: CreativeAssistantDescriptor(
        provider=CreativeProvider.CLAUDE,
        user_label="Claude",
        default_renderer=None,
        supports_reference_images=True,
        supported_aspect_ratios=(
            AspectRatio.SQUARE,
            AspectRatio.PORTRAIT,
            AspectRatio.STORY,
            AspectRatio.LANDSCAPE,
        ),
        supported_quality_levels=(QualityLevel.STANDARD, QualityLevel.HIGH),
    ),
}

RENDERER_DESCRIPTORS: dict[ImageRenderer, ImageRendererDescriptor] = {
    ImageRenderer.NANO_BANANA: ImageRendererDescriptor(
        renderer=ImageRenderer.NANO_BANANA,
        user_label="Nano Banana",
        supports_reference_images=True,
        supported_aspect_ratios=(
            AspectRatio.SQUARE,
            AspectRatio.PORTRAIT,
            AspectRatio.STORY,
            AspectRatio.LANDSCAPE,
        ),
        supported_quality_levels=(QualityLevel.STANDARD, QualityLevel.HIGH),
    ),
    ImageRenderer.CHATGPT: ImageRendererDescriptor(
        renderer=ImageRenderer.CHATGPT,
        user_label="ChatGPT",
        supports_reference_images=True,
        supported_aspect_ratios=(
            AspectRatio.SQUARE,
            AspectRatio.PORTRAIT,
            AspectRatio.LANDSCAPE,
        ),
        supported_quality_levels=(QualityLevel.STANDARD, QualityLevel.HIGH),
    ),
}


class ProviderCapabilityRegistry:
    def __init__(self, availability: tuple[ProviderAvailability, ...]) -> None:
        self._availability = {item.provider: item for item in availability}

    @property
    def assistant_descriptors(self) -> tuple[CreativeAssistantDescriptor, ...]:
        return tuple(ASSISTANT_DESCRIPTORS[provider] for provider in CreativeProvider)

    @property
    def renderer_descriptors(self) -> tuple[ImageRendererDescriptor, ...]:
        return tuple(RENDERER_DESCRIPTORS[renderer] for renderer in ImageRenderer)

    def assistant_menu(self) -> tuple[AssistantMenuItem, ...]:
        return tuple(
            self._assistant_menu_item(ASSISTANT_DESCRIPTORS[provider])
            for provider in CreativeProvider
            if self._availability[provider].assistant_enabled
        )

    def renderer_menu(self) -> tuple[RendererMenuItem, ...]:
        items: list[RendererMenuItem] = []
        for renderer in ImageRenderer:
            provider = _provider_for_renderer(renderer)
            availability = self._availability[provider]
            if not availability.renderer_enabled:
                continue
            descriptor = RENDERER_DESCRIPTORS[renderer]
            items.append(
                RendererMenuItem(
                    renderer=renderer,
                    user_label=descriptor.user_label,
                    available=availability.renderer_available,
                    health=availability.health,
                )
            )
        return tuple(items)

    def require_renderer_handoff(self, provider: CreativeProvider) -> bool:
        return ASSISTANT_DESCRIPTORS[provider].default_renderer is None

    def default_renderer_for(self, provider: CreativeProvider) -> ImageRenderer | None:
        return ASSISTANT_DESCRIPTORS[provider].default_renderer

    def deserialize_renderer(self, value: str) -> ImageRenderer:
        return ImageRenderer(value)

    def _assistant_menu_item(
        self,
        descriptor: CreativeAssistantDescriptor,
    ) -> AssistantMenuItem:
        availability = self._availability[descriptor.provider]
        return AssistantMenuItem(
            provider=descriptor.provider,
            user_label=descriptor.user_label,
            available=availability.assistant_available,
            health=availability.health,
            default_renderer=descriptor.default_renderer,
            requires_renderer_handoff=descriptor.default_renderer is None,
        )


def _provider_for_renderer(renderer: ImageRenderer) -> CreativeProvider:
    if renderer is ImageRenderer.NANO_BANANA:
        return CreativeProvider.NANO_BANANA
    return CreativeProvider.CHATGPT
