from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=naming_convention)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TelegramUser(TimestampMixin, Base):
    __tablename__ = "telegram_users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    telegram_username: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str | None] = mapped_column(Text)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    access_grants: Mapped[list[AccessGrant]] = relationship(
        back_populates="user",
        foreign_keys="AccessGrant.user_id",
    )


class AccessGrant(Base):
    __tablename__ = "access_grants"
    __table_args__ = (
        CheckConstraint("role in ('user', 'admin', 'operator')", name="role_valid"),
        CheckConstraint(
            "status in ('active', 'suspended', 'revoked', 'expired')",
            name="status_valid",
        ),
        CheckConstraint("valid_until is null or valid_until > valid_from", name="valid_window"),
        Index("ix_access_grants_effective", "user_id", "status", "valid_from", "valid_until"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    limits: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("telegram_users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[TelegramUser] = relationship(
        back_populates="access_grants",
        foreign_keys=[user_id],
    )


class ProcessedTelegramUpdate(Base):
    __tablename__ = "processed_telegram_updates"
    __table_args__ = (
        CheckConstraint(
            "status in ('received', 'processed', 'failed', 'ignored')",
            name="status_valid",
        ),
    )

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payload_hash: Mapped[str | None] = mapped_column(String(128))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    result_code: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[UUID | None] = mapped_column(ForeignKey("generation_requests.id"))
    last_error_code: Mapped[str | None] = mapped_column(String(128))


class ImageConversation(TimestampMixin, Base):
    __tablename__ = "image_conversations"
    __table_args__ = (
        CheckConstraint("kind = 'image'", name="kind_image_only"),
        CheckConstraint("question_count >= 0", name="question_count_nonnegative"),
        CheckConstraint(
            "assistant_provider in ('nano_banana', 'chatgpt', 'claude')",
            name="assistant_provider_valid",
        ),
        CheckConstraint(
            "renderer_provider is null or renderer_provider in ('nano_banana', 'chatgpt')",
            name="renderer_provider_not_claude",
        ),
        Index(
            "ix_image_conversations_active",
            "user_id",
            "chat_id",
            "stage",
            "expires_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("telegram_users.id"), nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="image")
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    assistant_provider: Mapped[str | None] = mapped_column(String(32))
    renderer_provider: Mapped[str | None] = mapped_column(String(32))
    original_prompt: Mapped[str | None] = mapped_column(Text)
    optimized_prompt: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"
    __table_args__ = (
        CheckConstraint("turn_index >= 0", name="turn_index_nonnegative"),
        CheckConstraint("role in ('user', 'assistant', 'system')", name="role_valid"),
        UniqueConstraint("conversation_id", "turn_index", name="uq_conversation_turn_order"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("image_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    safe_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CreativeBrief(TimestampMixin, Base):
    __tablename__ = "creative_briefs"
    __table_args__ = (
        UniqueConstraint("conversation_id", "version", name="uq_creative_briefs_version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("image_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    brief_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    readiness_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))


class CreativeBriefField(Base):
    __tablename__ = "creative_brief_fields"
    __table_args__ = (
        CheckConstraint(
            "provenance in ('user', 'assistant', 'inferred', 'default')",
            name="provenance_valid",
        ),
        UniqueConstraint("brief_id", "field_name", name="uq_creative_brief_fields_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    brief_id: Mapped[UUID] = mapped_column(
        ForeignKey("creative_briefs.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    field_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False)
    source_turn_id: Mapped[UUID | None] = mapped_column(ForeignKey("conversation_turns.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class GenerationRequest(TimestampMixin, Base):
    __tablename__ = "generation_requests"
    __table_args__ = (
        CheckConstraint("kind = 'image'", name="kind_image_only"),
        CheckConstraint(
            "status in ("
            "'draft', 'confirmed', 'queued', 'processing', "
            "'completed', 'failed', 'cancelled', 'expired'"
            ")",
            name="status_valid",
        ),
        CheckConstraint(
            "assistant_provider in ('nano_banana', 'chatgpt', 'claude')",
            name="assistant_provider_valid",
        ),
        CheckConstraint(
            "renderer_provider in ('nano_banana', 'chatgpt')",
            name="renderer_provider_not_claude",
        ),
        Index("ix_generation_requests_user_created", "user_id", text("created_at DESC")),
        Index("ix_generation_requests_status_created", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    short_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("telegram_users.id"), nullable=False)
    conversation_id: Mapped[UUID | None] = mapped_column(ForeignKey("image_conversations.id"))
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="image")
    original_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    optimized_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    brief_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    assistant_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    renderer_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_message_id: Mapped[int | None] = mapped_column(BigInteger)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GenerationRequestVersion(Base):
    __tablename__ = "generation_request_versions"
    __table_args__ = (
        UniqueConstraint("request_id", "version", name="uq_generation_request_versions_version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("generation_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    original_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    optimized_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    brief_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ConfirmationRecord(Base):
    __tablename__ = "confirmation_records"
    __table_args__ = (
        UniqueConstraint("request_id", name="uq_confirmation_records_request"),
        UniqueConstraint("idempotency_key", name="uq_confirmation_records_idempotency_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("generation_requests.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("telegram_users.id"), nullable=False)
    conversation_id: Mapped[UUID | None] = mapped_column(ForeignKey("image_conversations.id"))
    conversation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class GenerationJob(TimestampMixin, Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        CheckConstraint(
            "status in ("
            "'queued', 'leased', 'submitted', 'running', 'succeeded', "
            "'failed', 'cancel_requested', 'cancelled', 'expired'"
            ")",
            name="status_valid",
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count_nonnegative"),
        CheckConstraint("max_attempts > 0", name="max_attempts_positive"),
        CheckConstraint(
            "(lease_owner is null and lease_expires_at is null) or "
            "(lease_owner is not null and lease_expires_at is not null)",
            name="lease_complete",
        ),
        Index(
            "ix_generation_jobs_runnable",
            "status",
            "next_attempt_at",
            "priority",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("generation_requests.id"),
        nullable=False,
        unique=True,
    )
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, default="image_generation")
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=100)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(128))
    last_error_safe_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobLease(Base):
    __tablename__ = "job_leases"
    __table_args__ = (CheckConstraint("expires_at > acquired_at", name="lease_window"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("generation_jobs.id"), nullable=False)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProviderOperation(TimestampMixin, Base):
    __tablename__ = "provider_operations"
    __table_args__ = (
        CheckConstraint("provider in ('nano_banana', 'chatgpt')", name="provider_renderer_valid"),
        CheckConstraint(
            "status in ("
            "'created', 'submitted', 'running', 'succeeded', "
            "'failed', 'cancelled', 'unknown'"
            ")",
            name="status_valid",
        ),
        UniqueConstraint(
            "provider",
            "provider_operation_id",
            name="uq_provider_operations_external_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("generation_jobs.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_operation_id: Mapped[str | None] = mapped_column(String(256))
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(18, 8),
        nullable=False,
        default=Decimal("0"),
    )
    actual_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProviderAttempt(Base):
    __tablename__ = "provider_attempts"
    __table_args__ = (
        CheckConstraint("attempt_number > 0", name="attempt_number_positive"),
        UniqueConstraint("operation_id", "attempt_number", name="uq_provider_attempts_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    operation_id: Mapped[UUID] = mapped_column(ForeignKey("provider_operations.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    safe_error_code: Mapped[str | None] = mapped_column(String(128))
    safe_error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GeneratedAsset(TimestampMixin, Base):
    __tablename__ = "generated_assets"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="size_bytes_positive"),
        CheckConstraint("status in ('available', 'deleted', 'quarantined')", name="status_valid"),
        UniqueConstraint("request_id", "sha256", name="uq_generated_assets_request_sha256"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("generation_requests.id"), nullable=False)
    provider_operation_id: Mapped[UUID | None] = mapped_column(ForeignKey("provider_operations.id"))
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsageReservation(Base):
    __tablename__ = "usage_reservations"
    __table_args__ = (
        CheckConstraint("amount_usd >= 0", name="amount_nonnegative"),
        UniqueConstraint("idempotency_key", name="uq_usage_reservations_idempotency_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("telegram_users.id"), nullable=False)
    request_id: Mapped[UUID | None] = mapped_column(ForeignKey("generation_requests.id"))
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    units: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsageSettlement(Base):
    __tablename__ = "usage_settlements"
    __table_args__ = (
        CheckConstraint("amount_usd >= 0", name="amount_nonnegative"),
        UniqueConstraint("idempotency_key", name="uq_usage_settlements_idempotency_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    reservation_id: Mapped[UUID | None] = mapped_column(ForeignKey("usage_reservations.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("telegram_users.id"), nullable=False)
    request_id: Mapped[UUID | None] = mapped_column(ForeignKey("generation_requests.id"))
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    settlement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    units: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("attempt_count >= 0", name="attempt_count_nonnegative"),
        UniqueConstraint("idempotency_key", name="uq_notifications_idempotency_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID | None] = mapped_column(ForeignKey("generation_requests.id"))
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(128))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint("attempt_count >= 0", name="attempt_count_nonnegative"),
        UniqueConstraint("idempotency_key", name="uq_outbox_events_idempotency_key"),
        Index("ix_outbox_events_unpublished", "published_at", "next_attempt_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(128), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(128))


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("telegram_users.id"))
    subject_type: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
