import typer

from music_synchronizer.config import Settings


app = typer.Typer(help="CLI for Yandex Music to Obsidian synchronization.")


@app.command("show-config")
def show_config() -> None:
    settings = Settings()
    typer.echo(f"Obsidian path: {settings.obsidian_vault_path}")
    typer.echo(f"Log level: {settings.log_level}")


@app.command("sync")
def sync() -> None:
    typer.echo("Sync skeleton is ready. Implementation comes next.")
