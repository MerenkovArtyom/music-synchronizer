import json

import typer
from pydantic import ValidationError

from music_synchronizer.config import Settings
from music_synchronizer.models import SavedTrackInfo, SyncSummary
from music_synchronizer.obsidian import ObsidianExporter
from music_synchronizer.sync import SyncService


app = typer.Typer(help="CLI for Yandex Music to Obsidian synchronization.")

EXIT_CODE_SUCCESS = 0
EXIT_CODE_VALIDATION_ERROR = 2
EXIT_CODE_CONFIG_ERROR = 3
EXIT_CODE_RUNTIME_ERROR = 4
EXIT_CODE_INTERNAL_ERROR = 5


def _emit_json(payload: dict[str, object]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False))


def _json_success(command: str, data: dict[str, object]) -> None:
    _emit_json(
        {
            "ok": True,
            "command": command,
            "data": data,
        }
    )


def _json_error(
    command: str,
    error_code: str,
    message: str,
    exit_code: int,
    details: dict[str, object] | None = None,
) -> None:
    _emit_json(
        {
            "ok": False,
            "command": command,
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {},
            },
        }
    )
    raise typer.Exit(code=exit_code)


def _config_error_details(error: ValidationError) -> tuple[str, str, dict[str, object]]:
    aliases: list[str] = []
    for item in error.errors():
        location = item.get("loc", ())
        if not location:
            continue

        field_name = str(location[0])
        field_info = Settings.model_fields.get(field_name)
        aliases.append(str(field_info.alias if field_info is not None and field_info.alias else field_name))

    fields = sorted(set(aliases))
    if fields == ["OBSIDIAN_VAULT_PATH"]:
        return (
            "CONFIG_MISSING_VAULT_PATH",
            "Missing required setting: OBSIDIAN_VAULT_PATH",
            {"fields": fields},
        )
    if "YANDEX_MUSIC_TOKEN" in fields:
        return (
            "CONFIG_MISSING_TOKEN",
            "Missing required setting: YANDEX_MUSIC_TOKEN",
            {"fields": fields},
        )
    if fields:
        return (
            "CONFIG_INVALID",
            f"Missing or invalid settings: {', '.join(fields)}",
            {"fields": fields},
        )
    return ("CONFIG_INVALID", str(error), {})


def _load_settings(command: str, json_output: bool) -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        error_code, message, details = _config_error_details(error)
        if json_output:
            _json_error(command, error_code, message, EXIT_CODE_CONFIG_ERROR, details)

        typer.secho(message, fg=typer.colors.RED, err=True)
        raise typer.Exit(code=EXIT_CODE_CONFIG_ERROR) from error


def _validation_error(command: str, message: str, json_output: bool) -> None:
    if json_output:
        _json_error(command, "INVALID_ARGUMENT", message, EXIT_CODE_VALIDATION_ERROR)

    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(code=EXIT_CODE_VALIDATION_ERROR)


def _unexpected_error(command: str, error: Exception, json_output: bool) -> None:
    if json_output:
        _json_error(command, "UNEXPECTED_ERROR", str(error), EXIT_CODE_INTERNAL_ERROR)

    typer.secho(f"{command} failed: {error}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=EXIT_CODE_INTERNAL_ERROR) from error


def _show_config_payload(settings: Settings) -> dict[str, object]:
    return {
        "config": {
            "yandexMusicTokenPresent": bool(settings.yandex_music_token),
            "obsidianVaultPath": str(settings.obsidian_vault_path),
            "logLevel": settings.log_level,
        }
    }


def _sync_payload(sync_summary: SyncSummary) -> dict[str, object]:
    return {
        "summary": {
            "fetched": sync_summary.fetched,
            "written": sync_summary.written,
            "archived": sync_summary.archived,
            "restored": sync_summary.restored,
            "removed": sync_summary.archived,
        }
    }


def _list_payload(filter_kind: str, filter_value: str, tracks: list[SavedTrackInfo]) -> dict[str, object]:
    return {
        "filter": {
            "kind": filter_kind,
            "value": filter_value,
        },
        "tracks": [
            {
                "title": track.title,
                "artists": track.artists,
            }
            for track in tracks
        ],
    }


@app.command("show-config")
def show_config(
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
) -> None:
    settings = _load_settings("show-config", json_output)
    if json_output:
        _json_success("show-config", _show_config_payload(settings))
        return

    typer.echo(f"Obsidian path: {settings.obsidian_vault_path}")
    typer.echo(f"Log level: {settings.log_level}")


@app.command("sync")
def sync(
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
) -> None:
    settings = _load_settings("sync", json_output)

    try:
        sync_summary = SyncService(settings).run()
    except RuntimeError as error:
        if json_output:
            _json_error("sync", "SYNC_FAILED", str(error), EXIT_CODE_RUNTIME_ERROR)

        typer.secho(f"Sync failed: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=EXIT_CODE_RUNTIME_ERROR) from error
    except Exception as error:
        _unexpected_error("sync", error, json_output)

    if json_output:
        _json_success("sync", _sync_payload(sync_summary))
        return

    typer.echo(f"Synchronized {sync_summary.fetched} tracks.")


@app.command(
    "list",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": False},
)
def list_tracks(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
    tag: str | None = typer.Option(None, "--tag", help="Filter active saved tracks by tag."),
    artist: str | None = typer.Option(None, "--artist", help="Filter active saved tracks by artist."),
) -> None:
    if ctx.args:
        _validation_error(
            "list",
            'Filter values must be passed as a single argument. If the name contains spaces, use quotes, for example --artist "Artist Guest".',
            json_output,
        )

    if (tag is None and artist is None) or (tag is not None and artist is not None):
        _validation_error("list", "Exactly one of --tag or --artist must be provided.", json_output)

    settings = _load_settings("list", json_output)
    try:
        exporter = ObsidianExporter(settings.obsidian_vault_path)
        if tag is not None:
            tracks = exporter.list_tracks_by_tag(tag)
            filter_name = "tag"
            filter_value = tag
        else:
            tracks = exporter.list_tracks_by_artist(artist or "")
            filter_name = "artist"
            filter_value = artist or ""
    except Exception as error:
        _unexpected_error("list", error, json_output)

    if json_output:
        _json_success("list", _list_payload(filter_name, filter_value, tracks))
        return

    if not tracks:
        typer.echo(f'No active saved tracks found for {filter_name} "{filter_value}".')
        return

    for track in tracks:
        artists = ", ".join(track.artists) if track.artists else "Unknown Artist"
        typer.echo(f"{track.title} - {artists}")
