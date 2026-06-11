from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from typing import Sequence

from pydantic import ValidationError

from music_synchronizer.backend_contracts import (
    BackendCommand,
    build_error_envelope,
    validate_backend_envelope,
)
from music_synchronizer.app import MusicSyncApp


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="music-sync-app")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("show-config")
    save_config_parser = subparsers.add_parser("save-config")
    save_config_parser.add_argument("--yandex-music-token", required=True)
    save_config_parser.add_argument("--obsidian-vault-path", required=True)
    save_config_parser.add_argument("--discovery-playlist-name", required=True)
    save_config_parser.add_argument("--log-level", required=True)
    subparsers.add_parser("sync")
    subparsers.add_parser("dashboard")
    discovery_parser = subparsers.add_parser("discovery")
    discovery_parser.add_argument("--clear", action="store_true")
    recommend_parser = subparsers.add_parser("recommend")
    recommend_parser.add_argument("--archived", action="store_true")
    vault_parser = subparsers.add_parser("vault")
    vault_parser.add_argument("--selected-path")

    list_parser = subparsers.add_parser("list")
    list_group = list_parser.add_mutually_exclusive_group(required=True)
    list_group.add_argument("--tag")
    list_group.add_argument("--artist")

    top_listen_parser = subparsers.add_parser("top-listen")
    top_listen_group = top_listen_parser.add_mutually_exclusive_group(required=True)
    top_listen_group.add_argument("--most", action="store_true")
    top_listen_group.add_argument("--least", action="store_true")

    return parser


def _payload_for_args(app: MusicSyncApp, args: argparse.Namespace) -> dict[str, object]:
    if args.command == "show-config":
        return app.run_command("show-config")
    if args.command == "save-config":
        return app.run_command(
            "save-config",
            yandex_music_token=args.yandex_music_token,
            obsidian_vault_path=args.obsidian_vault_path,
            discovery_playlist_name=args.discovery_playlist_name,
            log_level=args.log_level,
        )
    if args.command == "sync":
        return app.run_command("sync")
    if args.command == "dashboard":
        return app.run_command("dashboard")
    if args.command == "discovery":
        return app.run_command("discovery", clear=args.clear)
    if args.command == "list":
        if args.tag is not None:
            return app.run_command("list", kind="tag", value=args.tag)
        return app.run_command("list", kind="artist", value=args.artist)
    if args.command == "recommend":
        return app.run_command("recommend", include_archived=args.archived)
    if args.command == "vault":
        return app.run_command("vault", selected_path=args.selected_path)

    return app.run_command("top-listen", mode="most" if args.most else "least")


def _serialize_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _execute_command(args: argparse.Namespace) -> tuple[BackendCommand, dict[str, object]]:
    command = args.command
    assert isinstance(command, str)

    captured_stdout = io.StringIO()
    try:
        with redirect_stdout(captured_stdout):
            payload = _payload_for_args(MusicSyncApp(), args)
    except Exception as error:
        return command, build_error_envelope(
            command,
            "BACKEND_UNHANDLED_ERROR",
            f"music-sync-app failed before producing a response: {error}",
            {},
        )

    leaked_stdout = captured_stdout.getvalue()
    if leaked_stdout:
        return command, build_error_envelope(
            command,
            "BACKEND_STDOUT_VIOLATION",
            "music-sync-app must not write non-JSON output to stdout.",
            {"capturedStdout": leaked_stdout},
        )

    try:
        return command, validate_backend_envelope(command, payload)
    except ValidationError as error:
        return command, build_error_envelope(
            command,
            "BACKEND_SCHEMA_VALIDATION_FAILED",
            f"Backend payload failed schema validation: {error}",
            {"errors": error.errors(include_url=False)},
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    _command, payload = _execute_command(args)
    sys.stdout.write(_serialize_payload(payload) + "\n")
    return 0 if payload["ok"] else 1


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
