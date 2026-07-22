from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from creova.domain.enums import AccessRole, AccessStatus
from creova.infrastructure.db.models import AccessGrant
from creova.infrastructure.db.session import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class AccessRecord:
    telegram_user_id: int
    role: AccessRole
    status: AccessStatus
    valid_from: datetime
    valid_until: datetime | None
    reason: str


def validate_telegram_user_id(value: int) -> int:
    if value <= 0:
        raise ValueError("Telegram user ID must be a positive integer")
    return value


class AccessAdminService:
    def __init__(self, unit_of_work: SqlAlchemyUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def grant(
        self,
        *,
        telegram_user_id: int,
        role: AccessRole = AccessRole.USER,
        reason: str,
    ) -> AccessRecord:
        telegram_user_id = validate_telegram_user_id(telegram_user_id)
        async with self._unit_of_work as unit:
            user = await unit.users.upsert_telegram_user(telegram_user_id=telegram_user_id)
            existing = await unit.access_grants.find_effective_by_telegram_user_id(
                telegram_user_id
            )
            if existing is not None and existing.role is role:
                await unit.audit_events.add(
                    event_type="access.bootstrap_unchanged",
                    subject_type="telegram_user",
                    subject_id=str(telegram_user_id),
                    metadata={"role": role.value, "reason": reason},
                )
                return AccessRecord(
                    telegram_user_id=telegram_user_id,
                    role=existing.role,
                    status=existing.status,
                    valid_from=existing.valid_from,
                    valid_until=existing.valid_until,
                    reason=reason,
                )
            grant = await unit.access_grants.add(
                user_id=user.id,
                role=role,
                status=AccessStatus.ACTIVE,
                valid_from=datetime.now(UTC),
                reason=reason,
            )
            await unit.audit_events.add(
                event_type="access.granted",
                subject_type="telegram_user",
                subject_id=str(telegram_user_id),
                metadata={"role": role.value, "reason": reason},
            )
            return _record_from_grant(telegram_user_id, grant)

    async def revoke(self, *, telegram_user_id: int, reason: str) -> AccessRecord | None:
        return await self._set_status(
            telegram_user_id=telegram_user_id,
            status=AccessStatus.REVOKED,
            reason=reason,
            event_type="access.revoked",
        )

    async def suspend(self, *, telegram_user_id: int, reason: str) -> AccessRecord | None:
        return await self._set_status(
            telegram_user_id=telegram_user_id,
            status=AccessStatus.SUSPENDED,
            reason=reason,
            event_type="access.suspended",
        )

    async def inspect(self, *, telegram_user_id: int) -> list[AccessRecord]:
        telegram_user_id = validate_telegram_user_id(telegram_user_id)
        async with self._unit_of_work as unit:
            grants = await unit.access_grants.list_for_telegram_user_id(telegram_user_id)
            return [_record_from_grant(telegram_user_id, grant) for grant in grants]

    async def list_access(self, *, status: AccessStatus | None = None) -> list[AccessRecord]:
        async with self._unit_of_work as unit:
            rows = await unit.access_grants.list_all(status=status)
            return [_record_from_grant(user.telegram_user_id, grant) for user, grant in rows]

    async def sync_bootstrap(
        self,
        *,
        admin_ids: frozenset[int],
        allowed_user_ids: frozenset[int],
    ) -> list[AccessRecord]:
        records: list[AccessRecord] = []
        for telegram_user_id in sorted(admin_ids):
            records.append(
                await self.grant(
                    telegram_user_id=telegram_user_id,
                    role=AccessRole.ADMIN,
                    reason="bootstrap",
                )
            )
        for telegram_user_id in sorted(allowed_user_ids - admin_ids):
            records.append(
                await self.grant(
                    telegram_user_id=telegram_user_id,
                    role=AccessRole.USER,
                    reason="bootstrap",
                )
            )
        return records

    async def _set_status(
        self,
        *,
        telegram_user_id: int,
        status: AccessStatus,
        reason: str,
        event_type: str,
    ) -> AccessRecord | None:
        telegram_user_id = validate_telegram_user_id(telegram_user_id)
        async with self._unit_of_work as unit:
            grant = await unit.access_grants.set_latest_status(
                telegram_user_id=telegram_user_id,
                status=status,
            )
            await unit.audit_events.add(
                event_type=event_type,
                subject_type="telegram_user",
                subject_id=str(telegram_user_id),
                metadata={"reason": reason, "status": status.value},
            )
            if grant is None:
                return None
            return _record_from_grant(telegram_user_id, grant)


def _record_from_grant(telegram_user_id: int, grant: AccessGrant) -> AccessRecord:
    return AccessRecord(
        telegram_user_id=telegram_user_id,
        role=AccessRole(grant.role),
        status=AccessStatus(grant.status),
        valid_from=grant.valid_from,
        valid_until=grant.valid_until,
        reason=grant.reason,
    )
