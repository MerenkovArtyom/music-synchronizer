from __future__ import annotations

import argparse
import json
from typing import Sequence

from music_synchronizer.app import MusicSyncApp


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="music-sync-app")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("show-config")
    subparsers.add_parser("sync")
    subparsers.add_parser("dashboard")
    discovery_parser = subparsers.add_parser("discovery")
    discovery_parser.add_argument("--clear", action="store_true")
    recommend_parser = subparsers.add_parser("recommend")
    recommend_parser.add_argument("--archived", action="store_true")

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

    return app.run_command("top-listen", mode="most" if args.most else "least")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    payload = _payload_for_args(MusicSyncApp(), args)
    print(json.dumps(payload))
    return 0 if payload["ok"] else 1


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
