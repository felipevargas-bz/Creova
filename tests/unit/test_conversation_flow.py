from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from creova.application.conversation_flow import (
    ConversationPolicy,
    CreativeConversationService,
)
from creova.application.ports import BriefAssessment
from creova.domain.enums import ConversationStage, CreativeProvider, ImageRenderer
from creova.domain.errors import InvalidStateTransition
from creova.domain.models import CreativeBrief
from creova.infrastructure.memory import InMemoryConversationRepository

NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


@dataclass(slots=True)
class FrozenClock:
    value: datetime = NOW

    def now(self) -> datetime:
        return self.value

    def advance(self, delta: timedelta) -> None:
        self.value += delta


@dataclass(slots=True)
class ScriptedPromptAssistant:
    provider: CreativeProvider
    responses: list[BriefAssessment]

    async def assess(
        self,
        *,
        original_prompt: str,
        brief: CreativeBrief,
        conversation_answers: tuple[str, ...],
        renderer: ImageRenderer | None,
    ) -> BriefAssessment:
        del original_prompt, brief, conversation_answers, renderer
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_service_runs_adaptive_brief_flow_with_fake_assistant() -> None:
    service = _service(
        [
            BriefAssessment(
                brief_patch={"subject": "coffee bag"},
                material_unknowns=("audience",),
                next_question="Who is the audience?",
                answer_options=("Consumers", "Retailers"),
                is_ready_for_review=False,
                safe_summary="Needs audience",
            ),
            BriefAssessment(
                brief_patch={"style": "editorial"},
                material_unknowns=(),
                next_question=None,
                answer_options=(),
                is_ready_for_review=True,
                safe_summary="Ready",
                optimized_prompt="Create an editorial coffee launch image.",
            ),
        ]
    )

    started = await service.start(owner_telegram_user_id=123, chat_id=456)
    selected = await service.select_assistant(
        started.conversation.id,
        draft_version=started.conversation.version,
        provider=CreativeProvider.NANO_BANANA,
    )
    asked = await service.submit_initial_prompt(
        selected.conversation.id,
        prompt="Create a coffee launch image",
    )

    assert asked.message_kind == "clarification_question"
    assert asked.conversation.original_prompt == "Create a coffee launch image"
    assert asked.conversation.active_question is not None

    reviewed = await service.answer_question(
        asked.conversation.id,
        answer="premium coffee buyers",
        field_name="audience",
    )

    assert reviewed.conversation.stage is ConversationStage.AWAITING_CONFIRMATION
    assert reviewed.conversation.brief.audience == "premium coffee buyers"
    assert reviewed.conversation.brief.subject == "coffee bag"
    assert reviewed.conversation.optimized_prompt == "Create an editorial coffee launch image."


@pytest.mark.asyncio
async def test_service_rejects_stale_callback_versions() -> None:
    service = _service([])
    started = await service.start(owner_telegram_user_id=123, chat_id=456)

    with pytest.raises(InvalidStateTransition, match="Stale"):
        await service.select_assistant(
            started.conversation.id,
            draft_version=started.conversation.version - 1,
            provider=CreativeProvider.CHATGPT,
        )


@pytest.mark.asyncio
async def test_service_supports_review_now_edit_start_over_and_cancel() -> None:
    service = _service(
        [
            BriefAssessment(
                brief_patch={"subject": "coffee bag"},
                material_unknowns=("style",),
                next_question="What style?",
                answer_options=(),
                is_ready_for_review=False,
                safe_summary="Needs style",
            ),
            BriefAssessment(
                brief_patch={},
                material_unknowns=(),
                next_question=None,
                answer_options=(),
                is_ready_for_review=True,
                safe_summary="Ready",
                optimized_prompt="Updated prompt",
            ),
        ]
    )
    asked = await _started_refining(service)

    reviewed = await service.review_now(
        asked.conversation.id,
        draft_version=asked.conversation.version,
    )
    assert reviewed.conversation.stage is ConversationStage.AWAITING_CONFIRMATION

    edited = await service.edit_details(
        reviewed.conversation.id,
        draft_version=reviewed.conversation.version,
        field_name="style",
        value="minimal",
    )
    assert edited.conversation.stage is ConversationStage.AWAITING_CONFIRMATION
    assert edited.conversation.brief.style == "minimal"

    restarted = await service.start_over(
        edited.conversation.id,
        draft_version=edited.conversation.version,
    )
    assert restarted.conversation.stage is ConversationStage.AWAITING_PROVIDER

    cancelled = await service.cancel(
        restarted.conversation.id,
        draft_version=restarted.conversation.version,
    )
    assert cancelled.conversation.stage is ConversationStage.CANCELLED


@pytest.mark.asyncio
async def test_service_supports_use_best_judgment_and_question_limit() -> None:
    service = _service(
        [
            BriefAssessment(
                brief_patch={},
                material_unknowns=("style",),
                next_question="What style?",
                answer_options=(),
                is_ready_for_review=False,
                safe_summary="Needs style",
            ),
            BriefAssessment(
                brief_patch={},
                material_unknowns=("lighting",),
                next_question="What lighting?",
                answer_options=(),
                is_ready_for_review=False,
                safe_summary="Would ask more",
                optimized_prompt="Best judgment prompt",
            ),
        ],
        max_questions=1,
    )
    asked = await _started_refining(service)

    reviewed = await service.use_best_judgment(
        asked.conversation.id,
        draft_version=asked.conversation.version,
    )

    assert reviewed.conversation.stage is ConversationStage.AWAITING_CONFIRMATION
    assert reviewed.conversation.question_count == 1
    assert reviewed.conversation.active_question is None


@pytest.mark.asyncio
async def test_service_requires_claude_renderer_handoff() -> None:
    service = _service(
        [
            BriefAssessment(
                brief_patch={"subject": "coffee bag"},
                material_unknowns=(),
                next_question=None,
                answer_options=(),
                is_ready_for_review=True,
                safe_summary="Ready",
                optimized_prompt="Claude assisted prompt",
            )
        ],
        provider=CreativeProvider.CLAUDE,
    )
    started = await service.start(owner_telegram_user_id=123, chat_id=456)
    selected = await service.select_assistant(
        started.conversation.id,
        draft_version=started.conversation.version,
        provider=CreativeProvider.CLAUDE,
    )
    handoff = await service.submit_initial_prompt(selected.conversation.id, prompt="Coffee launch")

    assert handoff.conversation.stage is ConversationStage.AWAITING_RENDERER
    confirmed = await service.select_renderer(
        handoff.conversation.id,
        draft_version=handoff.conversation.version,
        renderer=ImageRenderer.NANO_BANANA,
    )
    assert confirmed.conversation.stage is ConversationStage.AWAITING_CONFIRMATION


@pytest.mark.asyncio
async def test_service_expires_abandoned_conversation_safely() -> None:
    clock = FrozenClock()
    repository = InMemoryConversationRepository()
    service = _service([], repository=repository, clock=clock, ttl_minutes=5)
    started = await service.start(owner_telegram_user_id=123, chat_id=456)

    clock.advance(timedelta(minutes=6))

    with pytest.raises(InvalidStateTransition, match="expired"):
        await service.select_assistant(
            started.conversation.id,
            draft_version=started.conversation.version,
            provider=CreativeProvider.CHATGPT,
        )
    stored = await repository.get(started.conversation.id)
    assert stored is not None
    assert stored.stage is ConversationStage.EXPIRED


async def _started_refining(service: CreativeConversationService):
    started = await service.start(owner_telegram_user_id=123, chat_id=456)
    selected = await service.select_assistant(
        started.conversation.id,
        draft_version=started.conversation.version,
        provider=CreativeProvider.NANO_BANANA,
    )
    return await service.submit_initial_prompt(selected.conversation.id, prompt="Coffee launch")


def _service(
    responses: list[BriefAssessment],
    *,
    provider: CreativeProvider = CreativeProvider.NANO_BANANA,
    max_questions: int = 6,
    ttl_minutes: int = 60,
    repository: InMemoryConversationRepository | None = None,
    clock: FrozenClock | None = None,
) -> CreativeConversationService:
    return CreativeConversationService(
        repository=repository or InMemoryConversationRepository(),
        prompt_assistants={
            provider: ScriptedPromptAssistant(provider=provider, responses=responses),
            CreativeProvider.NANO_BANANA: ScriptedPromptAssistant(
                provider=CreativeProvider.NANO_BANANA,
                responses=responses,
            ),
        },
        policy=ConversationPolicy(
            ttl_minutes=ttl_minutes,
            max_clarification_questions=max_questions,
        ),
        clock=clock or FrozenClock(),
    )
