from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineQuery, Message, TelegramObject

from creova.application.access import AccessService


class AllowlistMiddleware(BaseMiddleware):
    def __init__(self, access_service: AccessService) -> None:
        self._access_service = access_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id, is_private, is_inline = self._extract_identity(event)
        if user_id is None or is_inline or not is_private:
            await self._deny(event, user_id, is_inline=is_inline)
            return None

        decision = await self._access_service.decide(user_id)
        if not decision.allowed or decision.context is None:
            await self._deny(event, user_id, is_inline=False)
            return None

        data["access_context"] = decision.context
        return await handler(event, data)

    @staticmethod
    def _extract_identity(event: TelegramObject) -> tuple[int | None, bool, bool]:
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            return user_id, event.chat.type == "private", False
        if isinstance(event, CallbackQuery):
            message = event.message
            is_private = bool(
                message
                and getattr(message, "chat", None)
                and message.chat.type == "private"
            )
            return event.from_user.id, is_private, False
        if isinstance(event, InlineQuery):
            return event.from_user.id, False, True
        return None, False, False

    @staticmethod
    async def _deny(event: TelegramObject, user_id: int | None, *, is_inline: bool) -> None:
        if is_inline:
            return
        suffix = f"\nYour ID is: <code>{user_id}</code>" if user_id is not None else ""
        text = "This bot is private and your account does not have access." + suffix
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer("You do not have access to Creova.", show_alert=True)
