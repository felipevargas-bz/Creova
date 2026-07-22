# ADR-0002: Python 3.12, aiogram 3, and FastAPI

- Status: Accepted
- Date: 2026-07-21

## Context

The system is I/O intensive, integrates Telegram and AI providers, and should be straightforward to extend with Codex while retaining strong typing and testability.

## Decision

Use Python 3.12 or a compatible declared version, aiogram 3 for Telegram, FastAPI for webhook and health endpoints, and SQLAlchemy 2 asynchronous APIs for persistence.

## Rationale

- Strong AI and automation ecosystem.
- aiogram provides asynchronous dispatching, middleware, callback handling, and FSM support.
- FastAPI provides typed HTTP endpoints and operational simplicity.
- One asynchronous programming model reduces blocking risk in handlers.

## Consequences

- The team must follow correct asyncio practices.
- Blocking libraries must be isolated or moved outside the event loop.
- Dependency versions must be locked only after checking current official documentation and compatibility.
