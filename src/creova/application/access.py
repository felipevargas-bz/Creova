from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from creova.application.ports import AccessGrantRepository
from creova.domain.enums import AccessRole
from creova.domain.models import AccessGrant


@dataclass(frozen=True, slots=True)
class AccessContext:
    telegram_user_id: int
    role: AccessRole
    grant: AccessGrant


@dataclass(frozen=True, slots=True)
class AccessDecision:
    allowed: bool
    context: AccessContext | None = None
    reason: str = "denied"


class AccessService:
    def __init__(self, repository: AccessGrantRepository) -> None:
        self._repository = repository

    async def decide(self, telegram_user_id: int, *, now: datetime | None = None) -> AccessDecision:
        grant = await self._repository.find_effective_by_telegram_user_id(telegram_user_id)
        if grant is None:
            return AccessDecision(allowed=False, reason="grant_not_found")
        if not grant.is_effective(now or datetime.now(UTC)):
            return AccessDecision(allowed=False, reason="grant_not_effective")
        return AccessDecision(
            allowed=True,
            context=AccessContext(
                telegram_user_id=telegram_user_id,
                role=grant.role,
                grant=grant,
            ),
            reason="allowed",
        )
