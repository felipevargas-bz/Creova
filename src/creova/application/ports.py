from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Protocol

from creova.domain.enums import CreativeProvider, ImageRenderer
from creova.domain.models import AccessGrant, CreativeBrief, GenerationSpec


class Clock(Protocol):
    def now(self) -> object: ...


class AccessGrantRepository(Protocol):
    async def find_effective_by_telegram_user_id(
        self, telegram_user_id: int
    ) -> AccessGrant | None: ...


@dataclass(frozen=True, slots=True)
class BriefAssessment:
    brief_patch: Mapping[str, object]
    material_unknowns: tuple[str, ...]
    next_question: str | None
    answer_options: tuple[str, ...]
    is_ready_for_review: bool
    safe_summary: str
    optimized_prompt: str | None = None


class PromptAssistant(Protocol):
    provider: CreativeProvider

    async def assess(
        self,
        *,
        original_prompt: str,
        brief: CreativeBrief,
        conversation_answers: tuple[str, ...],
        renderer: ImageRenderer | None,
    ) -> BriefAssessment: ...


class ImageGenerationProvider(Protocol):
    renderer: ImageRenderer

    async def generate(self, spec: GenerationSpec, idempotency_key: str) -> bytes: ...


class ObjectStorage(Protocol):
    async def put(self, key: str, chunks: AsyncIterator[bytes], content_type: str) -> None: ...

    async def create_signed_get_url(self, key: str, ttl_seconds: int) -> str: ...

    async def delete(self, key: str) -> None: ...
