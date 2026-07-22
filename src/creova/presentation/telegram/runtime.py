from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from creova.composition import AppContainer, build_container
from creova.config import Settings
from creova.presentation.telegram.access_middleware import AllowlistMiddleware
from creova.presentation.telegram.handlers import router
from creova.presentation.telegram.transport import (
    TelegramUpdateDeduplicationMiddleware,
    TelegramUpdateDeduplicator,
)


@dataclass(slots=True)
class TelegramRuntime:
    bot: Bot
    dispatcher: Dispatcher


def build_telegram_runtime(
    settings: Settings,
    container: AppContainer | None = None,
) -> TelegramRuntime:
    resolved_container = container or build_container(settings)
    bot = Bot(
        token=settings.require_bot_token(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.workflow_data["settings"] = settings
    dispatcher.workflow_data["unit_of_work"] = resolved_container.unit_of_work
    dispatcher.update.outer_middleware(
        TelegramUpdateDeduplicationMiddleware(
            TelegramUpdateDeduplicator(resolved_container.unit_of_work)
        )
    )
    dispatcher.message.middleware(AllowlistMiddleware(resolved_container.access_service))
    dispatcher.callback_query.middleware(AllowlistMiddleware(resolved_container.access_service))
    dispatcher.inline_query.middleware(AllowlistMiddleware(resolved_container.access_service))
    dispatcher.include_router(router)
    return TelegramRuntime(bot=bot, dispatcher=dispatcher)
