from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from aiogram.types import Update
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from creova.config import Settings
from creova.domain.enums import AccessRole, AccessStatus
from creova.infrastructure.db.models import Base, ImageConversation, ProcessedTelegramUpdate
from creova.infrastructure.db.session import SqlAlchemyUnitOfWork
from creova.presentation.telegram.transport import TelegramUpdateDeduplicator


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
async def test_update_deduplicator_rejects_duplicate_update_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    deduplicator = TelegramUpdateDeduplicator(SqlAlchemyUnitOfWork(session_factory))
    update = Update(update_id=99)
    payload = {"update_id": 99}

    assert await deduplicator.register_received(update, payload) is True
    assert await deduplicator.register_received(update, payload) is False


@pytest.mark.asyncio
async def test_update_deduplicator_marks_processed(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    deduplicator = TelegramUpdateDeduplicator(SqlAlchemyUnitOfWork(session_factory))
    update = Update(update_id=100)
    await deduplicator.register_received(update, {"update_id": 100})
    await deduplicator.mark_processed(100)

    async with session_factory() as session:
        stored = await session.get(ProcessedTelegramUpdate, 100)

    assert stored is not None
    assert stored.status == "processed"
    assert stored.processed_at is not None


async def seed_authorized_user(
    session_factory: async_sessionmaker[AsyncSession],
    telegram_user_id: int,
) -> None:
    async with SqlAlchemyUnitOfWork(session_factory) as unit:
        user = await unit.users.upsert_telegram_user(telegram_user_id=telegram_user_id)
        await unit.access_grants.add(
            user_id=user.id,
            role=AccessRole.USER,
            status=AccessStatus.ACTIVE,
            valid_from=datetime.now(UTC) - timedelta(minutes=1),
            reason="test",
        )


@pytest.mark.asyncio
async def test_create_command_persists_conversation_fast(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from creova.application.access import AccessContext
    from creova.domain.models import AccessGrant
    from creova.presentation.telegram.handlers import create_handler

    await seed_authorized_user(session_factory, 123)
    answers: list[str] = []

    class User:
        username = "felo"
        full_name = "Felipe"

    class Chat:
        id = 456

    class Message:
        from_user = User()
        chat = Chat()

        async def answer(self, text: str) -> None:
            answers.append(text)

    context = AccessContext(
        telegram_user_id=123,
        role=AccessRole.USER,
        grant=AccessGrant(
            id=uuid4(),
            telegram_user_id=123,
            role=AccessRole.USER,
            status=AccessStatus.ACTIVE,
            valid_from=datetime.now(UTC),
        ),
    )

    await create_handler(
        Message(),  # type: ignore[arg-type]
        context,
        Settings(env="test", telegram_bot_token=""),
        SqlAlchemyUnitOfWork(session_factory),
    )

    async with session_factory() as session:
        conversations = list((await session.execute(select(ImageConversation))).scalars())

    assert len(conversations) == 1
    assert conversations[0].chat_id == 456
    assert answers
