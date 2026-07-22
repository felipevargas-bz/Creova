from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Any

from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request, status

from creova.composition import AppContainer, build_container
from creova.config import Settings
from creova.presentation.telegram.runtime import TelegramRuntime, build_telegram_runtime
from creova.presentation.telegram.transport import TelegramUpdateDeduplicator


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    return build_container(get_settings())


@lru_cache(maxsize=1)
def get_runtime() -> TelegramRuntime:
    return build_telegram_runtime(get_settings(), get_container())


@lru_cache(maxsize=1)
def get_deduplicator() -> TelegramUpdateDeduplicator:
    return TelegramUpdateDeduplicator(get_container().unit_of_work)


def is_valid_webhook_secret(expected: str, provided: str | None) -> bool:
    return bool(expected and provided and secrets.compare_digest(expected, provided))


def create_app() -> FastAPI:
    application = FastAPI(title="Creova", version="0.1.0", docs_url=None, redoc_url=None)

    @application.get("/health/live")
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready")
    async def readiness() -> dict[str, object]:
        settings = get_settings()
        diagnostics = get_container().startup_diagnostics
        return {
            "status": "ready",
            "mode": settings.telegram_mode.value,
            "missing_optional_variables": diagnostics.missing_optional_variable_names,
        }

    @application.post(get_settings().telegram_webhook_path, include_in_schema=False)
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> dict[str, bool]:
        settings = get_settings()
        expected = settings.telegram_webhook_secret.get_secret_value()
        if not is_valid_webhook_secret(expected, x_telegram_bot_api_secret_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

        payload: dict[str, Any] = await request.json()
        update = Update.model_validate(payload, context={"bot": get_runtime().bot})
        deduplicator = get_deduplicator()
        if not await deduplicator.register_received(update, payload):
            return {"ok": True}
        runtime = get_runtime()
        runtime.dispatcher.workflow_data["skip_update_deduplication"] = True
        try:
            await runtime.dispatcher.feed_update(runtime.bot, update)
        except Exception:
            await deduplicator.mark_failed(update.update_id, error_code="feed_update_failed")
            raise
        await deduplicator.mark_processed(update.update_id)
        return {"ok": True}

    return application


app = create_app()
