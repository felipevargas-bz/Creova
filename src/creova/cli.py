from __future__ import annotations

import typer

from creova.config import Settings

app = typer.Typer(help="Creova administration CLI")
access_app = typer.Typer(help="Manage the access allowlist")
app.add_typer(access_app, name="access")


@access_app.command("bootstrap")
def show_bootstrap() -> None:
    """Show bootstrap IDs without exposing other secrets."""
    settings = Settings()
    typer.echo(f"Admin IDs: {sorted(settings.bootstrap_admin_ids)}")
    typer.echo(f"Allowed IDs: {sorted(settings.bootstrap_allowed_user_ids)}")
    typer.echo("Persistent access commands are implemented in Prompt 03.")


@access_app.command("list")
def list_access() -> None:
    typer.echo("PostgreSQL allowlist is not implemented yet. Execute Prompt 03.")
    raise typer.Exit(code=2)
