from typer.testing import CliRunner

from nightshift.cli.app import app


def test_cli_help_smoke():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "NightShift" in result.stdout
