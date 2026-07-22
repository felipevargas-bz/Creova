from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from creova.infrastructure.db.repositories import (
    SqlAlchemyAccessGrantRepository,
    SqlAlchemyAuditEventRepository,
    SqlAlchemyTelegramUpdateRepository,
    SqlAlchemyUserRepository,
)


def create_async_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None
        self.users: SqlAlchemyUserRepository
        self.access_grants: SqlAlchemyAccessGrantRepository
        self.audit_events: SqlAlchemyAuditEventRepository
        self.telegram_updates: SqlAlchemyTelegramUpdateRepository

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self._session_factory()
        self.users = SqlAlchemyUserRepository(self.session)
        self.access_grants = SqlAlchemyAccessGrantRepository(self.session)
        self.audit_events = SqlAlchemyAuditEventRepository(self.session)
        self.telegram_updates = SqlAlchemyTelegramUpdateRepository(self.session)
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.session is None:
            return
        if exc_type is None:
            await self.session.commit()
        else:
            await self.session.rollback()
        await self.session.close()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[SqlAlchemyUnitOfWork]:
        async with self as unit:
            yield unit
