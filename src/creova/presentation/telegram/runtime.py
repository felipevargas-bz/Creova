from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from creova.composition import AppContainer, build_container
from creova.config import Settings
from creova.presentation.telegram.access_middleware import AllowlistMiddleware
from creova.presentation.telegram.handlers import router


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
    dispatcher.message.middleware(AllowlistMiddleware(resolved_container.access_service))
    dispatcher.callback_query.middleware(AllowlistMiddleware(resolved_container.access_service))
    dispatcher.include_router(router)
    return TelegramRuntime(bot=bot, dispatcher=dispatcher)
