import typer
from pydantic import ValidationError

from music_synchronizer.app import MusicSyncApp
from music_synchronizer.models import DashboardStatEntry, MonthlyTopEntry, TrackDashboardEntry


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


def _emit_dashboard_summary(payload: dict[str, object]) -> None:
    typer.echo(f"Dashboard updated: {payload['path']}")
    summary = payload["summary"]
    assert isinstance(summary, dict)
    typer.echo(f"liked_tracks={summary['likedTracks']}")
    typer.echo(f"removed_tracks={summary['removedTracks']}")
    typer.echo(f"total_tracks={summary['totalTracks']}")
    typer.echo(f"total_duration={summary['totalDuration']}")
    typer.echo(f"monthly_listens_known={summary['monthlyListensKnown']}")
    typer.echo(
        f"monthly_listens_coverage_percent={float(summary['monthlyListensCoveragePercent']):.2f}"
    )
    average = summary["averageMonthlyListens"]
    typer.echo(
        "average_monthly_listens="
        + (f"{float(average):.2f}" if average is not None else "-")
    )
    median = summary["medianMonthlyListens"]
    typer.echo(
        "median_monthly_listens="
        + (f"{float(median):.2f}" if median is not None else "-")
    )
    most_listened_track = summary["mostListenedTrack"]
    typer.echo(
        "most_listened_track="
        + (
            "-"
            if most_listened_track is None
            else f"{most_listened_track['title']} - {', '.join(most_listened_track['artists']) if most_listened_track['artists'] else 'Unknown Artist'} | monthly_listens={most_listened_track['monthlyListens']}"
        )
    )
    most_listened_artist = summary["mostListenedArtist"]
    typer.echo(
        "most_listened_artist="
        + (
            "-"
            if most_listened_artist is None
            else f"{most_listened_artist['name']} | monthly_listens={most_listened_artist['monthlyListens']} | tracks={most_listened_artist['tracks']}"
        )
    )
    most_used_tag = summary["mostUsedTag"]
    typer.echo(
        "most_used_tag="
        + (
            "-"
            if most_used_tag is None
            else f"{most_used_tag['name']} | tracks={most_used_tag['tracks']}"
        )
    )
    longest_track = summary["longestTrack"]
    typer.echo(
        "longest_track="
        + (
            "-"
            if longest_track is None
            else f"{longest_track['title']} - {', '.join(longest_track['artists']) if longest_track['artists'] else 'Unknown Artist'} | duration={longest_track['duration']}"
        )
    )
    typer.echo("top_tags:")
    top_tags = payload["topTags"]
    assert isinstance(top_tags, list)
    for index, entry in enumerate(top_tags, start=1):
        typer.echo(f"{index}. {entry['name']} | tracks={entry['tracks']}")
    typer.echo("top_artists:")
    top_artists = payload["topArtists"]
    assert isinstance(top_artists, list)
    for index, entry in enumerate(top_artists, start=1):
        typer.echo(
            f"{index}. {entry['name']} | monthly_listens={entry['monthlyListens']} | tracks={entry['tracks']}"
        )


def _build_app() -> MusicSyncApp:
    try:
        return MusicSyncApp()
    except ValidationError as error:
        missing_fields: list[str] = []
        for detail in error.errors():
            if detail.get("type") != "missing":
                continue
            location = detail.get("loc", ())
            if not location:
                continue
            missing_fields.append(str(location[-1]))

        if missing_fields:
            fields = ", ".join(missing_fields)
            raise RuntimeError(f"Missing required setting: {fields}") from error

        raise RuntimeError("Invalid application settings.") from error


@app.command("show-config")
def show_config() -> None:
    try:
        config = _build_app().show_config()["config"]
    except RuntimeError as error:
        typer.secho(f"Show config failed: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"Obsidian path: {config['obsidianVaultPath']}")
    typer.echo(f"Log level: {config['logLevel']}")


@app.command("sync")
def sync() -> None:
    try:
        summary = _build_app().sync()["summary"]
    except RuntimeError as error:
        typer.secho(f"Sync failed: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    typer.echo(
        f"Added: {summary['added']}, unchanged: {summary['unchanged']}, removed: {summary['removed']}."
    )


@app.command("dashboard")
def dashboard() -> None:
    try:
        payload = _build_app().dashboard()
    except RuntimeError as error:
        typer.secho(f"Dashboard failed: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    _emit_dashboard_summary(payload)


@app.command("top-listen")
def top_listen(
    most: bool = typer.Option(False, "--most", help="Show the most listened liked tracks."),
    least: bool = typer.Option(False, "--least", help="Show the least listened liked tracks."),
) -> None:
    if most == least:
        raise typer.BadParameter("Exactly one of --most or --least must be provided.")

    try:
        payload = _build_app().top_listen(mode="most" if most else "least")
    except RuntimeError as error:
        typer.secho(f"Top listen failed: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    typer.echo("Most Played:" if most else "Least Played:")
    entries = payload["mostPlayed"] if most else payload["leastPlayed"]
    for index, entry in enumerate(entries, start=1):
        typer.echo(
            f"{index}. {entry['title']} - {', '.join(entry['artists']) if entry['artists'] else 'Unknown Artist'} | "
            f"monthly_listens={entry['monthlyListens']} | position={entry['position']}"
        )


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

    try:
        if tag is not None:
            payload = _build_app().list_tracks(kind="tag", value=tag)
            filter_name = "tag"
            filter_value = tag
        else:
            payload = _build_app().list_tracks(kind="artist", value=artist or "")
            filter_name = "artist"
            filter_value = artist or ""
    except RuntimeError as error:
        typer.secho(f"List failed: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from error

    tracks = payload["tracks"]
    if not tracks:
        typer.echo(f'No active saved tracks found for {filter_name} "{filter_value}".')
        return

    for track in tracks:
        artists = ", ".join(track["artists"]) if track["artists"] else "Unknown Artist"
        typer.echo(f"{track['title']} - {artists}")
