from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from creova.application.ports import PromptAssistant
from creova.domain.enums import ConversationStage, CreativeProvider, ImageRenderer
from creova.domain.errors import InvalidStateTransition
from creova.domain.models import ImageConversation


class ConversationRepository(Protocol):
    async def add(self, conversation: ImageConversation) -> None: ...

    async def get(self, conversation_id: UUID) -> ImageConversation | None: ...

    async def save(self, conversation: ImageConversation) -> None: ...

    async def get_active(
        self,
        *,
        owner_telegram_user_id: int,
        chat_id: int,
    ) -> ImageConversation | None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ConversationPolicy:
    ttl_minutes: int
    max_clarification_questions: int


@dataclass(frozen=True, slots=True)
class ConversationResult:
    conversation: ImageConversation
    message_kind: str


class CreativeConversationService:
    def __init__(
        self,
        *,
        repository: ConversationRepository,
        prompt_assistants: Mapping[CreativeProvider, PromptAssistant],
        policy: ConversationPolicy,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._prompt_assistants = dict(prompt_assistants)
        self._policy = policy
        self._clock = clock or SystemClock()

    async def start(
        self,
        *,
        owner_telegram_user_id: int,
        chat_id: int,
    ) -> ConversationResult:
        now = self._clock.now()
        active = await self._repository.get_active(
            owner_telegram_user_id=owner_telegram_user_id,
            chat_id=chat_id,
        )
        if active is not None:
            expired = active.expire_if_abandoned(now)
            if expired.stage is ConversationStage.EXPIRED:
                await self._repository.save(expired)
            elif active.stage not in _TERMINAL_STAGES:
                return ConversationResult(active, "active_conversation_exists")

        conversation = ImageConversation.start(
            owner_telegram_user_id=owner_telegram_user_id,
            chat_id=chat_id,
            now=now,
            ttl_minutes=self._policy.ttl_minutes,
        )
        await self._repository.add(conversation)
        return ConversationResult(conversation, "awaiting_provider")

    async def select_assistant(
        self,
        conversation_id: UUID,
        *,
        draft_version: int,
        provider: CreativeProvider,
    ) -> ConversationResult:
        conversation = await self._load_current(conversation_id, draft_version)
        updated = conversation.select_assistant(
            provider,
            now=self._clock.now(),
            ttl_minutes=self._policy.ttl_minutes,
        )
        await self._repository.save(updated)
        return ConversationResult(updated, "collecting_initial_prompt")

    async def submit_initial_prompt(
        self,
        conversation_id: UUID,
        *,
        prompt: str,
    ) -> ConversationResult:
        conversation = await self._load_current(conversation_id)
        updated = conversation.submit_initial_prompt(
            prompt,
            now=self._clock.now(),
            ttl_minutes=self._policy.ttl_minutes,
        )
        updated = await self._assess(updated)
        await self._repository.save(updated)
        return ConversationResult(updated, _message_for_stage(updated.stage))

    async def answer_question(
        self,
        conversation_id: UUID,
        *,
        answer: str,
        field_name: str | None = None,
    ) -> ConversationResult:
        conversation = await self._load_current(conversation_id)
        updated = conversation.answer_question(
            answer,
            field_name=field_name,
            now=self._clock.now(),
            ttl_minutes=self._policy.ttl_minutes,
        )
        updated = await self._assess(updated)
        await self._repository.save(updated)
        return ConversationResult(updated, _message_for_stage(updated.stage))

    async def use_best_judgment(
        self,
        conversation_id: UUID,
        *,
        draft_version: int,
    ) -> ConversationResult:
        conversation = await self._load_current(conversation_id, draft_version)
        updated = conversation.use_best_judgment(
            now=self._clock.now(),
            ttl_minutes=self._policy.ttl_minutes,
        )
        updated = await self._assess(updated)
        await self._repository.save(updated)
        return ConversationResult(updated, _message_for_stage(updated.stage))

    async def review_now(
        self,
        conversation_id: UUID,
        *,
        draft_version: int,
    ) -> ConversationResult:
        conversation = await self._load_current(conversation_id, draft_version)
        updated = conversation.review_now(
            now=self._clock.now(),
            ttl_minutes=self._policy.ttl_minutes,
        )
        await self._repository.save(updated)
        return ConversationResult(updated, _message_for_stage(updated.stage))

    async def select_renderer(
        self,
        conversation_id: UUID,
        *,
        draft_version: int,
        renderer: ImageRenderer,
    ) -> ConversationResult:
        conversation = await self._load_current(conversation_id, draft_version)
        updated = conversation.select_renderer(
            renderer,
            now=self._clock.now(),
            ttl_minutes=self._policy.ttl_minutes,
        )
        await self._repository.save(updated)
        return ConversationResult(updated, "awaiting_confirmation")

    async def edit_details(
        self,
        conversation_id: UUID,
        *,
        draft_version: int,
        field_name: str,
        value: object,
    ) -> ConversationResult:
        conversation = await self._load_current(conversation_id, draft_version)
        updated = conversation.edit_details(
            field_name,
            value,
            now=self._clock.now(),
            ttl_minutes=self._policy.ttl_minutes,
        )
        updated = await self._assess(updated)
        await self._repository.save(updated)
        return ConversationResult(updated, _message_for_stage(updated.stage))

    async def start_over(
        self,
        conversation_id: UUID,
        *,
        draft_version: int,
    ) -> ConversationResult:
        conversation = await self._load_current(conversation_id, draft_version)
        updated = conversation.start_over(
            now=self._clock.now(),
            ttl_minutes=self._policy.ttl_minutes,
        )
        await self._repository.save(updated)
        return ConversationResult(updated, "awaiting_provider")

    async def cancel(
        self,
        conversation_id: UUID,
        *,
        draft_version: int,
    ) -> ConversationResult:
        conversation = await self._load_current(conversation_id, draft_version)
        updated = conversation.cancel(now=self._clock.now())
        await self._repository.save(updated)
        return ConversationResult(updated, "cancelled")

    async def expire_abandoned(self, conversation_id: UUID) -> ConversationResult:
        conversation = await self._load_current(conversation_id)
        updated = conversation.expire_if_abandoned(self._clock.now())
        await self._repository.save(updated)
        return ConversationResult(updated, _message_for_stage(updated.stage))

    async def _assess(self, conversation: ImageConversation) -> ImageConversation:
        if conversation.assistant_provider is None:
            raise InvalidStateTransition("Assistant provider is required")
        if conversation.original_prompt is None:
            raise InvalidStateTransition("Original prompt is required")
        assistant = self._prompt_assistants[conversation.assistant_provider]
        assessment = await assistant.assess(
            original_prompt=conversation.original_prompt,
            brief=conversation.brief,
            conversation_answers=tuple(
                turn.text for turn in conversation.turns if turn.role == "user"
            ),
            renderer=conversation.renderer_provider,
        )
        return conversation.apply_assessment(
            brief_patch=assessment.brief_patch,
            next_question=assessment.next_question,
            answer_options=assessment.answer_options,
            is_ready_for_review=assessment.is_ready_for_review,
            optimized_prompt=assessment.optimized_prompt,
            max_questions=self._policy.max_clarification_questions,
            now=self._clock.now(),
            ttl_minutes=self._policy.ttl_minutes,
        )

    async def _load_current(
        self,
        conversation_id: UUID,
        draft_version: int | None = None,
    ) -> ImageConversation:
        conversation = await self._repository.get(conversation_id)
        if conversation is None:
            raise InvalidStateTransition("Conversation not found")
        expired = conversation.expire_if_abandoned(self._clock.now())
        if expired.stage is ConversationStage.EXPIRED:
            await self._repository.save(expired)
            raise InvalidStateTransition("Conversation has expired")
        if draft_version is not None:
            expired.apply_callback_version(draft_version)
        return expired


_TERMINAL_STAGES = frozenset(
    {
        ConversationStage.QUEUED,
        ConversationStage.GENERATING,
        ConversationStage.COMPLETED,
        ConversationStage.FAILED,
        ConversationStage.CANCELLED,
        ConversationStage.EXPIRED,
    }
)


def _message_for_stage(stage: ConversationStage) -> str:
    if stage is ConversationStage.REFINING_BRIEF:
        return "clarification_question"
    if stage is ConversationStage.AWAITING_RENDERER:
        return "awaiting_renderer"
    if stage is ConversationStage.AWAITING_CONFIRMATION:
        return "awaiting_confirmation"
    if stage is ConversationStage.EXPIRED:
        return "expired"
    if stage is ConversationStage.CANCELLED:
        return "cancelled"
    return stage.value
