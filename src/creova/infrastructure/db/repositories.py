from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from creova.domain.enums import AccessRole, AccessStatus
from creova.domain.models import AccessGrant as DomainAccessGrant
from creova.infrastructure.db.models import (
    AccessGrant,
    ProcessedTelegramUpdate,
    TelegramUser,
)


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_user_id(self, telegram_user_id: int) -> TelegramUser | None:
        result = await self._session.execute(
            select(TelegramUser).where(TelegramUser.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_telegram_user(
        self,
        *,
        telegram_user_id: int,
        telegram_username: str | None = None,
        display_name: str | None = None,
        timezone: str | None = None,
        now: datetime | None = None,
    ) -> TelegramUser:
        current = now or datetime.now(UTC)
        user = await self.get_by_telegram_user_id(telegram_user_id)
        if user is None:
            user = TelegramUser(
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                display_name=display_name,
                timezone=timezone,
                last_seen_at=current,
            )
            self._session.add(user)
            await self._session.flush()
            return user
        user.telegram_username = telegram_username
        user.display_name = display_name
        user.timezone = timezone
        user.last_seen_at = current
        await self._session.flush()
        return user


class SqlAlchemyAccessGrantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        user_id: UUID,
        role: AccessRole,
        status: AccessStatus,
        valid_from: datetime,
        valid_until: datetime | None = None,
        limits: dict[str, int | float] | None = None,
        reason: str = "",
        created_by: UUID | None = None,
    ) -> AccessGrant:
        grant = AccessGrant(
            user_id=user_id,
            role=role.value,
            status=status.value,
            valid_from=valid_from,
            valid_until=valid_until,
            limits=dict(limits or {}),
            reason=reason,
            created_by=created_by,
        )
        self._session.add(grant)
        await self._session.flush()
        return grant

    async def find_effective_by_telegram_user_id(
        self, telegram_user_id: int
    ) -> DomainAccessGrant | None:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(AccessGrant)
            .join(TelegramUser, TelegramUser.id == AccessGrant.user_id)
            .where(TelegramUser.telegram_user_id == telegram_user_id)
            .where(AccessGrant.status == AccessStatus.ACTIVE.value)
            .where(AccessGrant.valid_from <= now)
            .where((AccessGrant.valid_until.is_(None)) | (AccessGrant.valid_until > now))
            .order_by(AccessGrant.valid_from.desc())
            .limit(1)
        )
        grant = result.scalar_one_or_none()
        if grant is None:
            return None
        return DomainAccessGrant(
            id=grant.id,
            telegram_user_id=telegram_user_id,
            role=AccessRole(grant.role),
            status=AccessStatus(grant.status),
            valid_from=grant.valid_from,
            valid_until=grant.valid_until,
            limits=grant.limits,
        )


class SqlAlchemyTelegramUpdateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_received(
        self,
        *,
        update_id: int,
        payload_hash: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> ProcessedTelegramUpdate:
        del metadata
        update = ProcessedTelegramUpdate(
            update_id=update_id,
            payload_hash=payload_hash,
            status="received",
        )
        self._session.add(update)
        await self._session.flush()
        return update

    async def get(self, update_id: int) -> ProcessedTelegramUpdate | None:
        return await self._session.get(ProcessedTelegramUpdate, update_id)
