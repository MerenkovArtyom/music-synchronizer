import typer

from music_synchronizer.config import Settings
from music_synchronizer.models import DashboardData, DashboardStatEntry, MonthlyTopEntry, TrackDashboardEntry
from music_synchronizer.obsidian import ObsidianExporter
from music_synchronizer.sync import SyncService


app = typer.Typer(help="CLI for Yandex Music to Obsidian synchronization.")


def _format_monthly_top_entry(index: int, entry: MonthlyTopEntry) -> str:
    artists = ", ".join(entry.artists) if entry.artists else "Unknown Artist"
    return (
        f"{index}. {entry.title} - {artists} | "
        f"monthly_listens={entry.monthly_listens} | position={entry.source_position}"
    )


def _format_dashboard_track(entry: TrackDashboardEntry | None) -> str:
    if entry is None:
        return "-"

    artists = ", ".join(entry.artists) if entry.artists else "Unknown Artist"
    listens = entry.monthly_listens if entry.monthly_listens is not None else 0
    return f"{entry.title} - {artists} | monthly_listens={listens}"


def _format_dashboard_longest_track(entry: TrackDashboardEntry | None) -> str:
    if entry is None:
        return "-"

    artists = ", ".join(entry.artists) if entry.artists else "Unknown Artist"
    return f"{entry.title} - {artists} | duration={entry.duration_text}"


def _format_dashboard_stat(entry: DashboardStatEntry | None, *, include_monthly_listens: bool) -> str:
    if entry is None:
        return "-"

    if include_monthly_listens:
        listens = entry.monthly_listens if entry.monthly_listens is not None else 0
        return f"{entry.name} | monthly_listens={listens} | tracks={entry.count}"

    return f"{entry.name} | tracks={entry.count}"


def _emit_dashboard_summary(settings: Settings, dashboard: DashboardData) -> None:
    typer.echo(f"Dashboard updated: {settings.obsidian_vault_path / 'dashboard.md'}")
    typer.echo(f"liked_tracks={dashboard.liked_tracks_count}")
    typer.echo(f"removed_tracks={dashboard.removed_tracks_count}")
    typer.echo(f"total_tracks={dashboard.total_tracks_count}")
    typer.echo(f"total_duration={dashboard.total_duration_text}")
    typer.echo(f"monthly_listens_known={dashboard.monthly_listens_known_count}")
    typer.echo(
        f"monthly_listens_coverage_percent={dashboard.monthly_listens_coverage_percent:.2f}"
    )
    typer.echo(
        "average_monthly_listens="
        + (
            f"{dashboard.average_monthly_listens:.2f}"
            if dashboard.average_monthly_listens is not None
            else "-"
        )
    )
    typer.echo(
        "median_monthly_listens="
        + (
            f"{dashboard.median_monthly_listens:.2f}"
            if dashboard.median_monthly_listens is not None
            else "-"
        )
    )
    typer.echo(f"most_listened_track={_format_dashboard_track(dashboard.most_listened_track)}")
    typer.echo(
        "most_listened_artist="
        + _format_dashboard_stat(dashboard.most_listened_artist, include_monthly_listens=True)
    )
    typer.echo(f"most_used_tag={_format_dashboard_stat(dashboard.most_used_tag, include_monthly_listens=False)}")
    typer.echo(f"longest_track={_format_dashboard_longest_track(dashboard.longest_track)}")
    typer.echo("top_tags:")
    for index, entry in enumerate(dashboard.top_tags, start=1):
        typer.echo(f"{index}. {_format_dashboard_stat(entry, include_monthly_listens=False)}")
    typer.echo("top_artists:")
    for index, entry in enumerate(dashboard.top_artists, start=1):
        typer.echo(f"{index}. {_format_dashboard_stat(entry, include_monthly_listens=True)}")


@app.command("show-config")
def show_config() -> None:
    settings = Settings()
    typer.echo(f"Obsidian path: {settings.obsidian_vault_path}")
    typer.echo(f"Log level: {settings.log_level}")


@app.command("sync")
def sync() -> None:
    settings = Settings()

    try:
        summary = SyncService(settings).run()
    except RuntimeError as error:
        typer.secho(f"Sync failed: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    typer.echo(
        f"Added: {summary.added}, unchanged: {summary.unchanged}, removed: {summary.removed}."
    )


@app.command("dashboard")
def dashboard() -> None:
    settings = Settings()

    try:
        data = SyncService(settings).refresh_dashboard()
    except RuntimeError as error:
        typer.secho(f"Dashboard failed: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    _emit_dashboard_summary(settings, data)


@app.command("top-listen")
def top_listen(
    most: bool = typer.Option(False, "--most", help="Show the most listened liked tracks."),
    least: bool = typer.Option(False, "--least", help="Show the least listened liked tracks."),
) -> None:
    if most == least:
        raise typer.BadParameter("Exactly one of --most or --least must be provided.")

    settings = Settings()

    try:
        entries = SyncService(settings).top_listen_entries(most=most)
    except RuntimeError as error:
        typer.secho(f"Top listen failed: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    typer.echo("Most Played:" if most else "Least Played:")
    for index, entry in enumerate(entries, start=1):
        typer.echo(_format_monthly_top_entry(index, entry))


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
