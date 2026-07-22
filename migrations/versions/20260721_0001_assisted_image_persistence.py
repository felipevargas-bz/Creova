"""Add assisted image persistence model.

Revision ID: 20260721_0001
Revises:
Create Date: 2026-07-21 00:01:00.000000
"""
# ruff: noqa: E501

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260721_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

uuid = postgresql.UUID(as_uuid=True)
jsonb = postgresql.JSONB(astext_type=sa.Text())


def timestamps() -> tuple[sa.Column[sa.DateTime], sa.Column[sa.DateTime]]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "telegram_users",
        sa.Column("id", uuid, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_telegram_users")),
        sa.UniqueConstraint("telegram_user_id", name=op.f("uq_telegram_users_telegram_user_id")),
    )

    op.create_table(
        "access_grants",
        sa.Column("id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("limits", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by", uuid, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role in ('user', 'admin', 'operator')", name=op.f("ck_access_grants_role_valid")),
        sa.CheckConstraint("status in ('active', 'suspended', 'revoked', 'expired')", name=op.f("ck_access_grants_status_valid")),
        sa.CheckConstraint("valid_until is null or valid_until > valid_from", name=op.f("ck_access_grants_valid_window")),
        sa.ForeignKeyConstraint(["created_by"], ["telegram_users.id"], name=op.f("fk_access_grants_created_by_telegram_users")),
        sa.ForeignKeyConstraint(["user_id"], ["telegram_users.id"], ondelete="CASCADE", name=op.f("fk_access_grants_user_id_telegram_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_access_grants")),
    )
    op.create_index("ix_access_grants_effective", "access_grants", ["user_id", "status", "valid_from", "valid_until"])

    op.create_table(
        "image_conversations",
        sa.Column("id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=16), server_default="image", nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("assistant_provider", sa.String(length=32), nullable=True),
        sa.Column("renderer_provider", sa.String(length=32), nullable=True),
        sa.Column("original_prompt", sa.Text(), nullable=True),
        sa.Column("optimized_prompt", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("question_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        *timestamps(),
        sa.CheckConstraint("kind = 'image'", name=op.f("ck_image_conversations_kind_image_only")),
        sa.CheckConstraint("question_count >= 0", name=op.f("ck_image_conversations_question_count_nonnegative")),
        sa.CheckConstraint("assistant_provider in ('nano_banana', 'chatgpt', 'claude')", name=op.f("ck_image_conversations_assistant_provider_valid")),
        sa.CheckConstraint("renderer_provider is null or renderer_provider in ('nano_banana', 'chatgpt')", name=op.f("ck_image_conversations_renderer_provider_not_claude")),
        sa.ForeignKeyConstraint(["user_id"], ["telegram_users.id"], name=op.f("fk_image_conversations_user_id_telegram_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_image_conversations")),
    )
    op.create_index("ix_image_conversations_active", "image_conversations", ["user_id", "chat_id", "stage", "expires_at"])

    op.create_table(
        "generation_requests",
        sa.Column("id", uuid, nullable=False),
        sa.Column("short_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("conversation_id", uuid, nullable=True),
        sa.Column("kind", sa.String(length=16), server_default="image", nullable=False),
        sa.Column("original_prompt", sa.Text(), nullable=False),
        sa.Column("optimized_prompt", sa.Text(), nullable=False),
        sa.Column("prompt_hash", sa.String(length=128), nullable=False),
        sa.Column("parameters", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("brief_snapshot", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("assistant_provider", sa.String(length=32), nullable=False),
        sa.Column("renderer_provider", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("kind = 'image'", name=op.f("ck_generation_requests_kind_image_only")),
        sa.CheckConstraint("status in ('draft', 'confirmed', 'queued', 'processing', 'completed', 'failed', 'cancelled', 'expired')", name=op.f("ck_generation_requests_status_valid")),
        sa.CheckConstraint("assistant_provider in ('nano_banana', 'chatgpt', 'claude')", name=op.f("ck_generation_requests_assistant_provider_valid")),
        sa.CheckConstraint("renderer_provider in ('nano_banana', 'chatgpt')", name=op.f("ck_generation_requests_renderer_provider_not_claude")),
        sa.ForeignKeyConstraint(["conversation_id"], ["image_conversations.id"], name=op.f("fk_generation_requests_conversation_id_image_conversations")),
        sa.ForeignKeyConstraint(["user_id"], ["telegram_users.id"], name=op.f("fk_generation_requests_user_id_telegram_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generation_requests")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_generation_requests_idempotency_key")),
        sa.UniqueConstraint("short_id", name=op.f("uq_generation_requests_short_id")),
    )
    op.create_index("ix_generation_requests_status_created", "generation_requests", ["status", "created_at"])
    op.create_index("ix_generation_requests_user_created", "generation_requests", ["user_id", sa.text("created_at DESC")])

    op.create_table(
        "processed_telegram_updates",
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result_code", sa.String(length=64), nullable=True),
        sa.Column("request_id", uuid, nullable=True),
        sa.Column("last_error_code", sa.String(length=128), nullable=True),
        sa.CheckConstraint("status in ('received', 'processed', 'failed', 'ignored')", name=op.f("ck_processed_telegram_updates_status_valid")),
        sa.ForeignKeyConstraint(["request_id"], ["generation_requests.id"], name=op.f("fk_processed_telegram_updates_request_id_generation_requests")),
        sa.PrimaryKeyConstraint("update_id", name=op.f("pk_processed_telegram_updates")),
    )

    op.create_table(
        "conversation_turns",
        sa.Column("id", uuid, nullable=False),
        sa.Column("conversation_id", uuid, nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("safe_text", sa.Text(), nullable=False),
        sa.Column("metadata_json", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role in ('user', 'assistant', 'system')", name=op.f("ck_conversation_turns_role_valid")),
        sa.CheckConstraint("turn_index >= 0", name=op.f("ck_conversation_turns_turn_index_nonnegative")),
        sa.ForeignKeyConstraint(["conversation_id"], ["image_conversations.id"], ondelete="CASCADE", name=op.f("fk_conversation_turns_conversation_id_image_conversations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversation_turns")),
        sa.UniqueConstraint("conversation_id", "turn_index", name="uq_conversation_turn_order"),
    )

    op.create_table(
        "creative_briefs",
        sa.Column("id", uuid, nullable=False),
        sa.Column("conversation_id", uuid, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("brief_json", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("readiness_score", sa.Numeric(5, 4), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["conversation_id"], ["image_conversations.id"], ondelete="CASCADE", name=op.f("fk_creative_briefs_conversation_id_image_conversations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creative_briefs")),
        sa.UniqueConstraint("conversation_id", "version", name="uq_creative_briefs_version"),
    )

    op.create_table(
        "creative_brief_fields",
        sa.Column("id", uuid, nullable=False),
        sa.Column("brief_id", uuid, nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("field_value", jsonb, nullable=False),
        sa.Column("provenance", sa.String(length=32), nullable=False),
        sa.Column("source_turn_id", uuid, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("provenance in ('user', 'assistant', 'inferred', 'default')", name=op.f("ck_creative_brief_fields_provenance_valid")),
        sa.ForeignKeyConstraint(["brief_id"], ["creative_briefs.id"], ondelete="CASCADE", name=op.f("fk_creative_brief_fields_brief_id_creative_briefs")),
        sa.ForeignKeyConstraint(["source_turn_id"], ["conversation_turns.id"], name=op.f("fk_creative_brief_fields_source_turn_id_conversation_turns")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creative_brief_fields")),
        sa.UniqueConstraint("brief_id", "field_name", name="uq_creative_brief_fields_name"),
    )

    op.create_table(
        "generation_request_versions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("request_id", uuid, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("original_prompt", sa.Text(), nullable=False),
        sa.Column("optimized_prompt", sa.Text(), nullable=False),
        sa.Column("brief_snapshot", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("parameters", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["generation_requests.id"], ondelete="CASCADE", name=op.f("fk_generation_request_versions_request_id_generation_requests")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generation_request_versions")),
        sa.UniqueConstraint("request_id", "version", name="uq_generation_request_versions_version"),
    )

    op.create_table(
        "confirmation_records",
        sa.Column("id", uuid, nullable=False),
        sa.Column("request_id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("conversation_id", uuid, nullable=True),
        sa.Column("conversation_version", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["image_conversations.id"], name=op.f("fk_confirmation_records_conversation_id_image_conversations")),
        sa.ForeignKeyConstraint(["request_id"], ["generation_requests.id"], name=op.f("fk_confirmation_records_request_id_generation_requests")),
        sa.ForeignKeyConstraint(["user_id"], ["telegram_users.id"], name=op.f("fk_confirmation_records_user_id_telegram_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_confirmation_records")),
        sa.UniqueConstraint("idempotency_key", name="uq_confirmation_records_idempotency_key"),
        sa.UniqueConstraint("request_id", name="uq_confirmation_records_request"),
    )

    op.create_table(
        "generation_jobs",
        sa.Column("id", uuid, nullable=False),
        sa.Column("request_id", uuid, nullable=False),
        sa.Column("job_type", sa.String(length=32), server_default="image_generation", nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.SmallInteger(), server_default="100", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=128), nullable=True),
        sa.Column("last_error_safe_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("attempt_count >= 0", name=op.f("ck_generation_jobs_attempt_count_nonnegative")),
        sa.CheckConstraint("max_attempts > 0", name=op.f("ck_generation_jobs_max_attempts_positive")),
        sa.CheckConstraint("(lease_owner is null and lease_expires_at is null) or (lease_owner is not null and lease_expires_at is not null)", name=op.f("ck_generation_jobs_lease_complete")),
        sa.CheckConstraint("status in ('queued', 'leased', 'submitted', 'running', 'succeeded', 'failed', 'cancel_requested', 'cancelled', 'expired')", name=op.f("ck_generation_jobs_status_valid")),
        sa.ForeignKeyConstraint(["request_id"], ["generation_requests.id"], name=op.f("fk_generation_jobs_request_id_generation_requests")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generation_jobs")),
        sa.UniqueConstraint("request_id", name=op.f("uq_generation_jobs_request_id")),
    )
    op.create_index("ix_generation_jobs_runnable", "generation_jobs", ["status", "next_attempt_at", "priority", "created_at"])

    op.create_table(
        "job_leases",
        sa.Column("id", uuid, nullable=False),
        sa.Column("job_id", uuid, nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("expires_at > acquired_at", name=op.f("ck_job_leases_lease_window")),
        sa.ForeignKeyConstraint(["job_id"], ["generation_jobs.id"], name=op.f("fk_job_leases_job_id_generation_jobs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_leases")),
    )

    op.create_table(
        "provider_operations",
        sa.Column("id", uuid, nullable=False),
        sa.Column("job_id", uuid, nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_operation_id", sa.String(length=256), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(18, 8), server_default="0", nullable=False),
        sa.Column("actual_cost_usd", sa.Numeric(18, 8), nullable=True),
        sa.Column("metadata_json", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("provider in ('nano_banana', 'chatgpt')", name=op.f("ck_provider_operations_provider_renderer_valid")),
        sa.CheckConstraint("status in ('created', 'submitted', 'running', 'succeeded', 'failed', 'cancelled', 'unknown')", name=op.f("ck_provider_operations_status_valid")),
        sa.ForeignKeyConstraint(["job_id"], ["generation_jobs.id"], name=op.f("fk_provider_operations_job_id_generation_jobs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_operations")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_provider_operations_idempotency_key")),
        sa.UniqueConstraint("provider", "provider_operation_id", name="uq_provider_operations_external_id"),
    )

    op.create_table(
        "provider_attempts",
        sa.Column("id", uuid, nullable=False),
        sa.Column("operation_id", uuid, nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("safe_error_code", sa.String(length=128), nullable=True),
        sa.Column("safe_error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempt_number > 0", name=op.f("ck_provider_attempts_attempt_number_positive")),
        sa.ForeignKeyConstraint(["operation_id"], ["provider_operations.id"], name=op.f("fk_provider_attempts_operation_id_provider_operations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_attempts")),
        sa.UniqueConstraint("operation_id", "attempt_number", name="uq_provider_attempts_number"),
    )

    op.create_table(
        "generated_assets",
        sa.Column("id", uuid, nullable=False),
        sa.Column("request_id", uuid, nullable=False),
        sa.Column("provider_operation_id", uuid, nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("size_bytes > 0", name=op.f("ck_generated_assets_size_bytes_positive")),
        sa.CheckConstraint("status in ('available', 'deleted', 'quarantined')", name=op.f("ck_generated_assets_status_valid")),
        sa.ForeignKeyConstraint(["provider_operation_id"], ["provider_operations.id"], name=op.f("fk_generated_assets_provider_operation_id_provider_operations")),
        sa.ForeignKeyConstraint(["request_id"], ["generation_requests.id"], name=op.f("fk_generated_assets_request_id_generation_requests")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generated_assets")),
        sa.UniqueConstraint("request_id", "sha256", name="uq_generated_assets_request_sha256"),
        sa.UniqueConstraint("storage_key", name=op.f("uq_generated_assets_storage_key")),
    )

    op.create_table(
        "usage_reservations",
        sa.Column("id", uuid, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("request_id", uuid, nullable=True),
        sa.Column("amount_usd", sa.Numeric(18, 8), nullable=False),
        sa.Column("units", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount_usd >= 0", name=op.f("ck_usage_reservations_amount_nonnegative")),
        sa.ForeignKeyConstraint(["request_id"], ["generation_requests.id"], name=op.f("fk_usage_reservations_request_id_generation_requests")),
        sa.ForeignKeyConstraint(["user_id"], ["telegram_users.id"], name=op.f("fk_usage_reservations_user_id_telegram_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_reservations")),
        sa.UniqueConstraint("idempotency_key", name="uq_usage_reservations_idempotency_key"),
    )

    op.create_table(
        "usage_settlements",
        sa.Column("id", uuid, nullable=False),
        sa.Column("reservation_id", uuid, nullable=True),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("request_id", uuid, nullable=True),
        sa.Column("amount_usd", sa.Numeric(18, 8), nullable=False),
        sa.Column("settlement_type", sa.String(length=32), nullable=False),
        sa.Column("units", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount_usd >= 0", name=op.f("ck_usage_settlements_amount_nonnegative")),
        sa.ForeignKeyConstraint(["request_id"], ["generation_requests.id"], name=op.f("fk_usage_settlements_request_id_generation_requests")),
        sa.ForeignKeyConstraint(["reservation_id"], ["usage_reservations.id"], name=op.f("fk_usage_settlements_reservation_id_usage_reservations")),
        sa.ForeignKeyConstraint(["user_id"], ["telegram_users.id"], name=op.f("fk_usage_settlements_user_id_telegram_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_settlements")),
        sa.UniqueConstraint("idempotency_key", name="uq_usage_settlements_idempotency_key"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", uuid, nullable=False),
        sa.Column("request_id", uuid, nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error_code", sa.String(length=128), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("attempt_count >= 0", name=op.f("ck_notifications_attempt_count_nonnegative")),
        sa.ForeignKeyConstraint(["request_id"], ["generation_requests.id"], name=op.f("fk_notifications_request_id_generation_requests")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
        sa.UniqueConstraint("idempotency_key", name="uq_notifications_idempotency_key"),
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", uuid, nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("aggregate_type", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", uuid, nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("payload", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error_code", sa.String(length=128), nullable=True),
        sa.CheckConstraint("attempt_count >= 0", name=op.f("ck_outbox_events_attempt_count_nonnegative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
        sa.UniqueConstraint("idempotency_key", name="uq_outbox_events_idempotency_key"),
    )
    op.create_index("ix_outbox_events_unpublished", "outbox_events", ["published_at", "next_attempt_at"])

    op.create_table(
        "audit_events",
        sa.Column("id", uuid, nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor_user_id", uuid, nullable=True),
        sa.Column("subject_type", sa.String(length=128), nullable=False),
        sa.Column("subject_id", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["telegram_users.id"], name=op.f("fk_audit_events_actor_user_id_telegram_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )


def downgrade() -> None:
    for table_name in (
        "audit_events",
        "outbox_events",
        "notifications",
        "usage_settlements",
        "usage_reservations",
        "generated_assets",
        "provider_attempts",
        "provider_operations",
        "job_leases",
        "generation_jobs",
        "confirmation_records",
        "generation_request_versions",
        "creative_brief_fields",
        "creative_briefs",
        "conversation_turns",
        "processed_telegram_updates",
        "generation_requests",
        "image_conversations",
        "access_grants",
        "telegram_users",
    ):
        op.drop_table(table_name)
