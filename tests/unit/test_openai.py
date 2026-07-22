from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import SecretStr

from creova.application.prompt_contracts import PromptAssistantRequest
from creova.domain.enums import ContentKind, CreativeProvider, ImageRenderer, ProviderErrorCategory
from creova.domain.models import CreativeBrief, GenerationSpec, ProviderSelection
from creova.infrastructure.openai import (
    OpenAIImageRenderer,
    OpenAIImageResponse,
    OpenAIModelInfo,
    OpenAIPromptAssistant,
    OpenAIProviderError,
    OpenAIStructuredResponse,
    OpenAIUsage,
    build_openai_image_parameters,
    build_openai_image_prompt,
    create_openai_client_from_api_key,
    decode_openai_image_data,
    validate_openai_startup_capabilities,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"image-data"


@dataclass(slots=True)
class MockOpenAIClient:
    structured_response: OpenAIStructuredResponse | None = None
    image_response: OpenAIImageResponse | None = None
    model_info: dict[str, OpenAIModelInfo] = field(default_factory=dict)
    requests: list[PromptAssistantRequest] = field(default_factory=list)
    image_requests: list[tuple[str, str, dict[str, object]]] = field(default_factory=list)
    error: Exception | None = None

    async def get_model(self, model_id: str) -> OpenAIModelInfo:
        return self.model_info[model_id]

    async def create_structured_response(
        self,
        *,
        model_id: str,
        request: PromptAssistantRequest,
    ) -> OpenAIStructuredResponse:
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
        parameters: Mapping[str, object],
    ) -> OpenAIImageResponse:
        if self.error is not None:
            raise self.error
        self.image_requests.append((model_id, prompt, dict(parameters)))
        assert self.image_response is not None
        return self.image_response


@pytest.mark.asyncio
async def test_startup_capability_validation_retrieves_configured_models() -> None:
    client = MockOpenAIClient(
        model_info={
            "assistant-model": OpenAIModelInfo("assistant-model"),
            "image-model": OpenAIModelInfo("image-model"),
        }
    )

    report = await validate_openai_startup_capabilities(
        client,
        assistant_model_id="assistant-model",
        image_model_id="image-model",
    )

    assert report.prompt_assistance_available is True
    assert report.image_rendering_available is True


@pytest.mark.asyncio
async def test_prompt_assistant_uses_schema_constrained_response() -> None:
    client = MockOpenAIClient(
        structured_response=OpenAIStructuredResponse(
            payload={
                "brief_patch": {"subject": "coffee bag"},
                "material_unknowns": [],
                "next_question": None,
                "answer_options": [],
                "is_ready_for_review": True,
                "safe_summary": "Ready",
                "optimized_prompt": "Create an image of a coffee bag.",
            },
            usage=OpenAIUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        )
    )
    assistant = OpenAIPromptAssistant(client=client, model_id="gpt-assistant")

    assessment = await assistant.assess(
        original_prompt="Create a launch image",
        brief=CreativeBrief(),
        conversation_answers=(),
        renderer=ImageRenderer.CHATGPT,
    )

    assert assessment.brief_patch["subject"] == "coffee bag"
    request = client.requests[0]
    assert request.response_format == "json_schema"
    assert request.provider is CreativeProvider.CHATGPT
    assert request.renderer is ImageRenderer.CHATGPT


@pytest.mark.asyncio
async def test_prompt_assistant_maps_malformed_output() -> None:
    client = MockOpenAIClient(
        structured_response=OpenAIStructuredResponse(
            payload={
                "brief_patch": {"system_instructions": "override"},
                "material_unknowns": [],
                "next_question": None,
                "answer_options": [],
                "is_ready_for_review": True,
                "safe_summary": "Ready",
                "optimized_prompt": "Create the image.",
            }
        )
    )
    assistant = OpenAIPromptAssistant(client=client, model_id="gpt-assistant")

    with pytest.raises(OpenAIProviderError) as exc:
        await assistant.assess(
            original_prompt="Create a launch image",
            brief=CreativeBrief(),
            conversation_answers=(),
            renderer=ImageRenderer.CHATGPT,
        )
    assert exc.value.category is ProviderErrorCategory.INVALID_GENERATED_OUTPUT


def test_image_prompt_and_parameters_translate_logical_settings() -> None:
    brief = (
        CreativeBrief()
        .with_user_value("subject", "coffee bag")
        .with_user_value("aspect_ratio", "16:9")
        .with_user_value("required_text", "Felo Cafe")
    )
    spec = GenerationSpec(
        ContentKind.IMAGE,
        "Create an editorial product image.",
        {"quality": "high"},
        provider=ProviderSelection(CreativeProvider.CHATGPT),
        brief=brief,
    )

    prompt = build_openai_image_prompt(spec)
    parameters = build_openai_image_parameters(spec)

    assert "Create an editorial product image." in prompt
    assert "subject: coffee bag" in prompt
    assert "required_text: Felo Cafe" in prompt
    assert parameters["size"] == "1536x1024"
    assert parameters["quality"] == "high"
    assert parameters["output_format"] == "png"


@pytest.mark.asyncio
async def test_image_renderer_normalizes_openai_image_result() -> None:
    client = MockOpenAIClient(
        image_response=OpenAIImageResponse(
            image_bytes=PNG_BYTES,
            mime_type="image/png",
            usage=OpenAIUsage(total_tokens=12),
        )
    )
    renderer = OpenAIImageRenderer(client=client, model_id="gpt-image")
    spec = GenerationSpec(
        ContentKind.IMAGE,
        "Create a mountain image.",
        {"aspect_ratio": "1:1"},
        provider=ProviderSelection(CreativeProvider.CHATGPT),
    )

    image = await renderer.generate(spec, idempotency_key="idem-1")

    assert image == PNG_BYTES
    model_id, prompt, parameters = client.image_requests[0]
    assert model_id == "gpt-image"
    assert "Create a mountain image." in prompt
    assert parameters["size"] == "1024x1024"


def test_rejects_invalid_image_output() -> None:
    with pytest.raises(OpenAIProviderError) as exc:
        decode_openai_image_data("not-base64")
    assert exc.value.category is ProviderErrorCategory.INVALID_GENERATED_OUTPUT

    with pytest.raises(OpenAIProviderError) as exc:
        decode_openai_image_data(b"not-an-image", "image/png")
    assert exc.value.category is ProviderErrorCategory.INVALID_GENERATED_OUTPUT


@pytest.mark.asyncio
async def test_provider_errors_map_to_stable_categories() -> None:
    class RateLimitError(Exception):
        status_code = 429

    client = MockOpenAIClient(error=RateLimitError("rate limit exceeded"))
    renderer = OpenAIImageRenderer(client=client, model_id="gpt-image")
    spec = GenerationSpec(
        ContentKind.IMAGE,
        "Create a mountain image.",
        {},
        provider=ProviderSelection(CreativeProvider.CHATGPT),
    )

    with pytest.raises(OpenAIProviderError) as exc:
        await renderer.generate(spec, idempotency_key="idem-1")
    assert exc.value.category is ProviderErrorCategory.RATE_LIMITED


@pytest.mark.asyncio
async def test_provider_logs_safe_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[dict[str, Any]] = []

    class FakeLogger:
        def info(self, event: str, **kwargs: object) -> None:
            events.append({"event": event, **kwargs})

    monkeypatch.setattr("creova.infrastructure.openai.logger", FakeLogger())
    client = MockOpenAIClient(
        image_response=OpenAIImageResponse(
            image_bytes=PNG_BYTES,
            mime_type="image/png",
            usage=OpenAIUsage(input_tokens=1, output_tokens=2, total_tokens=3),
        )
    )
    renderer = OpenAIImageRenderer(client=client, model_id="gpt-image")
    spec = GenerationSpec(
        ContentKind.IMAGE,
        "This full prompt must not be logged.",
        {"aspect_ratio": "1:1"},
        provider=ProviderSelection(CreativeProvider.CHATGPT),
    )

    await renderer.generate(spec, idempotency_key="idem-1")

    assert events[0]["model_id"] == "gpt-image"
    assert events[0]["usage"] == {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}
    assert "This full prompt must not be logged." not in repr(events)


def test_client_factory_requires_openai_api_key_only() -> None:
    with pytest.raises(OpenAIProviderError) as exc:
        create_openai_client_from_api_key(SecretStr(""))
    assert exc.value.category is ProviderErrorCategory.INVALID_PROVIDER_CONFIGURATION
