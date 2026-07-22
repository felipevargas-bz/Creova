from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from creova.application.access import AccessService
from creova.domain.enums import AccessRole, AccessStatus
from creova.domain.models import AccessGrant


class Repository:
    def __init__(self, grant: AccessGrant | None) -> None:
        self.grant = grant

    async def find_effective_by_telegram_user_id(self, telegram_user_id: int) -> AccessGrant | None:
        if self.grant and self.grant.telegram_user_id == telegram_user_id:
            return self.grant
        return None


@pytest.mark.asyncio
async def test_denies_unknown_user() -> None:
    decision = await AccessService(Repository(None)).decide(123)
    assert decision.allowed is False
    assert decision.reason == "grant_not_found"


@pytest.mark.asyncio
async def test_allows_effective_grant() -> None:
    now = datetime.now(UTC)
    grant = AccessGrant(
        id=uuid4(),
        telegram_user_id=123,
        role=AccessRole.USER,
        status=AccessStatus.ACTIVE,
        valid_from=now - timedelta(minutes=1),
    )
    decision = await AccessService(Repository(grant)).decide(123, now=now)
    assert decision.allowed is True
    assert decision.context is not None
    assert decision.context.role is AccessRole.USER


@pytest.mark.asyncio
async def test_denies_expired_grant() -> None:
    now = datetime.now(UTC)
    grant = AccessGrant(
        id=uuid4(),
        telegram_user_id=123,
        role=AccessRole.USER,
        status=AccessStatus.ACTIVE,
        valid_from=now - timedelta(days=2),
        valid_until=now - timedelta(days=1),
    )
    decision = await AccessService(Repository(grant)).decide(123, now=now)
    assert decision.allowed is False
