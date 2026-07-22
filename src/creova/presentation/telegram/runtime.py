from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from creova.application.access import AccessService
from creova.config import Settings
from creova.infrastructure.memory import BootstrapAccessGrantRepository
from creova.presentation.telegram.access_middleware import AllowlistMiddleware
from creova.presentation.telegram.handlers import router


@dataclass(slots=True)
class TelegramRuntime:
    bot: Bot
    dispatcher: Dispatcher


def build_telegram_runtime(settings: Settings) -> TelegramRuntime:
    repository = BootstrapAccessGrantRepository(
        admin_ids=settings.bootstrap_admin_ids,
        allowed_ids=settings.bootstrap_allowed_user_ids,
    )
    access_service = AccessService(repository)

    bot = Bot(
        token=settings.require_bot_token(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.message.middleware(AllowlistMiddleware(access_service))
    dispatcher.callback_query.middleware(AllowlistMiddleware(access_service))
    dispatcher.include_router(router)
    return TelegramRuntime(bot=bot, dispatcher=dispatcher)
