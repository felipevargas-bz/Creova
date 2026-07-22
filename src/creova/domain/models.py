from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping
from uuid import UUID

from creova.domain.enums import (
    AccessRole,
    AccessStatus,
    ContentKind,
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
