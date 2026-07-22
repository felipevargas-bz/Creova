from pathlib import Path

from sqlalchemy import BigInteger, CheckConstraint, Index, UniqueConstraint

from creova.infrastructure.db.models import Base, GenerationRequest, ImageConversation


def test_metadata_contains_required_tables() -> None:
    expected_tables = {
        "access_grants",
        "audit_events",
        "confirmation_records",
        "conversation_turns",
        "creative_brief_fields",
        "creative_briefs",
        "generated_assets",
        "generation_jobs",
        "generation_request_versions",
        "generation_requests",
        "image_conversations",
        "job_leases",
        "notifications",
        "outbox_events",
        "processed_telegram_updates",
        "provider_attempts",
        "provider_operations",
        "telegram_users",
        "usage_reservations",
        "usage_settlements",
    }

    assert expected_tables.issubset(Base.metadata.tables)


def test_telegram_ids_use_bigint() -> None:
    users = Base.metadata.tables["telegram_users"]
    updates = Base.metadata.tables["processed_telegram_updates"]

    assert isinstance(users.c.telegram_user_id.type, BigInteger)
    assert isinstance(updates.c.update_id.type, BigInteger)


def test_renderer_constraints_exclude_claude() -> None:
    for table in (ImageConversation.__table__, GenerationRequest.__table__):
        constraints = {
            constraint.name: str(constraint.sqltext)
            for constraint in table.constraints
            if isinstance(constraint, CheckConstraint)
        }

        renderer_constraint = next(
            sql
            for name, sql in constraints.items()
            if name is not None and name.endswith("renderer_provider_not_claude")
        )
        assert "'nano_banana'" in renderer_constraint
        assert "'chatgpt'" in renderer_constraint
        assert "'claude'" not in renderer_constraint


def test_request_preserves_original_and_optimized_prompts_separately() -> None:
    columns = GenerationRequest.__table__.c

    assert "original_prompt" in columns
    assert "optimized_prompt" in columns
    assert columns.original_prompt is not columns.optimized_prompt


def test_idempotency_keys_are_unique() -> None:
    tables = Base.metadata.tables
    table_names = {
        "confirmation_records",
        "generation_requests",
        "notifications",
        "outbox_events",
        "provider_operations",
        "usage_reservations",
        "usage_settlements",
    }

    for table_name in table_names:
        table = tables[table_name]
        unique_columns = {
            column.name
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
            for column in constraint.columns
            if len(constraint.columns) == 1
        }
        assert "idempotency_key" in unique_columns


def test_active_conversation_and_runnable_job_indexes_exist() -> None:
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for table in Base.metadata.tables.values()
        for index in table.indexes
        if isinstance(index, Index)
    }

    assert indexes["ix_image_conversations_active"] == (
        "user_id",
        "chat_id",
        "stage",
        "expires_at",
    )
    assert indexes["ix_generation_jobs_runnable"] == (
        "status",
        "next_attempt_at",
        "priority",
        "created_at",
    )


def test_alembic_migration_contains_renderer_constraint_and_all_tables() -> None:
    migration_path = (
        Path(__file__).parents[2]
        / "migrations"
        / "versions"
        / "20260721_0001_assisted_image_persistence.py"
    )
    migration = migration_path.read_text(encoding="utf-8")

    assert "renderer_provider_not_claude" in migration
    assert "renderer_provider in ('nano_banana', 'chatgpt')" in migration
    for table_name in Base.metadata.tables:
        assert f'"{table_name}"' in migration
