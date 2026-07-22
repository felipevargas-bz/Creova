from __future__ import annotations

import asyncio

import uvicorn

from creova.composition import build_container
from creova.config import Settings, TelegramMode
from creova.logging import configure_logging
from creova.presentation.telegram.runtime import build_telegram_runtime


async def _polling_main() -> None:
    settings = Settings()
    if settings.telegram_mode is not TelegramMode.POLLING:
        raise RuntimeError("Set CREOVA_TELEGRAM_MODE=polling to run long polling")
    configure_logging(settings.log_level)
    diagnostics = settings.startup_diagnostics(require_bot_token=True)
    if diagnostics.missing_required_variable_names:
        missing = ", ".join(diagnostics.missing_required_variable_names)
        raise RuntimeError(f"Missing required configuration: {missing}")
    container = build_container(settings)
    runtime = build_telegram_runtime(settings, container)
    try:
        await runtime.bot.delete_webhook(drop_pending_updates=False)
        await runtime.dispatcher.start_polling(
            runtime.bot,
            allowed_updates=runtime.dispatcher.resolve_used_update_types(),
        )
    finally:
        await runtime.bot.session.close()


def run_polling() -> None:
    asyncio.run(_polling_main())


def run_api() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    build_container(settings)
    uvicorn.run("creova.presentation.http:app", host="0.0.0.0", port=8000, factory=False)
