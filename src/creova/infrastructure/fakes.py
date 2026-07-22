from __future__ import annotations

from dataclasses import dataclass

from creova.application.ports import BriefAssessment, ImageGenerationProvider, PromptAssistant
from creova.domain.enums import CreativeProvider, ImageRenderer
from creova.domain.models import CreativeBrief, GenerationSpec


@dataclass(frozen=True, slots=True)
class FakePromptAssistant(PromptAssistant):
    provider: CreativeProvider

    async def assess(
        self,
        *,
        original_prompt: str,
        brief: CreativeBrief,
        conversation_answers: tuple[str, ...],
        renderer: ImageRenderer | None,
    ) -> BriefAssessment:
        del original_prompt, brief, conversation_answers, renderer
        return BriefAssessment(
            brief_patch={},
            material_unknowns=(),
            next_question=None,
            answer_options=(),
            is_ready_for_review=True,
            safe_summary="Fake prompt assistant response",
            optimized_prompt="Fake optimized image prompt",
        )


@dataclass(frozen=True, slots=True)
class FakeImageGenerationProvider(ImageGenerationProvider):
    renderer: ImageRenderer

    async def generate(self, spec: GenerationSpec, idempotency_key: str) -> bytes:
        del spec, idempotency_key
        return b"fake-image-bytes"
