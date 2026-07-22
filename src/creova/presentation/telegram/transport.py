from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy.exc import IntegrityError

from creova.infrastructure.db.session import SqlAlchemyUnitOfWork


class TelegramUpdateDeduplicator:
    def __init__(self, unit_of_work: SqlAlchemyUnitOfWork | None) -> None:
        self._unit_of_work = unit_of_work

    async def register_received(self, update: Update, payload: dict[str, object]) -> bool:
        if self._unit_of_work is None:
            return True
        payload_hash = _payload_hash(payload)
        try:
            async with self._unit_of_work as unit:
                await unit.telegram_updates.insert_received(
                    update_id=update.update_id,
                    payload_hash=payload_hash,
                )
        except IntegrityError:
            return False
        return True

    async def mark_processed(self, update_id: int) -> None:
        if self._unit_of_work is None:
            return
        async with self._unit_of_work as unit:
            await unit.telegram_updates.mark_processed(update_id)

    async def mark_failed(self, update_id: int, *, error_code: str) -> None:
        if self._unit_of_work is None:
            return
        async with self._unit_of_work as unit:
            await unit.telegram_updates.mark_failed(update_id, error_code=error_code)


class TelegramUpdateDeduplicationMiddleware(BaseMiddleware):
    def __init__(self, deduplicator: TelegramUpdateDeduplicator) -> None:
        self._deduplicator = deduplicator

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)
        if data.get("skip_update_deduplication") is True:
            return await handler(event, data)
        payload = event.model_dump(mode="json", exclude_none=True)
        if not await self._deduplicator.register_received(event, payload):
            return None
        try:
            result = await handler(event, data)
        except Exception:
            await self._deduplicator.mark_failed(
                event.update_id,
                error_code="feed_update_failed",
            )
            raise
        await self._deduplicator.mark_processed(event.update_id)
        return result


def _payload_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
