from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from creova.domain.enums import (
    AccessRole,
    AccessStatus,
    BriefProvenance,
    ContentKind,
    ConversationStage,
    CreativeProvider,
    ImageRenderer,
    JobStatus,
)
from creova.domain.errors import InvalidStateTransition


@dataclass(frozen=True, slots=True)
class AccessGrant:
    id: UUID
    telegram_user_id: int
    role: AccessRole
    status: AccessStatus
    valid_from: datetime
    valid_until: datetime | None = None
    limits: Mapping[str, int | float] = field(default_factory=dict)

    def is_effective(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        if self.status is not AccessStatus.ACTIVE:
            return False
        if current < self.valid_from:
            return False
        return self.valid_until is None or current < self.valid_until


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    assistant: CreativeProvider
    renderer: ImageRenderer | None = None

    def __post_init__(self) -> None:
        renderer = self.renderer
        if renderer is None and self.assistant is CreativeProvider.NANO_BANANA:
            object.__setattr__(self, "renderer", ImageRenderer.NANO_BANANA)
        elif renderer is None and self.assistant is CreativeProvider.CHATGPT:
            object.__setattr__(self, "renderer", ImageRenderer.CHATGPT)

    @property
    def is_ready_for_confirmation(self) -> bool:
        return self.renderer is not None


@dataclass(frozen=True, slots=True)
class CreativeBrief:
    purpose: str | None = None
    audience: str | None = None
    subject: str | None = None
    action: str | None = None
    environment: str | None = None
    composition: str | None = None
    style: str | None = None
    lighting: str | None = None
    palette: str | None = None
    viewpoint: str | None = None
    aspect_ratio: str | None = None
    required_text: str | None = None
    constraints: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    provenance: Mapping[str, BriefProvenance] = field(default_factory=dict)
    assistant_suggestions: Mapping[str, object] = field(default_factory=dict)

    def with_user_value(self, field_name: str, value: object) -> CreativeBrief:
        return self._with_value(field_name, value, BriefProvenance.USER)

    def with_assistant_patch(self, patch: Mapping[str, object]) -> CreativeBrief:
        brief = self
        for field_name, value in patch.items():
            if not _is_brief_field(field_name):
                continue
            if brief.provenance.get(field_name) is BriefProvenance.USER:
                brief = replace(
                    brief,
                    assistant_suggestions={**brief.assistant_suggestions, field_name: value},
                )
                continue
            current = getattr(brief, field_name)
            if _has_value(current):
                brief = replace(
                    brief,
                    assistant_suggestions={**brief.assistant_suggestions, field_name: value},
                )
                continue
            brief = brief._with_value(field_name, value, BriefProvenance.ASSISTANT)
        return brief

    def _with_value(
        self,
        field_name: str,
        value: object,
        provenance: BriefProvenance,
    ) -> CreativeBrief:
        if not _is_brief_field(field_name):
            raise ValueError(f"Unknown creative brief field: {field_name}")
        normalized = _normalize_brief_value(field_name, value)
        return cast(
            CreativeBrief,
            replace(
                cast(Any, self),
                **{
                    field_name: normalized,
                    "provenance": {**self.provenance, field_name: provenance},
                },
            ),
        )

    @property
    def explicit_user_fields(self) -> frozenset[str]:
        return frozenset(
            field_name
            for field_name, provenance in self.provenance.items()
            if provenance is BriefProvenance.USER
        )


@dataclass(frozen=True, slots=True)
class ActiveQuestion:
    text: str
    options: tuple[str, ...] = ()

    @property
    def normalized_text(self) -> str:
        return _normalize_question(self.text)


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    role: str
    text: str
    draft_version: int
    created_at: datetime
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ImageConversation:
    id: UUID
    owner_telegram_user_id: int
    chat_id: int
    stage: ConversationStage
    expires_at: datetime
    version: int = 1
    question_count: int = 0
    assistant_provider: CreativeProvider | None = None
    renderer_provider: ImageRenderer | None = None
    original_prompt: str | None = None
    optimized_prompt: str | None = None
    brief: CreativeBrief = field(default_factory=CreativeBrief)
    active_question: ActiveQuestion | None = None
    asked_questions: tuple[str, ...] = ()
    turns: tuple[ConversationTurn, ...] = ()

    @classmethod
    def start(
        cls,
        *,
        owner_telegram_user_id: int,
        chat_id: int,
        now: datetime,
        ttl_minutes: int,
        id: UUID | None = None,
    ) -> ImageConversation:
        return cls(
            id=id or uuid4(),
            owner_telegram_user_id=owner_telegram_user_id,
            chat_id=chat_id,
            stage=ConversationStage.AWAITING_PROVIDER,
            expires_at=_expires_at(now, ttl_minutes),
        )

    def ensure_not_stale(self, now: datetime) -> None:
        if now >= self.expires_at and self.stage not in _TERMINAL_CONVERSATION_STAGES:
            raise InvalidStateTransition("Conversation has expired")

    def apply_callback_version(self, draft_version: int) -> None:
        if draft_version != self.version:
            raise InvalidStateTransition("Stale draft version")

    def select_assistant(
        self,
        provider: CreativeProvider,
        *,
        now: datetime,
        ttl_minutes: int,
    ) -> ImageConversation:
        self._require_stage(ConversationStage.AWAITING_PROVIDER)
        renderer = None
        if provider is CreativeProvider.NANO_BANANA:
            renderer = ImageRenderer.NANO_BANANA
        elif provider is CreativeProvider.CHATGPT:
            renderer = ImageRenderer.CHATGPT
        return replace(
            self,
            stage=ConversationStage.COLLECTING_INITIAL_PROMPT,
            assistant_provider=provider,
            renderer_provider=renderer,
            version=self.version + 1,
            expires_at=_expires_at(now, ttl_minutes),
        )

    def submit_initial_prompt(
        self,
        prompt: str,
        *,
        now: datetime,
        ttl_minutes: int,
    ) -> ImageConversation:
        self._require_stage(ConversationStage.COLLECTING_INITIAL_PROMPT)
        normalized = prompt.strip()
        if not normalized:
            raise ValueError("Initial prompt cannot be empty")
        return replace(
            self,
            stage=ConversationStage.REFINING_BRIEF,
            original_prompt=normalized,
            version=self.version + 1,
            expires_at=_expires_at(now, ttl_minutes),
            turns=self._append_turn("user", normalized, now, {"kind": "original_prompt"}),
        )

    def apply_assessment(
        self,
        *,
        brief_patch: Mapping[str, object],
        next_question: str | None,
        answer_options: tuple[str, ...],
        is_ready_for_review: bool,
        optimized_prompt: str | None,
        max_questions: int,
        now: datetime,
        ttl_minutes: int,
    ) -> ImageConversation:
        self._require_stage(ConversationStage.REFINING_BRIEF)
        if self.original_prompt is None:
            raise InvalidStateTransition("Original prompt is required before assessment")
        if self.active_question is not None:
            raise InvalidStateTransition("Conversation already has an active question")

        brief = self.brief.with_assistant_patch(brief_patch)
        question = _normalize_optional_question(next_question)
        can_ask = (
            question is not None
            and self.question_count < max_questions
            and question not in self.asked_questions
            and not is_ready_for_review
        )
        if can_ask:
            assert question is not None
            assert next_question is not None
            active_question = ActiveQuestion(text=next_question.strip(), options=answer_options)
            return replace(
                self,
                brief=brief,
                active_question=active_question,
                asked_questions=(*self.asked_questions, question),
                question_count=self.question_count + 1,
                version=self.version + 1,
                expires_at=_expires_at(now, ttl_minutes),
                turns=self._append_turn(
                    "assistant",
                    active_question.text,
                    now,
                    {"kind": "clarification_question", "options": answer_options},
                ),
            )

        next_stage = (
            ConversationStage.AWAITING_RENDERER
            if self.assistant_provider is CreativeProvider.CLAUDE and self.renderer_provider is None
            else ConversationStage.AWAITING_CONFIRMATION
        )
        return replace(
            self,
            stage=next_stage,
            brief=brief,
            active_question=None,
            optimized_prompt=optimized_prompt or self.optimized_prompt,
            version=self.version + 1,
            expires_at=_expires_at(now, ttl_minutes),
        )

    def answer_question(
        self,
        answer: str,
        *,
        now: datetime,
        ttl_minutes: int,
        field_name: str | None = None,
    ) -> ImageConversation:
        self._require_stage(ConversationStage.REFINING_BRIEF)
        if self.active_question is None:
            raise InvalidStateTransition("No active question to answer")
        normalized = answer.strip()
        if not normalized:
            raise ValueError("Answer cannot be empty")
        brief = self.brief
        if field_name is not None:
            brief = brief.with_user_value(field_name, normalized)
        return replace(
            self,
            brief=brief,
            active_question=None,
            version=self.version + 1,
            expires_at=_expires_at(now, ttl_minutes),
            turns=self._append_turn(
                "user",
                normalized,
                now,
                {"kind": "clarification_answer", "question": self.active_question.text},
            ),
        )

    def use_best_judgment(
        self,
        *,
        now: datetime,
        ttl_minutes: int,
    ) -> ImageConversation:
        self._require_stage(ConversationStage.REFINING_BRIEF)
        if self.active_question is None:
            raise InvalidStateTransition("No active question to skip")
        return replace(
            self,
            active_question=None,
            version=self.version + 1,
            expires_at=_expires_at(now, ttl_minutes),
            turns=self._append_turn(
                "user",
                "Use your best judgment",
                now,
                {"kind": "use_best_judgment", "question": self.active_question.text},
            ),
        )

    def review_now(self, *, now: datetime, ttl_minutes: int) -> ImageConversation:
        if self.stage not in {
            ConversationStage.REFINING_BRIEF,
            ConversationStage.AWAITING_RENDERER,
            ConversationStage.AWAITING_CONFIRMATION,
        }:
            raise InvalidStateTransition(f"Cannot review from {self.stage}")
        next_stage = (
            ConversationStage.AWAITING_RENDERER
            if self.assistant_provider is CreativeProvider.CLAUDE and self.renderer_provider is None
            else ConversationStage.AWAITING_CONFIRMATION
        )
        return replace(
            self,
            stage=next_stage,
            active_question=None,
            version=self.version + 1,
            expires_at=_expires_at(now, ttl_minutes),
        )

    def select_renderer(
        self,
        renderer: ImageRenderer,
        *,
        now: datetime,
        ttl_minutes: int,
    ) -> ImageConversation:
        self._require_stage(ConversationStage.AWAITING_RENDERER)
        return replace(
            self,
            stage=ConversationStage.AWAITING_CONFIRMATION,
            renderer_provider=renderer,
            version=self.version + 1,
            expires_at=_expires_at(now, ttl_minutes),
        )

    def edit_details(
        self,
        field_name: str,
        value: object,
        *,
        now: datetime,
        ttl_minutes: int,
    ) -> ImageConversation:
        if self.stage not in {
            ConversationStage.REFINING_BRIEF,
            ConversationStage.AWAITING_RENDERER,
            ConversationStage.AWAITING_CONFIRMATION,
        }:
            raise InvalidStateTransition(f"Cannot edit details from {self.stage}")
        return replace(
            self,
            stage=ConversationStage.REFINING_BRIEF,
            brief=self.brief.with_user_value(field_name, value),
            active_question=None,
            optimized_prompt=None,
            version=self.version + 1,
            expires_at=_expires_at(now, ttl_minutes),
            turns=self._append_turn(
                "user",
                f"{field_name}: {value}",
                now,
                {"kind": "edit_details", "field": field_name},
            ),
        )

    def start_over(self, *, now: datetime, ttl_minutes: int) -> ImageConversation:
        return ImageConversation.start(
            owner_telegram_user_id=self.owner_telegram_user_id,
            chat_id=self.chat_id,
            now=now,
            ttl_minutes=ttl_minutes,
            id=self.id,
        )

    def cancel(self, *, now: datetime) -> ImageConversation:
        if self.stage in _TERMINAL_CONVERSATION_STAGES:
            return self
        return replace(
            self,
            stage=ConversationStage.CANCELLED,
            active_question=None,
            version=self.version + 1,
            turns=self._append_turn("user", "Cancel", now, {"kind": "cancel"}),
        )

    def expire_if_abandoned(self, now: datetime) -> ImageConversation:
        if now < self.expires_at or self.stage in _TERMINAL_CONVERSATION_STAGES:
            return self
        return replace(
            self,
            stage=ConversationStage.EXPIRED,
            active_question=None,
            version=self.version + 1,
        )

    def _require_stage(self, expected: ConversationStage) -> None:
        if self.stage is not expected:
            raise InvalidStateTransition(f"Expected {expected}, got {self.stage}")

    def _append_turn(
        self,
        role: str,
        text: str,
        now: datetime,
        metadata: Mapping[str, object],
    ) -> tuple[ConversationTurn, ...]:
        return (
            *self.turns,
            ConversationTurn(
                role=role,
                text=text,
                draft_version=self.version,
                created_at=now,
                metadata=metadata,
            ),
        )


@dataclass(frozen=True, slots=True)
class GenerationSpec:
    kind: ContentKind
    prompt: str
    parameters: Mapping[str, str | int | float | bool]
    provider: ProviderSelection = field(
        default_factory=lambda: ProviderSelection(CreativeProvider.NANO_BANANA)
    )
    original_prompt: str | None = None
    brief: CreativeBrief = field(default_factory=CreativeBrief)

    def __post_init__(self) -> None:
        normalized = self.prompt.strip()
        if not normalized:
            raise ValueError("Prompt cannot be empty")
        if len(normalized) > 8_000:
            raise ValueError("Prompt is too long")
        if not self.provider.is_ready_for_confirmation:
            raise ValueError("An image renderer is required before confirmation")
        object.__setattr__(self, "prompt", normalized)
        if self.original_prompt is None:
            object.__setattr__(self, "original_prompt", normalized)


_BRIEF_VALUE_FIELDS = frozenset(CreativeBrief.__dataclass_fields__) - frozenset(
    {"provenance", "assistant_suggestions"}
)
_BRIEF_SEQUENCE_FIELDS = frozenset({"constraints", "exclusions"})
_TERMINAL_CONVERSATION_STAGES = frozenset(
    {
        ConversationStage.QUEUED,
        ConversationStage.GENERATING,
        ConversationStage.COMPLETED,
        ConversationStage.FAILED,
        ConversationStage.CANCELLED,
        ConversationStage.EXPIRED,
    }
)


def _is_brief_field(field_name: str) -> bool:
    return field_name in _BRIEF_VALUE_FIELDS


def _normalize_brief_value(field_name: str, value: object) -> object:
    if field_name in _BRIEF_SEQUENCE_FIELDS:
        if isinstance(value, str):
            return (value.strip(),) if value.strip() else ()
        if isinstance(value, tuple):
            return tuple(str(item).strip() for item in value if str(item).strip())
        if isinstance(value, list):
            return tuple(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str):
        return value.strip() or None
    return value


def _has_value(value: object) -> bool:
    return value not in (None, "", (), [], {})


def _normalize_question(question: str) -> str:
    return " ".join(question.casefold().strip().split())


def _normalize_optional_question(question: str | None) -> str | None:
    if question is None:
        return None
    normalized = _normalize_question(question)
    return normalized or None


def _expires_at(now: datetime, ttl_minutes: int) -> datetime:
    from datetime import timedelta

    return now + timedelta(minutes=ttl_minutes)


_ALLOWED_JOB_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset(
        {JobStatus.LEASED, JobStatus.CANCEL_REQUESTED, JobStatus.FAILED, JobStatus.EXPIRED}
    ),
    JobStatus.LEASED: frozenset(
        {
            JobStatus.QUEUED,
            JobStatus.SUBMITTED,
            JobStatus.RUNNING,
            JobStatus.CANCEL_REQUESTED,
            JobStatus.FAILED,
        }
    ),
    JobStatus.SUBMITTED: frozenset(
        {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.CANCEL_REQUESTED, JobStatus.FAILED}
    ),
    JobStatus.RUNNING: frozenset(
        {
            JobStatus.QUEUED,
            JobStatus.SUCCEEDED,
            JobStatus.CANCEL_REQUESTED,
            JobStatus.FAILED,
        }
    ),
    JobStatus.CANCEL_REQUESTED: frozenset({JobStatus.CANCELLED, JobStatus.SUCCEEDED}),
    JobStatus.SUCCEEDED: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
    JobStatus.EXPIRED: frozenset(),
}


def ensure_job_transition(current: JobStatus, target: JobStatus) -> None:
    if target not in _ALLOWED_JOB_TRANSITIONS[current]:
        raise InvalidStateTransition(f"Cannot transition job from {current} to {target}")
