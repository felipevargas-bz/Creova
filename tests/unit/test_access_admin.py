from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from creova.application.access_admin import AccessAdminService, validate_telegram_user_id
from creova.domain.enums import AccessRole, AccessStatus
from creova.infrastructure.db.models import AuditEvent, Base, TelegramUser
from creova.infrastructure.db.session import SqlAlchemyUnitOfWork


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


def test_rejects_non_positive_telegram_user_id() -> None:
    with pytest.raises(ValueError, match="positive"):
        validate_telegram_user_id(0)


@pytest.mark.asyncio
async def test_grant_suspend_revoke_and_audit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    service = AccessAdminService(SqlAlchemyUnitOfWork(session_factory))

    granted = await service.grant(
        telegram_user_id=123,
        role=AccessRole.ADMIN,
        reason="test grant",
    )
    suspended = await service.suspend(telegram_user_id=123, reason="test suspend")
    revoked = await service.revoke(telegram_user_id=123, reason="test revoke")

    assert granted.role is AccessRole.ADMIN
    assert suspended is not None
    assert suspended.status is AccessStatus.SUSPENDED
    assert revoked is not None
    assert revoked.status is AccessStatus.REVOKED

    async with session_factory() as session:
        audit_count = await session.scalar(select(func.count()).select_from(AuditEvent))

    assert audit_count == 3


@pytest.mark.asyncio
async def test_bootstrap_sync_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    service = AccessAdminService(SqlAlchemyUnitOfWork(session_factory))

    await service.sync_bootstrap(admin_ids=frozenset({1}), allowed_user_ids=frozenset({1, 2}))
    await service.sync_bootstrap(admin_ids=frozenset({1}), allowed_user_ids=frozenset({1, 2}))

    records = await service.list_access()
    async with session_factory() as session:
        user_count = await session.scalar(select(func.count()).select_from(TelegramUser))

    assert user_count == 2
    assert sorted(record.telegram_user_id for record in records) == [1, 2]


@pytest.mark.asyncio
async def test_inspect_is_scoped_to_one_numeric_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    service = AccessAdminService(SqlAlchemyUnitOfWork(session_factory))
    await service.grant(telegram_user_id=10, role=AccessRole.USER, reason="one")
    await service.grant(telegram_user_id=20, role=AccessRole.USER, reason="two")

    records = await service.inspect(telegram_user_id=10)

    assert len(records) == 1
    assert records[0].telegram_user_id == 10
