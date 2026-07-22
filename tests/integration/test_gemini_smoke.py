from __future__ import annotations

import os

import pytest
from pydantic import SecretStr

from creova.domain.enums import ContentKind, CreativeProvider
from creova.domain.models import GenerationSpec, ProviderSelection
from creova.infrastructure.gemini import GeminiImageRenderer, create_gemini_client_from_api_key

pytestmark = pytest.mark.real_provider


@pytest.mark.asyncio
async def test_real_gemini_text_to_image_smoke() -> None:
    if os.environ.get("CREOVA_REAL_PROVIDER_SMOKE") != "1":
        pytest.skip("Set CREOVA_REAL_PROVIDER_SMOKE=1 to run real Gemini smoke tests")
    api_key = os.environ.get("CREOVA_GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("CREOVA_GOOGLE_API_KEY is required for real Gemini smoke tests")
    model_id = os.environ.get("CREOVA_GOOGLE_IMAGE_MODEL", "gemini-3.1-flash-image")

    client = create_gemini_client_from_api_key(SecretStr(api_key))
    renderer = GeminiImageRenderer(client=client, model_id=model_id)
    spec = GenerationSpec(
        ContentKind.IMAGE,
        "Create a simple 1:1 icon of a blue coffee cup on a white background. No text.",
        {"aspect_ratio": "1:1", "quality": "standard"},
        provider=ProviderSelection(CreativeProvider.NANO_BANANA),
    )

    image = await renderer.generate(spec, idempotency_key="real-smoke")

    assert len(image) > 100
