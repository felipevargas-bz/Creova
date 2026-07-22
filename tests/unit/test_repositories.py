from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from creova.domain.enums import AccessRole, AccessStatus
from creova.infrastructure.db.models import Base
from creova.infrastructure.db.repositories import (
    SqlAlchemyAccessGrantRepository,
    SqlAlchemyTelegramUpdateRepository,
    SqlAlchemyUserRepository,
)


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_user_and_access_grant_repository_find_effective_grant(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        users = SqlAlchemyUserRepository(session)
        grants = SqlAlchemyAccessGrantRepository(session)
        user = await users.upsert_telegram_user(
            telegram_user_id=9_001_234_567,
            telegram_username="felo",
            display_name="Felipe",
        )
        await grants.add(
            user_id=user.id,
            role=AccessRole.ADMIN,
            status=AccessStatus.ACTIVE,
            valid_from=datetime.now(UTC) - timedelta(minutes=1),
            reason="bootstrap",
        )
        await session.commit()

    async with session_factory() as session:
        grants = SqlAlchemyAccessGrantRepository(session)
        grant = await grants.find_effective_by_telegram_user_id(9_001_234_567)

    assert grant is not None
    assert grant.telegram_user_id == 9_001_234_567
    assert grant.role is AccessRole.ADMIN
    assert grant.status is AccessStatus.ACTIVE


@pytest.mark.asyncio
async def test_processed_update_repository_enforces_update_id_uniqueness(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        updates = SqlAlchemyTelegramUpdateRepository(session)
        await updates.insert_received(update_id=123, payload_hash="hash")
        await session.commit()

    async with session_factory() as session:
        updates = SqlAlchemyTelegramUpdateRepository(session)
        with pytest.raises(IntegrityError):
            await updates.insert_received(update_id=123, payload_hash="hash")
