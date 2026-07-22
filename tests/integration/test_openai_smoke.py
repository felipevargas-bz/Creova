from __future__ import annotations

import os

import pytest
from pydantic import SecretStr

from creova.domain.enums import ContentKind, CreativeProvider
from creova.domain.models import GenerationSpec, ProviderSelection
from creova.infrastructure.openai import OpenAIImageRenderer, create_openai_client_from_api_key

pytestmark = pytest.mark.real_provider


@pytest.mark.asyncio
async def test_real_openai_text_to_image_smoke() -> None:
    if os.environ.get("CREOVA_REAL_PROVIDER_SMOKE_OPENAI") != "1":
        pytest.skip("Set CREOVA_REAL_PROVIDER_SMOKE_OPENAI=1 to run real OpenAI smoke tests")
    api_key = os.environ.get("CREOVA_OPENAI_API_KEY")
    if not api_key:
        pytest.skip("CREOVA_OPENAI_API_KEY is required for real OpenAI smoke tests")
    model_id = os.environ.get("CREOVA_OPENAI_IMAGE_MODEL")
    if not model_id:
        pytest.skip("CREOVA_OPENAI_IMAGE_MODEL is required for real OpenAI smoke tests")

    client = create_openai_client_from_api_key(SecretStr(api_key))
    renderer = OpenAIImageRenderer(client=client, model_id=model_id)
    spec = GenerationSpec(
        ContentKind.IMAGE,
        "Create a simple 1:1 icon of a blue coffee cup on a white background. No text.",
        {"aspect_ratio": "1:1", "quality": "low"},
        provider=ProviderSelection(CreativeProvider.CHATGPT),
    )

    image = await renderer.generate(spec, idempotency_key="real-openai-smoke")

    assert len(image) > 100
