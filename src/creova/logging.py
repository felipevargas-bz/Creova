import logging
import sys
from collections.abc import Mapping
from typing import Any, cast

import structlog
from pydantic import SecretBytes, SecretStr

REDACTED = "[redacted]"

_SENSITIVE_KEY_PARTS = (
    "authorization",
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "access_key",
    "signed_url",
    "database_url",
    "webhook_secret",
)


def redact(value: Any) -> Any:
    if isinstance(value, (SecretStr, SecretBytes)):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            key: REDACTED if _is_sensitive_key(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    return value


def redact_event(
    logger: logging.Logger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    del logger, method_name
    return cast(structlog.types.EventDict, redact(event_dict))


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level.upper(), stream=sys.stdout, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_event,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
    )
