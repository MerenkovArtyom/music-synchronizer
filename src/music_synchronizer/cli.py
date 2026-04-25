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


@app.command(
    "list",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": False},
)
def list_tracks(
    ctx: typer.Context,
    tag: str | None = typer.Option(None, "--tag", help="Filter active saved tracks by tag."),
    artist: str | None = typer.Option(None, "--artist", help="Filter active saved tracks by artist."),
) -> None:
    if ctx.args:
        raise typer.BadParameter(
            'Filter values must be passed as a single argument. If the name contains spaces, use quotes, for example --artist "Artist Guest".'
        )

    if (tag is None and artist is None) or (tag is not None and artist is not None):
        raise typer.BadParameter("Exactly one of --tag or --artist must be provided.")

    settings = Settings()
    exporter = ObsidianExporter(settings.obsidian_vault_path)
    if tag is not None:
        tracks = exporter.list_tracks_by_tag(tag)
        filter_name = "tag"
        filter_value = tag
    else:
        tracks = exporter.list_tracks_by_artist(artist or "")
        filter_name = "artist"
        filter_value = artist or ""

    if not tracks:
        typer.echo(f'No active saved tracks found for {filter_name} "{filter_value}".')
        return

    for track in tracks:
        artists = ", ".join(track.artists) if track.artists else "Unknown Artist"
        typer.echo(f"{track.title} - {artists}")
