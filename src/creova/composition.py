from __future__ import annotations

from dataclasses import dataclass

from creova.application.access import AccessService
from creova.application.ports import (
    AccessGrantRepository,
    ImageGenerationProvider,
    PromptAssistant,
)
from creova.application.provider_registry import ProviderCapabilityRegistry
from creova.config import HealthState, ProviderAvailability, Settings, StartupDiagnostics
from creova.domain.enums import CreativeProvider, ImageRenderer
from creova.infrastructure.db import DurableAccessGrantRepository, create_async_session_factory
from creova.infrastructure.db.session import SqlAlchemyUnitOfWork
from creova.infrastructure.fakes import FakeImageGenerationProvider, FakePromptAssistant
from creova.infrastructure.gemini import (
    GeminiImageRenderer,
    GeminiPromptAssistant,
    create_gemini_client_from_api_key,
)
from creova.infrastructure.memory import BootstrapAccessGrantRepository


@dataclass(frozen=True, slots=True)
class AppContainer:
    settings: Settings
    access_service: AccessService
    startup_diagnostics: StartupDiagnostics
    provider_availability: tuple[ProviderAvailability, ...]
    provider_registry: ProviderCapabilityRegistry
    unit_of_work: SqlAlchemyUnitOfWork | None
    prompt_assistants: dict[CreativeProvider, PromptAssistant]
    image_renderers: dict[ImageRenderer, ImageGenerationProvider]


def build_container(
    settings: Settings | None = None,
    *,
    provider_health: dict[CreativeProvider, HealthState] | None = None,
) -> AppContainer:
    resolved_settings = settings or Settings()
    if resolved_settings.env == "test":
        repository: AccessGrantRepository = BootstrapAccessGrantRepository(
            admin_ids=resolved_settings.bootstrap_admin_ids,
            allowed_ids=resolved_settings.bootstrap_allowed_user_ids,
        )
        unit_of_work = None
    else:
        session_factory = create_async_session_factory(
            resolved_settings.database_url.get_secret_value()
        )
        repository = DurableAccessGrantRepository(session_factory)
        unit_of_work = SqlAlchemyUnitOfWork(session_factory)
    access_service = AccessService(repository)
    diagnostics = resolved_settings.startup_diagnostics(provider_health=provider_health)
    availability = diagnostics.provider_availability
    return AppContainer(
        settings=resolved_settings,
        access_service=access_service,
        startup_diagnostics=diagnostics,
        provider_availability=availability,
        provider_registry=ProviderCapabilityRegistry(availability),
        unit_of_work=unit_of_work,
        prompt_assistants=_build_prompt_assistants(resolved_settings, availability),
        image_renderers=_build_image_renderers(resolved_settings, availability),
    )


def _build_prompt_assistants(
    settings: Settings,
    availability: tuple[ProviderAvailability, ...],
) -> dict[CreativeProvider, PromptAssistant]:
    if settings.env != "test":
        assistants: dict[CreativeProvider, PromptAssistant] = {}
        if _enabled_provider(availability, CreativeProvider.NANO_BANANA):
            client = create_gemini_client_from_api_key(settings.google_api_key)
            model_id = settings.google_assistant_model or settings.google_image_model
            assistants[CreativeProvider.NANO_BANANA] = GeminiPromptAssistant(
                client=client,
                model_id=model_id,
            )
        return assistants
    return {
        item.provider: FakePromptAssistant(item.provider)
        for item in availability
        if item.assistant_enabled
    }


def _build_image_renderers(
    settings: Settings,
    availability: tuple[ProviderAvailability, ...],
) -> dict[ImageRenderer, ImageGenerationProvider]:
    if settings.env != "test":
        production_renderers: dict[ImageRenderer, ImageGenerationProvider] = {}
        if _enabled_renderer(availability, CreativeProvider.NANO_BANANA):
            client = create_gemini_client_from_api_key(settings.google_api_key)
            production_renderers[ImageRenderer.NANO_BANANA] = GeminiImageRenderer(
                client=client,
                model_id=settings.google_image_model,
            )
        return production_renderers
    test_renderers: dict[ImageRenderer, ImageGenerationProvider] = {}
    for item in availability:
        renderer = _renderer_for_provider(item.provider)
        if renderer is not None and item.renderer_enabled:
            test_renderers[renderer] = FakeImageGenerationProvider(renderer)
    return test_renderers


def _renderer_for_provider(provider: CreativeProvider) -> ImageRenderer | None:
    if provider is CreativeProvider.NANO_BANANA:
        return ImageRenderer.NANO_BANANA
    if provider is CreativeProvider.CHATGPT:
        return ImageRenderer.CHATGPT
    return None


def _enabled_provider(
    availability: tuple[ProviderAvailability, ...],
    provider: CreativeProvider,
) -> bool:
    return any(
        item.provider is provider and item.assistant_enabled and item.has_credentials
        for item in availability
    )


def _enabled_renderer(
    availability: tuple[ProviderAvailability, ...],
    provider: CreativeProvider,
) -> bool:
    return any(
        item.provider is provider and item.renderer_enabled and item.has_credentials
        for item in availability
    )
