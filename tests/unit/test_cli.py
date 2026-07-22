from typer.testing import CliRunner

from creova.cli import app


def test_access_cli_help_lists_administration_commands() -> None:
    result = CliRunner().invoke(app, ["access", "--help"])

    assert result.exit_code == 0
    assert "grant" in result.output
    assert "revoke" in result.output
    assert "suspend" in result.output
    assert "inspect" in result.output
    assert "bootstrap" in result.output
