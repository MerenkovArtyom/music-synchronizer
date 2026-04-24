from typer.testing import CliRunner

from music_synchronizer.cli import app


def test_help_shows_sync_placeholder() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "sync" in result.output
    assert "show-config" in result.output
