from typing import Any

import pytest
from aiogram.types import InlineQuery, User

from creova.presentation.telegram.access_middleware import AllowlistMiddleware


class Service:
    async def decide(self, telegram_user_id: int) -> Any:
        raise AssertionError("Inline mode must be rejected before access lookup")


@pytest.mark.asyncio
async def test_inline_mode_is_rejected_without_access_lookup() -> None:
    middleware = AllowlistMiddleware(Service())
    inline_query = InlineQuery(
        id="inline-id",
        from_user=User(id=123, is_bot=False, first_name="Test"),
        query="image",
        offset="",
    )

    result = await middleware(lambda event, data: None, inline_query, {})

    assert result is None
