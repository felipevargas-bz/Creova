from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from creova.application.access_admin import AccessAdminService, validate_telegram_user_id
from creova.config import Settings
from creova.domain.enums import AccessRole, AccessStatus
from creova.infrastructure.db import SqlAlchemyUnitOfWork, create_async_session_factory

app = typer.Typer(help="Creova administration CLI")
access_app = typer.Typer(help="Manage the access allowlist")
app.add_typer(access_app, name="access")

TelegramUserIdArgument = Annotated[int, typer.Argument(help="Numeric Telegram user ID.")]
RoleOption = Annotated[AccessRole, typer.Option(help="Access role to grant.")]
ReasonOption = Annotated[str, typer.Option(help="Audit reason.")]
StatusOption = Annotated[AccessStatus | None, typer.Option(help="Optional status filter.")]


def _service() -> AccessAdminService:
    settings = Settings()
    session_factory = create_async_session_factory(settings.database_url.get_secret_value())
    return AccessAdminService(SqlAlchemyUnitOfWork(session_factory))


@access_app.command("bootstrap")
def sync_bootstrap() -> None:
    """Synchronize bootstrap access IDs from configuration."""
    settings = Settings()
    records = asyncio.run(
        _service().sync_bootstrap(
            admin_ids=settings.bootstrap_admin_ids,
            allowed_user_ids=settings.bootstrap_allowed_user_ids,
        )
    )
    typer.echo(f"Synchronized {len(records)} bootstrap access records.")


@access_app.command("grant")
def grant_access(
    telegram_user_id: TelegramUserIdArgument,
    role: RoleOption = AccessRole.USER,
    reason: ReasonOption = "manual grant",
) -> None:
    """Grant durable access to a numeric Telegram user ID."""
    validate_telegram_user_id(telegram_user_id)
    record = asyncio.run(
        _service().grant(telegram_user_id=telegram_user_id, role=role, reason=reason)
    )
    typer.echo(f"Granted {record.role.value} access to Telegram ID {record.telegram_user_id}.")


@access_app.command("revoke")
def revoke_access(
    telegram_user_id: TelegramUserIdArgument,
    reason: ReasonOption = "manual revoke",
) -> None:
    """Revoke the latest access grant for a numeric Telegram user ID."""
    validate_telegram_user_id(telegram_user_id)
    record = asyncio.run(_service().revoke(telegram_user_id=telegram_user_id, reason=reason))
    if record is None:
        typer.echo("No access grant exists for that Telegram ID.")
        raise typer.Exit(code=1)
    typer.echo(f"Revoked access for Telegram ID {record.telegram_user_id}.")


@access_app.command("suspend")
def suspend_access(
    telegram_user_id: TelegramUserIdArgument,
    reason: ReasonOption = "manual suspend",
) -> None:
    """Suspend the latest access grant for a numeric Telegram user ID."""
    validate_telegram_user_id(telegram_user_id)
    record = asyncio.run(_service().suspend(telegram_user_id=telegram_user_id, reason=reason))
    if record is None:
        typer.echo("No access grant exists for that Telegram ID.")
        raise typer.Exit(code=1)
    typer.echo(f"Suspended access for Telegram ID {record.telegram_user_id}.")


@access_app.command("inspect")
def inspect_access(
    telegram_user_id: TelegramUserIdArgument,
) -> None:
    """Inspect access records for one numeric Telegram user ID."""
    validate_telegram_user_id(telegram_user_id)
    records = asyncio.run(_service().inspect(telegram_user_id=telegram_user_id))
    if not records:
        typer.echo("No access records found for that Telegram ID.")
        raise typer.Exit(code=1)
    for record in records:
        typer.echo(
            f"{record.telegram_user_id}\t{record.role.value}\t{record.status.value}\t{record.reason}"
        )


@access_app.command("list")
def list_access(
    status: StatusOption = None,
) -> None:
    """List durable access records for private administration."""
    records = asyncio.run(_service().list_access(status=status))
    for record in records:
        typer.echo(
            f"{record.telegram_user_id}\t{record.role.value}\t{record.status.value}\t{record.reason}"
        )
