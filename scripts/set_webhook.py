"""Configure Telegram webhook after Prompt 02/03 wiring is complete."""

import asyncio

from aiogram import Bot

from creova.config import Settings, TelegramMode


async def main() -> None:
    settings = Settings()
    if settings.telegram_mode is not TelegramMode.WEBHOOK:
        raise RuntimeError("Set CREOVA_TELEGRAM_MODE=webhook")
    async with Bot(settings.require_bot_token()) as bot:
        await bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.telegram_webhook_secret.get_secret_value(),
            allowed_updates=["message", "callback_query"],
        )
        info = await bot.get_webhook_info()
        print(info.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
