from __future__ import annotations

import asyncio

import structlog

from creova.config import Settings
from creova.logging import configure_logging


async def _worker_main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    logger = structlog.get_logger("creova.worker")
    logger.error(
        "worker_not_implemented",
        guidance="Complete the remaining implementation phases before running the worker",
    )
    raise SystemExit(2)


def run_worker() -> None:
    asyncio.run(_worker_main())
