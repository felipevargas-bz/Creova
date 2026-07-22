from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from creova.domain.enums import AccessRole, AccessStatus
from creova.domain.models import AccessGrant


class BootstrapAccessGrantRepository:
    """Development/bootstrap repository. Replace with PostgreSQL in Prompt 03."""

    def __init__(self, admin_ids: frozenset[int], allowed_ids: frozenset[int]) -> None:
        self._admin_ids = admin_ids
        self._allowed_ids = allowed_ids | admin_ids

    async def find_effective_by_telegram_user_id(self, telegram_user_id: int) -> AccessGrant | None:
        if telegram_user_id not in self._allowed_ids:
            return None
        role = AccessRole.ADMIN if telegram_user_id in self._admin_ids else AccessRole.USER
        return AccessGrant(
            id=uuid4(),
            telegram_user_id=telegram_user_id,
            role=role,
            status=AccessStatus.ACTIVE,
            valid_from=datetime(2020, 1, 1, tzinfo=UTC),
        )
