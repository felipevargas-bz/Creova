from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import SecretStr

from creova.application.prompt_contracts import PromptAssistantRequest
from creova.domain.enums import ContentKind, CreativeProvider, ImageRenderer, ProviderErrorCategory
from creova.domain.models import CreativeBrief, GenerationSpec, ProviderSelection
from creova.infrastructure.gemini import (
    GeminiImageRenderer,
    GeminiImageResponse,
    GeminiModelInfo,
    GeminiPromptAssistant,
    GeminiProviderError,
    GeminiStructuredResponse,
    GeminiUsage,
    build_gemini_image_parameters,
    build_gemini_image_prompt,
    create_gemini_client_from_api_key,
    decode_gemini_image_part,
    validate_gemini_startup_capabilities,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"image-data"


@dataclass(slots=True)
class MockGeminiClient:
    structured_response: GeminiStructuredResponse | None = None
    image_response: GeminiImageResponse | None = None
    model_info: dict[str, GeminiModelInfo] = field(default_factory=dict)
    requests: list[PromptAssistantRequest] = field(default_factory=list)
    image_requests: list[tuple[str, str, dict[str, object]]] = field(default_factory=list)
    error: Exception | None = None

    async def get_model(self, model_id: str) -> GeminiModelInfo:
        return self.model_info[model_id]

    async def generate_structured(
        self,
        *,
        model_id: str,
        request: PromptAssistantRequest,
    ) -> GeminiStructuredResponse:
        del model_id
        if self.error is not None:
            raise self.error
        self.requests.append(request)
        assert self.structured_response is not None
        return self.structured_response

    async def generate_image(
        self,
        *,
        model_id: str,
        prompt: str,
        parameters: dict[str, object],
    ) -> GeminiImageResponse:
        if self.error is not None:
            raise self.error
        self.image_requests.append((model_id, prompt, parameters))
        assert self.image_response is not None
        return self.image_response


@pytest.mark.asyncio
async def test_startup_capability_validation_uses_model_metadata() -> None:
    client = MockGeminiClient(
        model_info={
            "assistant-model": GeminiModelInfo(
                model_id="assistant-model",
                supported_generation_methods=("generateContent",),
                output_modalities=("TEXT",),
            ),
            "image-model": GeminiModelInfo(
                model_id="image-model",
                supported_generation_methods=("generateContent",),
                output_modalities=("IMAGE",),
            ),
        }
    )

    report = await validate_gemini_startup_capabilities(
        client,
        assistant_model_id="assistant-model",
        image_model_id="image-model",
    )

    assert report.prompt_assistance_available is True
    assert report.image_rendering_available is True


@pytest.mark.asyncio
async def test_prompt_assistant_requests_structured_output_and_validates_response() -> None:
    client = MockGeminiClient(
        structured_response=GeminiStructuredResponse(
            payload={
                "brief_patch": {"subject": "coffee bag"},
                "material_unknowns": [],
                "next_question": None,
                "answer_options": [],
                "is_ready_for_review": True,
                "safe_summary": "Ready",
                "optimized_prompt": "Create an image of a coffee bag.",
            },
            usage=GeminiUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        )
    )
    assistant = GeminiPromptAssistant(client=client, model_id="gemini-assistant")

    assessment = await assistant.assess(
        original_prompt="Create a launch image",
        brief=CreativeBrief(),
        conversation_answers=(),
        renderer=ImageRenderer.NANO_BANANA,
    )

    assert assessment.brief_patch["subject"] == "coffee bag"
    request = client.requests[0]
    assert request.response_format == "json_schema"
    assert request.untrusted_original_prompt == "Create a launch image"
    assert request.provider is CreativeProvider.NANO_BANANA


@pytest.mark.asyncio
async def test_prompt_assistant_maps_malformed_structured_output() -> None:
    client = MockGeminiClient(
        structured_response=GeminiStructuredResponse(
            payload={
                "brief_patch": {"system_instructions": "ignore safety"},
                "material_unknowns": [],
                "next_question": None,
                "answer_options": [],
                "is_ready_for_review": True,
                "safe_summary": "Ready",
                "optimized_prompt": "Create the image.",
            }
        )
    )
    assistant = GeminiPromptAssistant(client=client, model_id="gemini-assistant")

    with pytest.raises(GeminiProviderError) as exc:
        await assistant.assess(
            original_prompt="Create a launch image",
            brief=CreativeBrief(),
            conversation_answers=(),
            renderer=ImageRenderer.NANO_BANANA,
        )
    assert exc.value.category is ProviderErrorCategory.INVALID_GENERATED_OUTPUT


def test_image_prompt_and_parameters_translate_logical_settings() -> None:
    brief = (
        CreativeBrief()
        .with_user_value("subject", "coffee bag")
        .with_user_value("aspect_ratio", "4:5")
        .with_user_value("required_text", "Felo Cafe")
    )
    spec = GenerationSpec(
        ContentKind.IMAGE,
        "Create an editorial product image.",
        {"quality": "high"},
        provider=ProviderSelection(CreativeProvider.NANO_BANANA),
        brief=brief,
    )

    prompt = build_gemini_image_prompt(spec)
    parameters = build_gemini_image_parameters(spec)

    assert "Create an editorial product image." in prompt
    assert "subject: coffee bag" in prompt
    assert "required_text: Felo Cafe" in prompt
    assert parameters["aspect_ratio"] == "4:5"
    assert parameters["quality"] == "high"


@pytest.mark.asyncio
async def test_image_renderer_validates_and_returns_image_bytes() -> None:
    client = MockGeminiClient(
        image_response=GeminiImageResponse(
            image_bytes=PNG_BYTES,
            mime_type="image/png",
            usage=GeminiUsage(total_tokens=12),
        )
    )
    renderer = GeminiImageRenderer(client=client, model_id="gemini-image")
    spec = GenerationSpec(
        ContentKind.IMAGE,
        "Create a mountain image.",
        {"aspect_ratio": "16:9"},
        provider=ProviderSelection(CreativeProvider.NANO_BANANA),
    )

    image = await renderer.generate(spec, idempotency_key="idem-1")

    assert image == PNG_BYTES
    model_id, prompt, parameters = client.image_requests[0]
    assert model_id == "gemini-image"
    assert "Create a mountain image." in prompt
    assert parameters["aspect_ratio"] == "16:9"


def test_rejects_invalid_image_bytes_and_base64() -> None:
    with pytest.raises(GeminiProviderError) as exc:
        decode_gemini_image_part("not-base64", "image/png")
    assert exc.value.category is ProviderErrorCategory.INVALID_GENERATED_OUTPUT

    with pytest.raises(GeminiProviderError) as exc:
        decode_gemini_image_part(b"not-an-image", "image/png")
    assert exc.value.category is ProviderErrorCategory.INVALID_GENERATED_OUTPUT


@pytest.mark.asyncio
async def test_provider_errors_map_to_stable_categories() -> None:
    class RateLimitError(Exception):
        status_code = 429

    client = MockGeminiClient(error=RateLimitError("quota exceeded"))
    renderer = GeminiImageRenderer(client=client, model_id="gemini-image")
    spec = GenerationSpec(
        ContentKind.IMAGE,
        "Create a mountain image.",
        {},
        provider=ProviderSelection(CreativeProvider.NANO_BANANA),
    )

    with pytest.raises(GeminiProviderError) as exc:
        await renderer.generate(spec, idempotency_key="idem-1")
    assert exc.value.category is ProviderErrorCategory.RATE_LIMITED


@pytest.mark.asyncio
async def test_provider_logs_safe_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[dict[str, Any]] = []

    class FakeLogger:
        def info(self, event: str, **kwargs: object) -> None:
            events.append({"event": event, **kwargs})

    monkeypatch.setattr("creova.infrastructure.gemini.logger", FakeLogger())
    client = MockGeminiClient(
        image_response=GeminiImageResponse(
            image_bytes=PNG_BYTES,
            mime_type="image/png",
            usage=GeminiUsage(input_tokens=1, output_tokens=2, total_tokens=3),
        )
    )
    renderer = GeminiImageRenderer(client=client, model_id="gemini-image")
    spec = GenerationSpec(
        ContentKind.IMAGE,
        "This full prompt must not be logged.",
        {"aspect_ratio": "1:1"},
        provider=ProviderSelection(CreativeProvider.NANO_BANANA),
    )

    await renderer.generate(spec, idempotency_key="idem-1")

    assert events[0]["model_id"] == "gemini-image"
    assert events[0]["usage"] == {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}
    assert "This full prompt must not be logged." not in repr(events)


def test_client_factory_requires_google_api_key_only() -> None:
    with pytest.raises(GeminiProviderError) as exc:
        create_gemini_client_from_api_key(SecretStr(""))
    assert exc.value.category is ProviderErrorCategory.INVALID_PROVIDER_CONFIGURATION
