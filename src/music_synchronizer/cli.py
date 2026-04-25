import typer

from music_synchronizer.config import Settings
from music_synchronizer.obsidian import ObsidianExporter
from music_synchronizer.sync import SyncService


app = typer.Typer(help="CLI for Yandex Music to Obsidian synchronization.")


@app.command("show-config")
def show_config() -> None:
    settings = Settings()
    typer.echo(f"Obsidian path: {settings.obsidian_vault_path}")
    typer.echo(f"Log level: {settings.log_level}")


@app.command("sync")
def sync() -> None:
    settings = Settings()

    try:
        synced_count = SyncService(settings).run()
    except RuntimeError as error:
        typer.secho(f"Sync failed: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"Synchronized {synced_count} tracks.")


@app.command("list")
def list_tracks(tag: str = typer.Option(..., "--tag", help="Filter active saved tracks by tag.")) -> None:
    settings = Settings()
    exporter = ObsidianExporter(settings.obsidian_vault_path)
    tracks = exporter.list_tracks(tag)

    if not tracks:
        typer.echo(f'No active saved tracks found for tag "{tag}".')
        return

    for track in tracks:
        artists = ", ".join(track.artists) if track.artists else "Unknown Artist"
        typer.echo(f"{track.title} - {artists}")
