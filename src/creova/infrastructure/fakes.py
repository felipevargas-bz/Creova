from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from creova.application.ports import BriefAssessment, ImageGenerationProvider, PromptAssistant
from creova.application.prompt_contracts import (
    PromptAssistantRequest,
    StructuredPromptAssistantAdapter,
)
from creova.domain.enums import CreativeProvider, ImageRenderer
from creova.domain.models import CreativeBrief, GenerationSpec


@dataclass(slots=True)
class FakeStructuredPromptClient:
    responses: list[Mapping[str, object]] = field(default_factory=list)
    requests: list[PromptAssistantRequest] = field(default_factory=list)

    async def complete_structured(
        self,
        request: PromptAssistantRequest,
    ) -> Mapping[str, object]:
        self.requests.append(request)
        if self.responses:
            return self.responses.pop(0)
        return {
            "brief_patch": {},
            "material_unknowns": (),
            "next_question": None,
            "answer_options": (),
            "is_ready_for_review": True,
            "safe_summary": "Fake prompt assistant response",
            "optimized_prompt": "Fake optimized image prompt",
        }


@dataclass(slots=True)
class FakePromptAssistant(PromptAssistant):
    provider: CreativeProvider
    client: FakeStructuredPromptClient = field(default_factory=FakeStructuredPromptClient)

    async def assess(
        self,
        *,
        original_prompt: str,
        brief: CreativeBrief,
        conversation_answers: tuple[str, ...],
        renderer: ImageRenderer | None,
    ) -> BriefAssessment:
        adapter = StructuredPromptAssistantAdapter(
            provider=self.provider,
            client=self.client,
        )
        return await adapter.assess(
            original_prompt=original_prompt,
            brief=brief,
            conversation_answers=conversation_answers,
            renderer=renderer,
        )


@dataclass(frozen=True, slots=True)
class FakeImageGenerationProvider(ImageGenerationProvider):
    renderer: ImageRenderer

    async def generate(self, spec: GenerationSpec, idempotency_key: str) -> bytes:
        del spec, idempotency_key
        return b"fake-image-bytes"
